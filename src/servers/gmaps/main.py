"""
This server provides a set of tools for interacting with the Google Maps API.
"""

import os
import sys
import json
from typing import List
import logging
from pathlib import Path
import googlemaps

from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_gmaps_key(user_id):
    """Authenticate with Google Maps and save API key"""
    logger.info("Starting Google Maps authentication for user %s...", user_id)

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your Google Maps API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials("gmaps", user_id, {"api_key": api_key})

    logger.info(
        "Google Maps API key saved for user %s. You can now run the server.", user_id
    )
    return api_key


async def get_gmaps_credentials(user_id, api_key=None):
    """Get Google Maps API key for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials("gmaps", user_id)

    def handle_missing_credentials():
        error_str = f"Google Maps API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
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


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("gmaps-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info("Listing tools for user: %s", server.user_id)

        return [
            Tool(
                name="address_to_coordinates",
                description="Get the coordinates of an address",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "The address to geocode",
                        }
                    },
                    "required": ["address"],
                },
            ),
            Tool(
                name="coordinates_to_address",
                description="Get the address of a set of coordinates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude coordinate",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude coordinate",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
            ),
            Tool(
                name="search_places",
                description="Search for places around a set of coordinates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "latitude": {
                            "type": "number",
                            "description": "Latitude coordinate",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude coordinate",
                        },
                        "radius": {
                            "type": "number",
                            "description": "Search radius in meters (default: 50000)",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Number of results to return (default: 5)",
                        },
                    },
                    "required": ["query", "latitude", "longitude"],
                },
            ),
            Tool(
                name="get_place_details",
                description="Get details about a place",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "place_id": {
                            "type": "string",
                            "description": "Google Places ID",
                        }
                    },
                    "required": ["place_id"],
                },
            ),
            Tool(
                name="get_place_reviews",
                description="Retrieve place reviews",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "place_id": {
                            "type": "string",
                            "description": "Google Places ID",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Number of reviews to return (default: 5)",
                        },
                    },
                    "required": ["place_id"],
                },
            ),
            Tool(
                name="get_distance_matrix",
                description="Get the distance and duration between two sets of coordinates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "origins": {
                            "type": "string",
                            "description": "Origin coordinates or address",
                        },
                        "destinations": {
                            "type": "string",
                            "description": "Destination coordinates or address",
                        },
                    },
                    "required": ["origins", "destinations"],
                },
            ),
            Tool(
                name="get_elevation",
                description="Get the elevation of a set of coordinates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude coordinate",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude coordinate",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
            ),
            Tool(
                name="get_directions",
                description="Get directions between two sets of coordinates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Origin coordinates or address",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination coordinates or address",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Travel mode (driving, walking, bicycling, transit) (default: driving)",
                        },
                    },
                    "required": ["origin", "destination"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            "User %s calling tool: %s with arguments: %s",
            server.user_id,
            name,
            arguments,
        )

        api_key = await get_gmaps_credentials(server.user_id, api_key=server.api_key)
        if not api_key:
            return [
                TextContent(type="text", text="Error: Google Maps API key not provided")
            ]

        gmaps = googlemaps.Client(key=api_key)

        try:
            if name == "address_to_coordinates":
                address = arguments.get("address")
                if not address:
                    return [
                        TextContent(
                            type="text", text="Error: Missing address parameter"
                        )
                    ]

                geocode_result = gmaps.geocode(address)
                if not geocode_result:
                    return [TextContent(type="text", text="No results found")]

                result = geocode_result[0]["geometry"]["location"]

            elif name == "coordinates_to_address":
                lat = arguments.get("latitude")
                lng = arguments.get("longitude")
                if lat is None or lng is None:
                    return [TextContent(type="text", text="Error: Missing coordinates")]

                reverse_geocode_result = gmaps.reverse_geocode((lat, lng))
                if not reverse_geocode_result:
                    return [TextContent(type="text", text="No results found")]

                result = {
                    "name": reverse_geocode_result[0].get("formatted_address", ""),
                    "address": reverse_geocode_result[0].get("formatted_address", ""),
                    "rating": reverse_geocode_result[0].get("rating", None),
                }

            elif name == "search_places":
                query = arguments.get("query")
                lat = arguments.get("latitude")
                lng = arguments.get("longitude")
                limit = arguments.get("limit", 5)
                radius = arguments.get("radius", 20000)

                if not all([query, lat, lng]):
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameters"
                        )
                    ]

                places_result = gmaps.places_nearby(
                    location=(lat, lng), radius=radius, keyword=query
                )

                if not places_result.get("results"):
                    return [TextContent(type="text", text="No places found")]

                result = places_result["results"][:limit]

            elif name == "get_place_details":
                place_id = arguments.get("place_id")
                if not place_id:
                    return [
                        TextContent(
                            type="text", text="Error: Missing place_id parameter"
                        )
                    ]

                place_details = gmaps.place(place_id)
                if not place_details.get("result"):
                    return [TextContent(type="text", text="No details found")]

                result = place_details["result"]

            elif name == "get_place_reviews":
                place_id = arguments.get("place_id")
                limit = arguments.get("limit", 5)
                if not place_id:
                    return [
                        TextContent(
                            type="text", text="Error: Missing place_id parameter"
                        )
                    ]

                place_details = gmaps.place(place_id)
                if not place_details.get("result", {}).get("reviews"):
                    return [TextContent(type="text", text="No reviews found")]

                result = []
                for review in place_details["result"]["reviews"][:limit]:
                    result.append(
                        f"Rating: {review['rating']}/5\n{review['text']}\n---"
                    )

            elif name == "get_distance_matrix":
                origins = arguments.get("origins")
                destinations = arguments.get("destinations")
                if not all([origins, destinations]):
                    return [
                        TextContent(
                            type="text", text="Error: Missing origins or destinations"
                        )
                    ]

                distance_matrix = gmaps.distance_matrix(origins, destinations)
                if not distance_matrix.get("rows"):
                    return [TextContent(type="text", text="No results found")]

                result = distance_matrix["rows"][0]["elements"][0]
                if result["status"] != "OK":
                    return [
                        TextContent(type="text", text="Could not calculate distance")
                    ]

                result = f"Distance: {result['distance']['text']}\nDuration: {result['duration']['text']}"

            elif name == "get_elevation":
                lat = arguments.get("latitude")
                lng = arguments.get("longitude")
                if lat is None or lng is None:
                    return [TextContent(type="text", text="Error: Missing coordinates")]

                elevation_result = gmaps.elevation((lat, lng))
                if not elevation_result:
                    return [TextContent(type="text", text="No elevation data found")]

                result = elevation_result[0]["elevation"]

            elif name == "get_directions":
                origin = arguments.get("origin")
                destination = arguments.get("destination")
                mode = arguments.get("mode", "driving")

                if not all([origin, destination]):
                    return [
                        TextContent(
                            type="text", text="Error: Missing origin or destination"
                        )
                    ]

                directions_result = gmaps.directions(origin, destination, mode=mode)
                if not directions_result:
                    return [TextContent(type="text", text="No directions found")]

                route = directions_result[0]["legs"][0]
                steps = [
                    f"{i+1}. {step['html_instructions']}"
                    for i, step in enumerate(route["steps"])
                ]

                result = (
                    f"Distance: {route['distance']['text']}\nDuration: {route['duration']['text']}\n\nDirections:\n"
                    + "\n".join(steps)
                )

            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error during Google Maps API call: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="gmaps-server",
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
        authenticate_and_save_gmaps_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
