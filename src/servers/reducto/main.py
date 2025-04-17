import os
import sys
import httpx
import logging
import json
from pathlib import Path
from typing import Optional

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
REDUCTO_API_URL = "https://platform.reducto.ai"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_reducto_key(user_id):
    """Authenticate with Reducto and save API key"""
    logger = logging.getLogger("reducto")
    logger.info(f"Starting Reducto authentication for user {user_id}...")

    auth_client = create_auth_client()
    api_key = input("Please enter your Reducto API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    auth_client.save_user_credentials("reducto", user_id, {"api_key": api_key})
    logger.info(
        f"Reducto API key saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_reducto_credentials(user_id, api_key=None):
    """Get Reducto API key for the specified user"""
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials("reducto", user_id)

    def handle_missing_credentials():
        error_str = f"Reducto API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    api_key = (
        credentials_data.get("api_key")
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


async def make_reducto_request(
    method, endpoint, data=None, api_key=None, params=None, files=None
):
    """Make a request to the Reducto API"""
    if not api_key:
        raise ValueError("Reducto API key is required")

    url = f"{REDUCTO_API_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    if data and not files:
        headers["Content-Type"] = "application/json"

    try:
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(
                    url, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "post":
                if files:
                    response = await client.post(
                        url, files=files, headers=headers, params=params, timeout=600.0
                    )
                else:
                    response = await client.post(
                        url, json=data, headers=headers, params=params, timeout=600.0
                    )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            try:
                response_json = response.json()
                response_json["_status_code"] = response.status_code
                return response_json
            except:
                return {"_status_code": response.status_code, "result": response.text}

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling {endpoint}: {e.response.status_code}")
        error_message = f"Reducto API error: {e.response.status_code}"
        try:
            error_details = e.response.json()
            if isinstance(error_details, dict) and "detail" in error_details:
                error_message = error_details["detail"]
        except:
            pass
        raise ValueError(error_message)

    except Exception as e:
        logger.error(f"Error making request to Reducto API: {str(e)}")
        raise ValueError(f"Error communicating with Reducto API: {str(e)}")


def create_server(user_id, api_key=None):
    server = Server("reducto-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="split_document",
                description="Split a document into sections based on provided criteria",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_url": {
                            "type": "string",
                            "description": "URL of the document to be processed (public URL, presigned S3 URL, or reducto:// URL obtained from upload)",
                        },
                        "split_description": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name of the section",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Description of what the section should contain",
                                    },
                                    "partition_key": {
                                        "type": "string",
                                        "description": "Optional key to identify the section",
                                    },
                                },
                                "required": ["name", "description"],
                            },
                            "description": "Configuration options for processing the document",
                        },
                        "split_rules": {
                            "type": "string",
                            "description": "Rules for splitting the document, defaults to 'Split the document into the applicable sections. Sections may only overlap at their first and last page if at all.'",
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "ocr_mode": {
                                    "type": "string",
                                    "enum": ["standard", "premium", "none"],
                                    "description": "OCR mode to use",
                                },
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["ocr", "pdf", "auto"],
                                    "description": "Mode for extracting text from PDF",
                                },
                            },
                        },
                        "advanced_options": {
                            "type": "object",
                            "properties": {
                                "ocr_system": {
                                    "type": "string",
                                    "enum": ["highres", "standard"],
                                    "description": "OCR system to use",
                                },
                                "table_output_format": {
                                    "type": "string",
                                    "enum": ["html", "markdown"],
                                    "description": "Format for table output",
                                },
                                "page_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {
                                            "type": "integer",
                                            "description": "Starting page",
                                        },
                                        "end": {
                                            "type": "integer",
                                            "description": "Ending page",
                                        },
                                    },
                                    "description": "Range of pages to process",
                                },
                                "document_password": {
                                    "type": "string",
                                    "description": "Password for protected PDF",
                                },
                            },
                        },
                        "priority": {
                            "type": "boolean",
                            "description": "Whether to process with priority, default is true",
                        },
                    },
                    "required": ["document_url", "split_description"],
                },
            ),
            Tool(
                name="split_document_async",
                description="Split a document asynchronously into sections based on provided criteria",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_url": {
                            "type": "string",
                            "description": "URL of the document to be processed (public URL, presigned S3 URL, or reducto:// URL obtained from upload)",
                        },
                        "split_description": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name of the section",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Description of what the section should contain",
                                    },
                                    "partition_key": {
                                        "type": "string",
                                        "description": "Optional key to identify the section",
                                    },
                                },
                                "required": ["name", "description"],
                            },
                            "description": "Configuration options for processing the document",
                        },
                        "split_rules": {
                            "type": "string",
                            "description": "Rules for splitting the document, defaults to 'Split the document into the applicable sections. Sections may only overlap at their first and last page if at all.'",
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "ocr_mode": {
                                    "type": "string",
                                    "enum": ["standard", "premium", "none"],
                                    "description": "OCR mode to use",
                                },
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["ocr", "pdf", "auto"],
                                    "description": "Mode for extracting text from PDF",
                                },
                            },
                        },
                        "advanced_options": {
                            "type": "object",
                            "properties": {
                                "ocr_system": {
                                    "type": "string",
                                    "enum": ["highres", "standard"],
                                    "description": "OCR system to use",
                                },
                                "table_output_format": {
                                    "type": "string",
                                    "enum": ["html", "markdown"],
                                    "description": "Format for table output",
                                },
                                "page_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {
                                            "type": "integer",
                                            "description": "Starting page",
                                        },
                                        "end": {
                                            "type": "integer",
                                            "description": "Ending page",
                                        },
                                    },
                                    "description": "Range of pages to process",
                                },
                                "document_password": {
                                    "type": "string",
                                    "description": "Password for protected PDF",
                                },
                            },
                        },
                        "priority": {
                            "type": "boolean",
                            "description": "Whether to process with priority, default is false for async jobs",
                        },
                        "webhook": {
                            "type": "object",
                            "properties": {
                                "mode": {
                                    "type": "string",
                                    "enum": ["disabled", "enabled"],
                                    "description": "Webhook mode",
                                },
                                "url": {"type": "string", "description": "Webhook URL"},
                                "metadata": {
                                    "type": "object",
                                    "description": "Metadata to include in webhook",
                                },
                                "channels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Channels for the webhook",
                                },
                            },
                        },
                    },
                    "required": ["document_url", "split_description"],
                },
            ),
            Tool(
                name="parse_document",
                description="Parse a document to extract its content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_url": {
                            "type": "string",
                            "description": "URL of the document to be processed (public URL, presigned S3 URL, or reducto:// URL obtained from upload)",
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "ocr_mode": {
                                    "type": "string",
                                    "enum": ["standard", "premium", "none"],
                                    "description": "OCR mode to use",
                                },
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["ocr", "pdf", "auto"],
                                    "description": "Mode for extracting text from PDF",
                                },
                                "chunking": {
                                    "type": "object",
                                    "properties": {
                                        "chunk_mode": {
                                            "type": "string",
                                            "enum": ["fixed", "variable"],
                                            "description": "Mode for splitting content into chunks",
                                        },
                                        "chunk_size": {
                                            "type": "integer",
                                            "description": "Size of chunks",
                                        },
                                    },
                                },
                                "filter_blocks": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Types of blocks to filter out (e.g., 'Page Number', 'Header', 'Footer')",
                                },
                            },
                        },
                        "advanced_options": {
                            "type": "object",
                            "properties": {
                                "ocr_system": {
                                    "type": "string",
                                    "enum": ["highres", "standard"],
                                    "description": "OCR system to use",
                                },
                                "table_output_format": {
                                    "type": "string",
                                    "enum": ["html", "markdown"],
                                    "description": "Format for table output",
                                },
                                "page_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {
                                            "type": "integer",
                                            "description": "Starting page",
                                        },
                                        "end": {
                                            "type": "integer",
                                            "description": "Ending page",
                                        },
                                    },
                                    "description": "Range of pages to process",
                                },
                                "document_password": {
                                    "type": "string",
                                    "description": "Password for protected PDF",
                                },
                            },
                        },
                        "priority": {
                            "type": "boolean",
                            "description": "Whether to process with priority, default is true",
                        },
                    },
                    "required": ["document_url"],
                },
            ),
            Tool(
                name="parse_document_async",
                description="Parse a document asynchronously to extract its content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_url": {
                            "type": "string",
                            "description": "URL of the document to be processed (public URL, presigned S3 URL, or reducto:// URL obtained from upload)",
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "ocr_mode": {
                                    "type": "string",
                                    "enum": ["standard", "premium", "none"],
                                    "description": "OCR mode to use",
                                },
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["ocr", "pdf", "auto"],
                                    "description": "Mode for extracting text from PDF",
                                },
                                "chunking": {
                                    "type": "object",
                                    "properties": {
                                        "chunk_mode": {
                                            "type": "string",
                                            "enum": ["fixed", "variable"],
                                            "description": "Mode for splitting content into chunks",
                                        },
                                        "chunk_size": {
                                            "type": "integer",
                                            "description": "Size of chunks",
                                        },
                                    },
                                },
                                "filter_blocks": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Types of blocks to filter out (e.g., 'Page Number', 'Header', 'Footer')",
                                },
                            },
                        },
                        "advanced_options": {
                            "type": "object",
                            "properties": {
                                "ocr_system": {
                                    "type": "string",
                                    "enum": ["highres", "standard"],
                                    "description": "OCR system to use",
                                },
                                "table_output_format": {
                                    "type": "string",
                                    "enum": ["html", "markdown"],
                                    "description": "Format for table output",
                                },
                                "page_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {
                                            "type": "integer",
                                            "description": "Starting page",
                                        },
                                        "end": {
                                            "type": "integer",
                                            "description": "Ending page",
                                        },
                                    },
                                    "description": "Range of pages to process",
                                },
                                "document_password": {
                                    "type": "string",
                                    "description": "Password for protected PDF",
                                },
                            },
                        },
                        "priority": {
                            "type": "boolean",
                            "description": "Whether to process with priority, default is false for async jobs",
                        },
                        "webhook": {
                            "type": "object",
                            "properties": {
                                "mode": {
                                    "type": "string",
                                    "enum": ["disabled", "enabled"],
                                    "description": "Webhook mode",
                                },
                                "url": {"type": "string", "description": "Webhook URL"},
                                "metadata": {
                                    "type": "object",
                                    "description": "Metadata to include in webhook",
                                },
                                "channels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Channels for the webhook",
                                },
                            },
                        },
                    },
                    "required": ["document_url"],
                },
            ),
            Tool(
                name="extract_data",
                description="Extract structured data from a document based on a provided schema",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_url": {
                            "type": "string",
                            "description": "URL of the document to be processed (public URL, presigned S3 URL, reducto:// URL, or a job_id with jobid:// prefix)",
                        },
                        "schema": {
                            "type": "object",
                            "description": "JSON schema defining the structure of data to extract",
                        },
                        "system_prompt": {
                            "type": "string",
                            "description": "System prompt for the extraction, defaults to 'Be precise and thorough.'",
                        },
                        "generate_citations": {
                            "type": "boolean",
                            "description": "Whether to generate citations for extracted content, default is false",
                        },
                        "use_chunking": {
                            "type": "boolean",
                            "description": "Whether to use chunking for extraction, default is false",
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "ocr_mode": {
                                    "type": "string",
                                    "enum": ["standard", "premium", "none"],
                                    "description": "OCR mode to use",
                                },
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["ocr", "pdf", "auto"],
                                    "description": "Mode for extracting text from PDF",
                                },
                            },
                        },
                        "advanced_options": {
                            "type": "object",
                            "properties": {
                                "ocr_system": {
                                    "type": "string",
                                    "enum": ["highres", "standard"],
                                    "description": "OCR system to use",
                                },
                                "table_output_format": {
                                    "type": "string",
                                    "enum": ["html", "markdown"],
                                    "description": "Format for table output",
                                },
                                "page_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {
                                            "type": "integer",
                                            "description": "Starting page",
                                        },
                                        "end": {
                                            "type": "integer",
                                            "description": "Ending page",
                                        },
                                    },
                                    "description": "Range of pages to process",
                                },
                                "document_password": {
                                    "type": "string",
                                    "description": "Password for protected PDF",
                                },
                            },
                        },
                        "priority": {
                            "type": "boolean",
                            "description": "Whether to process with priority, default is true",
                        },
                    },
                    "required": ["document_url", "schema"],
                },
            ),
            Tool(
                name="extract_data_async",
                description="Extract structured data asynchronously from a document based on a provided schema",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_url": {
                            "type": "string",
                            "description": "URL of the document to be processed (public URL, presigned S3 URL, reducto:// URL, or a job_id with jobid:// prefix)",
                        },
                        "schema": {
                            "type": "object",
                            "description": "JSON schema defining the structure of data to extract",
                        },
                        "system_prompt": {
                            "type": "string",
                            "description": "System prompt for the extraction, defaults to 'Be precise and thorough.'",
                        },
                        "generate_citations": {
                            "type": "boolean",
                            "description": "Whether to generate citations for extracted content, default is false",
                        },
                        "use_chunking": {
                            "type": "boolean",
                            "description": "Whether to use chunking for extraction, default is false",
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "ocr_mode": {
                                    "type": "string",
                                    "enum": ["standard", "premium", "none"],
                                    "description": "OCR mode to use",
                                },
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["ocr", "pdf", "auto"],
                                    "description": "Mode for extracting text from PDF",
                                },
                            },
                        },
                        "advanced_options": {
                            "type": "object",
                            "properties": {
                                "ocr_system": {
                                    "type": "string",
                                    "enum": ["highres", "standard"],
                                    "description": "OCR system to use",
                                },
                                "table_output_format": {
                                    "type": "string",
                                    "enum": ["html", "markdown"],
                                    "description": "Format for table output",
                                },
                                "page_range": {
                                    "type": "object",
                                    "properties": {
                                        "start": {
                                            "type": "integer",
                                            "description": "Starting page",
                                        },
                                        "end": {
                                            "type": "integer",
                                            "description": "Ending page",
                                        },
                                    },
                                    "description": "Range of pages to process",
                                },
                                "document_password": {
                                    "type": "string",
                                    "description": "Password for protected PDF",
                                },
                            },
                        },
                        "priority": {
                            "type": "boolean",
                            "description": "Whether to process with priority, default is false for async jobs",
                        },
                        "webhook": {
                            "type": "object",
                            "properties": {
                                "mode": {
                                    "type": "string",
                                    "enum": ["disabled", "enabled"],
                                    "description": "Webhook mode",
                                },
                                "url": {"type": "string", "description": "Webhook URL"},
                                "metadata": {
                                    "type": "object",
                                    "description": "Metadata to include in webhook",
                                },
                                "channels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Channels for the webhook",
                                },
                            },
                        },
                    },
                    "required": ["document_url", "schema"],
                },
            ),
            Tool(
                name="get_job_status",
                description="Check the status of an asynchronous job",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "ID of the job to check",
                        }
                    },
                    "required": ["job_id"],
                },
            ),
            Tool(
                name="cancel_job",
                description="Cancel an ongoing job",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "ID of the job to cancel",
                        }
                    },
                    "required": ["job_id"],
                },
            ),
            Tool(
                name="upload_document",
                description="Upload a document to Reducto",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Local path to the file to upload",
                        },
                        "extension": {
                            "type": "string",
                            "description": "File extension to use",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="get_version",
                description="Get the Reducto API version",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="webhook_portal",
                description="Configure webhook portal for receiving job notifications",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        api_key = await get_reducto_credentials(server.user_id, server.api_key)
        arguments = arguments or {}

        endpoints = {
            "split_document": {"method": "post", "endpoint": "split"},
            "split_document_async": {"method": "post", "endpoint": "split_async"},
            "parse_document": {"method": "post", "endpoint": "parse"},
            "parse_document_async": {"method": "post", "endpoint": "parse_async"},
            "extract_data": {"method": "post", "endpoint": "extract"},
            "extract_data_async": {"method": "post", "endpoint": "extract_async"},
            "get_job_status": {
                "method": "get",
                "endpoint": lambda args: f"job/{args['job_id']}",
            },
            "cancel_job": {
                "method": "post",
                "endpoint": lambda args: f"cancel/{args['job_id']}",
            },
            "get_version": {"method": "get", "endpoint": "version"},
            "webhook_portal": {"method": "post", "endpoint": "configure_webhook"},
        }

        try:
            if name == "upload_document":
                file_path = arguments.get("file_path")
                if not file_path or not os.path.exists(file_path):
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: File not found at path {file_path}",
                        )
                    ]

                params = {}
                if "extension" in arguments:
                    params["extension"] = arguments["extension"]

                with open(file_path, "rb") as file:
                    files = {"file": (os.path.basename(file_path), file)}
                    response = await make_reducto_request(
                        "post", "upload", api_key=api_key, params=params, files=files
                    )
            elif name in endpoints:
                endpoint_info = endpoints[name]
                method = endpoint_info["method"]
                endpoint = endpoint_info["endpoint"]

                if callable(endpoint):
                    endpoint = endpoint(arguments)

                response = await make_reducto_request(
                    method, endpoint, arguments, api_key
                )
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            status_code = response.get("_status_code", 0)
            if 200 <= status_code < 300:
                return [
                    TextContent(
                        type="text",
                        text=f"Operation successful. Response: {json.dumps(response, indent=2)}",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Error (Status {status_code}): {json.dumps(response, indent=2)}",
                    )
                ]

        except Exception as e:
            logger.error(f"Error in tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error using {name} tool: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="reducto-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_reducto_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
