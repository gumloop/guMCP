import os
import sys
import httpx

from typing import List, Dict

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path

from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client


SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

# Supported models
PERPLEXITY_MODELS = [
    "sonar",
    "sonar-pro",
    "sonar-deep-research",
    "sonar-reasoning",
    "sonar-reasoning-pro",
]

# Recency filters for search
RECENCY_FILTERS = [
    "hour",
    "day",
    "week",
    "month",
    "year",
    "none",
]


def authenticate_and_save_perplexity_key(user_id):
    """Authenticate with Perplexity and save API key"""
    logger = logging.getLogger("perplexity")

    logger.info(f"Starting Perplexity authentication for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your Perplexity API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials("perplexity", user_id, {"api_key": api_key})

    logger.info(
        f"Perplexity API key saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_perplexity_credentials(user_id, api_key=None):
    """Get Perplexity API key for the specified user"""
    logger = logging.getLogger("perplexity")

    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials("perplexity", user_id)

    def handle_missing_credentials():
        error_str = f"Perplexity API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    api_key = (
        credentials_data.get("api_key")
        # In the case of GumloopAuthClient, api key is returned directly
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("perplexity-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_prompts()
    async def handle_list_prompts() -> list[Prompt]:
        """List available prompts"""
        logger.info(f"Listing prompts for user: {server.user_id}")

        return [
            Prompt(
                name="search_with_recency",
                description="Search with Perplexity and filter by time range",
                arguments=[
                    PromptArgument(
                        name="query", description="The search query", required=True
                    ),
                    PromptArgument(
                        name="recency",
                        description="Time filter (hour, day, week, month, year, none)",
                        required=False,
                    ),
                ],
            ),
            Prompt(
                name="code_assistant",
                description="Get coding help from Perplexity's code model",
                arguments=[
                    PromptArgument(
                        name="problem",
                        description="The coding problem or question",
                        required=True,
                    ),
                    PromptArgument(
                        name="language",
                        description="Programming language",
                        required=False,
                    ),
                ],
            ),
        ]

    @server.get_prompt()
    async def handle_get_prompt(
        name: str, arguments: Dict[str, str] | None = None
    ) -> GetPromptResult:
        """Get a specific prompt with arguments"""
        logger.info(
            f"Getting prompt {name} with arguments {arguments} for user: {server.user_id}"
        )

        if not arguments:
            arguments = {}

        if name == "search_with_recency":
            query = arguments.get("query", "")
            recency = arguments.get("recency", "none")

            if recency not in RECENCY_FILTERS:
                recency = "none"

            system_message = "You're a helpful assistant providing accurate information based on web search results."
            user_message = f"Search for: {query}"

            if recency != "none":
                user_message += f" (from the past {recency})"

            return GetPromptResult(
                description=f"Search for {query} with {recency} recency filter",
                messages=[
                    PromptMessage(
                        role="system",
                        content=TextContent(type="text", text=system_message),
                    ),
                    PromptMessage(
                        role="user", content=TextContent(type="text", text=user_message)
                    ),
                ],
            )

        elif name == "code_assistant":
            problem = arguments.get("problem", "")
            language = arguments.get("language", "")

            system_message = "You're a skilled programming assistant. Provide clear, efficient, and well-documented code examples."
            user_message = problem

            if language:
                user_message = (
                    f"I need help with this {language} code problem: {problem}"
                )

            return GetPromptResult(
                description=f"Get coding help for {language}",
                messages=[
                    PromptMessage(
                        role="system",
                        content=TextContent(type="text", text=system_message),
                    ),
                    PromptMessage(
                        role="user", content=TextContent(type="text", text=user_message)
                    ),
                ],
            )

        raise ValueError(f"Unknown prompt: {name}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")

        return [
            Tool(
                name="search",
                description="Search the web using Perplexity's API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "model": {
                            "type": "string",
                            "description": f"The model to use: {', '.join(PERPLEXITY_MODELS)}",
                            "enum": PERPLEXITY_MODELS,
                        },
                        "recency_filter": {
                            "type": "string",
                            "description": "Filter results by time",
                            "enum": RECENCY_FILTERS,
                        },
                        "return_related": {
                            "type": "boolean",
                            "description": "Whether to return related questions",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="chat",
                description="Send a message to Perplexity model without forcing web search",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message to send to the model",
                        },
                        "model": {
                            "type": "string",
                            "description": f"The model to use: {', '.join(PERPLEXITY_MODELS)}",
                            "enum": PERPLEXITY_MODELS,
                        },
                        "system_prompt": {
                            "type": "string",
                            "description": "Optional system prompt",
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Randomness of responses (0-2)",
                            "minimum": 0,
                            "maximum": 2,
                        },
                    },
                    "required": ["message"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        api_key = await get_perplexity_credentials(
            server.user_id, api_key=server.api_key
        )

        if not api_key:
            return [
                TextContent(
                    type="text",
                    text="Error: Perplexity API key not provided. Please configure your API key.",
                )
            ]

        if not arguments:
            return [TextContent(type="text", text="Error: No arguments provided.")]

        if name == "search":
            query = arguments.get("query")
            if not query:
                return [TextContent(type="text", text="Error: Missing query parameter")]

            model = arguments.get("model", "sonar")
            recency_filter = arguments.get("recency_filter", None)
            return_related = arguments.get("return_related", False)

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }

                    data = {
                        "model": model,
                        "messages": [{"role": "user", "content": query}],
                        "return_related_questions": return_related,
                        "web_search_options": {"search_context_size": "high"},
                    }

                    if recency_filter:
                        data["search_recency_filter"] = recency_filter

                    response = await client.post(
                        "https://api.perplexity.ai/chat/completions",
                        headers=headers,
                        json=data,
                    )

                    if response.status_code != 200:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error: Perplexity API returned status code {response.status_code}: {response.text}",
                            )
                        ]

                    result = response.json()
                    answer_text = (
                        result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "No response generated")
                    )

                    response_text = answer_text

                    # Add related questions if available and requested
                    if return_related and "related_questions" in result:
                        related = result["related_questions"]
                        if related and len(related) > 0:
                            response_text += "\n\n**Related Questions:**\n"
                            for q in related:
                                response_text += f"- {q}\n"

                    return [TextContent(type="text", text=response_text)]

            except Exception as e:
                logger.error(f"Error during Perplexity search: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        elif name == "chat":
            message = arguments.get("message")
            if not message:
                return [
                    TextContent(type="text", text="Error: Missing message parameter")
                ]

            model = arguments.get("model", "sonar")
            system_prompt = arguments.get(
                "system_prompt", "Be helpful, concise, and precise."
            )
            temperature = arguments.get("temperature", 0.7)

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    }

                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})

                    messages.append({"role": "user", "content": message})

                    data = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "web_search_options": {"search_context_size": "medium"},
                    }

                    response = await client.post(
                        "https://api.perplexity.ai/chat/completions",
                        headers=headers,
                        json=data,
                    )

                    if response.status_code != 200:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error: Perplexity API returned status code {response.status_code}: {response.text}",
                            )
                        ]

                    result = response.json()
                    answer_text = (
                        result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "No response generated")
                    )

                    return [TextContent(type="text", text=answer_text)]

            except Exception as e:
                logger.error(f"Error during Perplexity chat: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="perplexity-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_perplexity_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
