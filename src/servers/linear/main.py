import os
import sys
from typing import Optional, Iterable, Dict, Any

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
import json
from pathlib import Path

from mcp.types import (
    AnyUrl,
    Resource,
    TextContent,
    Tool,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from src.auth.factory import create_auth_client
from src.utils.oauth.util import run_oauth_flow, refresh_token_if_needed

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["read", "write", "issues:create"]  # Linear OAuth scopes

# Linear OAuth configuration
LINEAR_OAUTH_AUTHORIZE_URL = "https://linear.app/oauth/authorize"
LINEAR_OAUTH_TOKEN_URL = "https://api.linear.app/oauth/token"
LINEAR_API_GRAPHQL = "https://api.linear.app/graphql"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


class LinearClient:
    """Client for interacting with Linear API"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = self._create_client()

    def _create_client(self) -> Client:
        """Create a GQL client for Linear API"""
        transport = RequestsHTTPTransport(
            url=LINEAR_API_GRAPHQL,
            headers={"Authorization": f"Bearer {self.access_token}"},
            use_json=True,
        )
        return Client(transport=transport, fetch_schema_from_transport=True)

    def execute(self, query: str, variable_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against Linear API"""
        return self.client.execute(gql(query), variable_values=variable_values)


def linear_auth_params_builder(oauth_config: Dict[str, Any], redirect_uri: str, scopes: list) -> Dict[str, str]:
    """Build authorization parameters for Linear OAuth"""
    return {
        "client_id": oauth_config["client_id"],
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "response_type": "code"
    }


def linear_token_data_builder(
    oauth_config: Dict[str, Any], redirect_uri: str, scopes: list, code: str
) -> Dict[str, str]:
    """Build token request data for Linear OAuth"""
    return {
        "client_id": oauth_config["client_id"],
        "client_secret": oauth_config["client_secret"],
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }


def linear_refresh_token_data_builder(
    oauth_config: Dict[str, Any], refresh_token: str, credentials_data: Dict[str, Any]
) -> Dict[str, str]:
    """Build refresh token request data for Linear OAuth"""
    return {
        "client_id": oauth_config["client_id"],
        "client_secret": oauth_config["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }


def authenticate_and_save_credentials(user_id: str, service_name: str, scopes: list) -> Dict[str, Any]:
    """Authenticate with Linear and save credentials"""
    return run_oauth_flow(
        service_name=service_name,
        user_id=user_id,
        scopes=scopes,
        auth_url_base=LINEAR_OAUTH_AUTHORIZE_URL,
        token_url=LINEAR_OAUTH_TOKEN_URL,
        auth_params_builder=linear_auth_params_builder,
        token_data_builder=linear_token_data_builder
    )


async def get_linear_client(user_id: str, api_key: Optional[str] = None) -> LinearClient:
    """Get a Linear client for the specified user"""
    logger = logging.getLogger("linear")

    # Use the global OAuth utility to get and refresh the token if needed
    access_token = await refresh_token_if_needed(
        user_id=user_id,
        service_name="linear",
        token_url=LINEAR_OAUTH_TOKEN_URL,
        token_data_builder=linear_refresh_token_data_builder,
        api_key=api_key
    )

    if not access_token:
        error_str = f"Credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run with 'auth' argument first."
        logging.error(error_str)
        raise ValueError(f"Credentials not found for user {user_id}")

    return LinearClient(access_token)


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("linear-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List issues from Linear"""
        logger.info(
            f"Listing issues for user: {server.user_id} with cursor: {cursor}"
        )

        linear_client = await get_linear_client(server.user_id, server.api_key)
        print(linear_client)
        
        page_size = 10
        query = """
        query($cursor: String) {
            issues(first: %d, after: $cursor) {
                nodes {
                    id
                    title
                    identifier
                    state {
                        name
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """ % page_size

        result = linear_client.execute(query, variable_values={"cursor": cursor})
        issues = result.get("issues", {}).get("nodes", [])

        resources = []
        for issue in issues:
            resource = Resource(
                uri=f"linear:///{issue['id']}",
                mimeType="application/linear.issue+json",
                name=f"{issue['identifier']}: {issue['title']}",
            )
            resources.append(resource)

        return resources


    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read an issue from Linear by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        linear_client = await get_linear_client(server.user_id, server.api_key)
        issue_id = str(uri).replace("linear:///", "")

        query = """
        query($issueId: String!) {
            issue(id: $issueId) {
                id
                title
                identifier
                description
                url
                state {
                    name
                }
                assignee {
                    name
                }
                priority
                labels {
                    nodes {
                        name
                    }
                }
                team {
                    name
                }
            }
        }
        """

        try:
            result = linear_client.execute(query, variable_values={"issueId": issue_id})
            issue = result.get("issue", {})

            if not issue:
                raise ValueError(f"Issue not found: {issue_id}")

            # Format issue data
            formatted_issue = {
                "id": issue["id"],
                "title": issue["title"],
                "identifier": issue["identifier"],
                "description": issue.get("description", ""),
                "url": issue["url"],
                "status": issue.get("state", {}).get("name", ""),
                "assignee": issue.get("assignee", {}).get("name", "Unassigned"),
                "priority": issue.get("priority", 0),
                "labels": [label["name"] for label in issue.get("labels", {}).get("nodes", [])],
                "team": issue.get("team", {}).get("name", ""),
            }

            # Return as JSON
            json_content = json.dumps(formatted_issue, indent=2)
            mime_type = "application/json"

            return [ReadResourceContents(content=json_content, mime_type=mime_type)]
        except Exception as e:
            logger.error(f"Error reading issue {issue_id}: {str(e)}")
            # Return an error message instead of None
            error_content = json.dumps({"error": str(e)}, indent=2)
            return [ReadResourceContents(content=error_content, mime_type="application/json")]


    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="create_issue",
                description="Create a new issue in Linear",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Issue title"},
                        "description": {"type": "string", "description": "Issue description"},
                        "team_id": {"type": "string", "description": "Team ID (optional)"},
                        "assignee_id": {"type": "string", "description": "Assignee ID (optional)"},
                        "priority": {"type": "integer", "description": "Priority (0-4, optional)"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Label IDs (optional)"},
                        "state_id": {"type": "string", "description": "State ID (optional)"}
                    },
                    "required": ["title", "description"],
                },
            ),
            Tool(
                name="search_issues",
                description="Search for issues in Linear",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "team_ids": {"type": "array", "items": {"type": "string"}, "description": "Filter by teams (optional)"},
                        "statuses": {"type": "array", "items": {"type": "string"}, "description": "Filter by statuses (optional)"},
                        "assignee_ids": {"type": "array", "items": {"type": "string"}, "description": "Filter by assignees (optional)"},
                        "limit": {"type": "integer", "description": "Maximum number of results (default: 10)"}
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="list_teams",
                description="List available teams in Linear workspace",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> list[TextContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        try:
            linear_client = await get_linear_client(server.user_id, server.api_key)

            if name == "create_issue":
                if not arguments or "title" not in arguments or "description" not in arguments:
                    return [
                        TextContent(
                            type="text", 
                            text="Missing required parameters: title and description"
                        )
                    ]

                # Handle team name if provided instead of ID
                if "team" in arguments and not arguments.get("team_id"):
                    team_name = arguments["team"]
                    # Get team ID from name
                    team_query = """
                    query {
                        teams {
                            nodes {
                                id
                                name
                                key
                            }
                        }
                    }
                    """
                    result = linear_client.execute(team_query)
                    teams = result.get("teams", {}).get("nodes", [])
                    
                    for team in teams:
                        if team["name"].lower() == team_name.lower():
                            arguments["team_id"] = team["id"]
                            break

                # Prepare mutation
                mutation = """
                mutation CreateIssue($input: IssueCreateInput!) {
                    issueCreate(input: $input) {
                        success
                        issue {
                            id
                            title
                            identifier
                            url
                        }
                    }
                }
                """

                # Prepare input variables
                input_vars = {
                    "title": arguments["title"],
                    "description": arguments["description"],
                }
                
                # Add optional fields if provided
                if "team_id" in arguments and arguments["team_id"]:
                    input_vars["teamId"] = arguments["team_id"]
                if "assignee_id" in arguments and arguments["assignee_id"]:
                    input_vars["assigneeId"] = arguments["assignee_id"]
                if "priority" in arguments:
                    try:
                        # Convert priority names to numbers if needed
                        priority_map = {"no priority": 0, "low": 1, "medium": 2, "high": 3, "urgent": 4}
                        if isinstance(arguments["priority"], str) and arguments["priority"].lower() in priority_map:
                            input_vars["priority"] = priority_map[arguments["priority"].lower()]
                        else:
                            input_vars["priority"] = int(arguments["priority"])
                    except (ValueError, TypeError):
                        # Default to medium priority if conversion fails
                        input_vars["priority"] = 2
                if "labels" in arguments and arguments["labels"]:
                    input_vars["labelIds"] = arguments["labels"]
                if "state_id" in arguments and arguments["state_id"]:
                    input_vars["stateId"] = arguments["state_id"]

                # Execute mutation
                result = linear_client.execute(
                    mutation, variable_values={"input": input_vars}
                )
                
                if result.get("issueCreate", {}).get("success"):
                    issue = result["issueCreate"]["issue"]
                    return [
                        TextContent(
                            type="text", 
                            text=f"Issue created successfully: {issue['identifier']} - {issue['title']}\nURL: {issue['url']}"
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text", 
                            text=f"Failed to create issue: {result.get('error', 'Unknown error')}"
                        )
                    ]

            elif name == "search_issues":
                if not arguments or "query" not in arguments:
                    return [
                        TextContent(
                            type="text", 
                            text="Missing required parameter: query"
                        )
                    ]
                    
                # Get limit parameter or use default
                limit = arguments.get("limit", 10)
                
                # Build filter conditions
                filter_conditions = [f'title: {{ contains: "{arguments["query"]}" }}']
                
                if "team_ids" in arguments and arguments["team_ids"]:
                    team_ids = [f'"{team_id}"' for team_id in arguments["team_ids"]]
                    filter_conditions.append(f'team: {{ id: {{ in: [{", ".join(team_ids)}] }} }}')
                    
                if "statuses" in arguments and arguments["statuses"]:
                    status_ids = [f'"{status}"' for status in arguments["statuses"]]
                    filter_conditions.append(f'state: {{ id: {{ in: [{", ".join(status_ids)}] }} }}')
                    
                if "assignee_ids" in arguments and arguments["assignee_ids"]:
                    assignee_ids = [f'"{assignee_id}"' for assignee_id in arguments["assignee_ids"]]
                    filter_conditions.append(f'assignee: {{ id: {{ in: [{", ".join(assignee_ids)}] }} }}')
                    
                filter_string = ", ".join(filter_conditions)
                
                query = f"""
                query {{
                    issues(first: {limit}, filter: {{ {filter_string} }}) {{
                        nodes {{
                            id
                            title
                            identifier
                            url
                            state {{
                                name
                            }}
                            assignee {{
                                name
                            }}
                        }}
                    }}
                }}
                """
                
                result = linear_client.execute(query)
                issues = result.get("issues", {}).get("nodes", [])
                
                # Format results
                issue_list = []
                for issue in issues:
                    status = issue.get("state", {}).get("name", "Unknown")
                    assignee = issue.get("assignee", {}).get("name", "Unassigned")
                    issue_list.append(f"{issue['identifier']} - {issue['title']} [{status}] - Assigned to: {assignee}")
                    
                return [
                    TextContent(
                        type="text", 
                        text=f"Found {len(issues)} issues:\n\n" + "\n".join(issue_list) if issue_list else "No issues found matching your query."
                    )
                ]
                
            elif name == "list_teams":
                query = """
                query {
                    teams {
                        nodes {
                            id
                            name
                            key
                        }
                    }
                }
                """
                
                result = linear_client.execute(query)
                teams = result.get("teams", {}).get("nodes", [])
                
                team_list = [f"{team['name']} ({team['key']}) - ID: {team['id']}" for team in teams]
                
                return [
                    TextContent(
                        type="text", 
                        text=f"Available teams:\n\n" + "\n".join(team_list) if team_list else "No teams found in your workspace."
                    )
                ]

            return [
                TextContent(
                    type="text", 
                    text=f"Unknown tool: {name}"
                )
            ]
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [
                TextContent(
                    type="text", 
                    text=f"Error executing {name}: {str(e)}"
                )
            ]
    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="linear-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
