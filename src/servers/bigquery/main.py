import sys
import logging
import json
import os
from pathlib import Path

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)


from src.utils.google.util import authenticate_and_save_credentials, get_credentials

from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/cloud-platform",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_bigquery_client(user_id, api_key=None):
    """Create a new BigQuery client instance for this request"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return bigquery.Client(credentials=credentials)


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("bigquery-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for BigQuery operations"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            # QUERY TOOLS
            # Tools for executing queries and retrieving data
            types.Tool(
                name="run_query",
                description="Execute a SQL query on BigQuery and return formatted results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL query to execute on BigQuery",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 100)",
                        },
                        "use_legacy_sql": {
                            "type": "boolean",
                            "description": "Whether to use legacy SQL syntax (default: false)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            # DATASET MANAGEMENT TOOLS
            # Tools for working with datasets
            types.Tool(
                name="list_datasets",
                description="List all available datasets in the BigQuery project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Optional project ID to list datasets from (defaults to authenticated project)",
                        },
                        "include_all": {
                            "type": "boolean",
                            "description": "Whether to list datasets from all projects (default: false)",
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="get_dataset_info",
                description="Get detailed information about a specific dataset",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "The dataset ID to get information about",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Optional project ID (defaults to authenticated project)",
                        },
                    },
                    "required": ["dataset_id"],
                },
            ),
            # TABLE MANAGEMENT TOOLS
            # Tools for working with tables
            types.Tool(
                name="list_tables",
                description="List tables within a specific dataset",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "Dataset ID to list tables from",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Optional project ID (defaults to authenticated project)",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of tables to return",
                        },
                    },
                    "required": ["dataset_id"],
                },
            ),
            types.Tool(
                name="get_table_schema",
                description="Get the schema details of a specific table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "Dataset ID containing the table",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "Table ID to get schema for",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Optional project ID (defaults to authenticated project)",
                        },
                    },
                    "required": ["dataset_id", "table_id"],
                },
            ),
            types.Tool(
                name="preview_table_data",
                description="Preview data from a table (first rows)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "Dataset ID containing the table",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "Table ID to preview data from",
                        },
                        "max_rows": {
                            "type": "integer",
                            "description": "Maximum number of rows to return (default: 10)",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Optional project ID (defaults to authenticated project)",
                        },
                    },
                    "required": ["dataset_id", "table_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle BigQuery tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        # Handle case where arguments is None or not a dictionary
        if arguments is None:
            arguments = {}

        try:
            # Create authenticated BigQuery client
            client = await create_bigquery_client(
                server.user_id, api_key=server.api_key
            )

            # QUERY TOOLS
            if name == "run_query":
                if "query" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter 'query'",
                        )
                    ]

                query = arguments["query"]
                max_results = arguments.get("max_results", 100)
                use_legacy_sql = arguments.get("use_legacy_sql", False)

                logger.info(f"Executing query: {query}")
                logger.info(f"Max results: {max_results}, Legacy SQL: {use_legacy_sql}")

                # Configure job options
                job_config = bigquery.QueryJobConfig(use_legacy_sql=use_legacy_sql)

                try:
                    # Execute the query
                    query_job = client.query(query, job_config=job_config)
                    rows_iterator = query_job.result(max_results=max_results)

                    # Convert to list for easier processing
                    rows = list(rows_iterator)

                    if not rows:
                        return [
                            TextContent(
                                type="text",
                                text="Query executed successfully but returned no results.",
                            )
                        ]

                    # Get column names
                    column_names = [field.name for field in rows_iterator.schema]

                    # Format results as a table
                    result_text = " | ".join(column_names) + "\n"
                    result_text += "-" * len(result_text) + "\n"

                    for row in rows:
                        row_values = [str(row[col]) for col in column_names]
                        result_text += " | ".join(row_values) + "\n"

                    # Add query statistics
                    bytes_processed = query_job.total_bytes_processed
                    elapsed_time = query_job.ended - query_job.started

                    result_text += f"\nTotal results: {len(rows)}"
                    result_text += f"\nBytes processed: {bytes_processed:,}"
                    result_text += (
                        f"\nQuery duration: {elapsed_time.total_seconds():.2f} seconds"
                    )

                    return [TextContent(type="text", text=result_text)]

                except GoogleAPIError as e:
                    error_message = f"Query execution failed: {str(e)}"
                    logger.error(error_message)
                    return [TextContent(type="text", text=f"Error: {error_message}")]

            # DATASET MANAGEMENT TOOLS
            elif name == "list_datasets":
                project_id = arguments.get("project_id")  # None is fine - uses default
                include_all = arguments.get("include_all", False)

                logger.info(
                    f"Listing datasets with project_id={project_id}, include_all={include_all}"
                )

                try:
                    # List datasets
                    datasets = list(
                        client.list_datasets(
                            project=project_id, include_all=include_all
                        )
                    )

                    if not datasets:
                        return [
                            TextContent(
                                type="text",
                                text="No datasets found in the specified project.",
                            )
                        ]

                    # Format dataset information
                    dataset_info = []
                    for dataset in datasets:
                        dataset_info.append(
                            {
                                "dataset_id": dataset.dataset_id,
                                "project_id": dataset.project,
                                "location": dataset.location,
                                "full_dataset_id": f"{dataset.project}.{dataset.dataset_id}",
                            }
                        )

                    # Build response with the total count and formatted dataset list
                    result = {
                        "total_datasets": len(dataset_info),
                        "datasets": dataset_info,
                    }

                    return [
                        TextContent(
                            type="text",
                            text=f"Successfully retrieved {len(dataset_info)} datasets:\n{json.dumps(result, indent=2)}",
                        )
                    ]

                except GoogleAPIError as e:
                    error_message = f"Error listing datasets: {str(e)}"
                    logger.error(error_message)
                    return [TextContent(type="text", text=f"Error: {error_message}")]

            elif name == "get_dataset_info":
                if "dataset_id" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter 'dataset_id'",
                        )
                    ]

                dataset_id = arguments["dataset_id"]
                project_id = arguments.get("project_id")  # None is fine - uses default

                logger.info(
                    f"Getting dataset info for {dataset_id} in project {project_id}"
                )

                try:
                    # Get dataset reference
                    dataset_ref = client.dataset(dataset_id, project=project_id)

                    # Get the dataset
                    dataset = client.get_dataset(dataset_ref)

                    # Format dataset information
                    dataset_info = {
                        "id": dataset.dataset_id,
                        "project_id": dataset.project,
                        "full_dataset_id": dataset.full_dataset_id,
                        "friendly_name": dataset.friendly_name,
                        "description": dataset.description,
                        "location": dataset.location,
                        "labels": dataset.labels,
                        "created": dataset.created.isoformat(),
                        "modified": dataset.modified.isoformat(),
                        "default_table_expiration_ms": dataset.default_table_expiration_ms,
                    }

                    return [
                        TextContent(
                            type="text",
                            text=f"Dataset information for '{dataset_id}':\n{json.dumps(dataset_info, indent=2)}",
                        )
                    ]

                except GoogleAPIError as e:
                    error_message = f"Error retrieving dataset information: {str(e)}"
                    logger.error(error_message)
                    return [TextContent(type="text", text=f"Error: {error_message}")]

            # TABLE MANAGEMENT TOOLS
            elif name == "list_tables":
                if "dataset_id" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter 'dataset_id'",
                        )
                    ]

                dataset_id = arguments["dataset_id"]
                project_id = arguments.get("project_id")  # None is fine - uses default
                max_results = arguments.get("max_results")

                logger.info(
                    f"Listing tables in dataset {dataset_id}, project {project_id}"
                )

                try:
                    # Get dataset reference
                    dataset_ref = client.dataset(dataset_id, project=project_id)

                    # List tables
                    tables = list(
                        client.list_tables(dataset_ref, max_results=max_results)
                    )

                    if not tables:
                        return [
                            TextContent(
                                type="text",
                                text=f"No tables found in dataset '{dataset_id}'.",
                            )
                        ]

                    # Format table information
                    table_info = []
                    for table in tables:
                        table_info.append(
                            {
                                "table_id": table.table_id,
                                "dataset_id": table.dataset_id,
                                "project_id": table.project,
                                "full_table_id": f"{table.project}.{table.dataset_id}.{table.table_id}",
                                "table_type": table.table_type,
                            }
                        )

                    # Build response with the total count and formatted table list
                    result = {
                        "dataset_id": dataset_id,
                        "project_id": project_id or client.project,
                        "total_tables": len(table_info),
                        "tables": table_info,
                    }

                    return [
                        TextContent(
                            type="text",
                            text=f"Successfully retrieved {len(table_info)} tables from dataset '{dataset_id}':\n{json.dumps(result, indent=2)}",
                        )
                    ]

                except GoogleAPIError as e:
                    error_message = f"Error listing tables: {str(e)}"
                    logger.error(error_message)
                    return [TextContent(type="text", text=f"Error: {error_message}")]

            elif name == "get_table_schema":
                if "dataset_id" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter 'dataset_id'",
                        )
                    ]
                if "table_id" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter 'table_id'",
                        )
                    ]

                dataset_id = arguments["dataset_id"]
                table_id = arguments["table_id"]
                project_id = arguments.get("project_id")  # None is fine - uses default

                logger.info(
                    f"Getting table schema for {dataset_id}.{table_id} in project {project_id}"
                )

                try:
                    # Get table reference
                    table_ref = client.dataset(dataset_id, project=project_id).table(
                        table_id
                    )

                    # Get the table
                    table = client.get_table(table_ref)

                    # Format schema information
                    schema_fields = []
                    for field in table.schema:
                        field_info = {
                            "name": field.name,
                            "field_type": field.field_type,
                            "mode": field.mode,
                            "description": field.description,
                        }

                        # Handle nested fields
                        if field.fields:
                            nested_fields = []
                            for nested_field in field.fields:
                                nested_fields.append(
                                    {
                                        "name": nested_field.name,
                                        "field_type": nested_field.field_type,
                                        "mode": nested_field.mode,
                                        "description": nested_field.description,
                                    }
                                )
                            field_info["nested_fields"] = nested_fields

                        schema_fields.append(field_info)

                    # Include table metadata
                    table_info = {
                        "table_id": table.table_id,
                        "dataset_id": table.dataset_id,
                        "project_id": table.project,
                        "full_table_id": table.full_table_id,
                        "description": table.description,
                        "num_rows": table.num_rows,
                        "num_bytes": table.num_bytes,
                        "created": table.created.isoformat() if table.created else None,
                        "modified": (
                            table.modified.isoformat() if table.modified else None
                        ),
                        "schema": schema_fields,
                    }

                    return [
                        TextContent(
                            type="text",
                            text=f"Table schema for '{table_id}':\n{json.dumps(table_info, indent=2)}",
                        )
                    ]

                except GoogleAPIError as e:
                    error_message = f"Error retrieving table schema: {str(e)}"
                    logger.error(error_message)
                    return [TextContent(type="text", text=f"Error: {error_message}")]

            elif name == "preview_table_data":
                if "dataset_id" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter 'dataset_id'",
                        )
                    ]
                if "table_id" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter 'table_id'",
                        )
                    ]

                dataset_id = arguments["dataset_id"]
                table_id = arguments["table_id"]
                max_rows = arguments.get("max_rows", 10)
                project_id = arguments.get("project_id")  # None is fine - uses default

                logger.info(
                    f"Previewing {max_rows} rows from {dataset_id}.{table_id} in project {project_id}"
                )

                try:
                    # Construct the query
                    query = f"SELECT * FROM `{project_id or client.project}.{dataset_id}.{table_id}` LIMIT {max_rows}"

                    # Execute the query
                    query_job = client.query(query)
                    rows_iterator = query_job.result()

                    # Convert to list for easier processing
                    rows = list(rows_iterator)

                    if not rows:
                        return [
                            TextContent(
                                type="text",
                                text=f"Table '{table_id}' exists but contains no data.",
                            )
                        ]

                    # Get column names
                    column_names = [field.name for field in rows_iterator.schema]

                    # Format results as a table and as structured data
                    result_rows = []
                    for row in rows:
                        row_dict = {column: str(row[column]) for column in column_names}
                        result_rows.append(row_dict)

                    # Build response with preview data
                    result = {
                        "dataset_id": dataset_id,
                        "table_id": table_id,
                        "project_id": project_id or client.project,
                        "preview_count": len(result_rows),
                        "columns": column_names,
                        "preview_rows": result_rows,
                    }

                    return [
                        TextContent(
                            type="text",
                            text=f"Data preview for '{dataset_id}.{table_id}':\n{json.dumps(result, indent=2)}",
                        )
                    ]

                except GoogleAPIError as e:
                    error_message = f"Error previewing table data: {str(e)}"
                    logger.error(error_message)
                    return [TextContent(type="text", text=f"Error: {error_message}")]

            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}. Please use one of the available tools.",
                    )
                ]

        except Exception as e:
            logger.error(f"Error in BigQuery tool execution: {str(e)}")
            return [
                TextContent(type="text", text=f"An unexpected error occurred: {str(e)}")
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="bigquery-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
