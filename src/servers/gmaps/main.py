import os
import sys
from typing import Optional, Iterable
import json
import urllib.parse

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import httpx

from mcp.types import (
    AnyUrl,
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.google.util import authenticate_and_save_credentials, get_credentials


SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_maps_client(user_id, api_key=None):
    """Create authenticated client for Google Maps APIs"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return httpx.AsyncClient(headers={"Authorization": f"Bearer {credentials.token}"})


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("google-maps-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="maps_get_route",
                description="Compute routes between two points using Google Maps Routes API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Origin location (address or lat,lng)",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination location (address or lat,lng)",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Travel mode (driving, walking, bicycling, transit)",
                            "default": "driving",
                        },
                        "alternatives": {
                            "type": "boolean",
                            "description": "Whether to return alternative routes",
                            "default": False,
                        },
                    },
                    "required": ["origin", "destination"],
                },
            ),
            Tool(
                name="maps_text_search",
                description="Search for places using a text query in Google Maps Places API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Text search query (e.g., 'restaurants in New York')",
                        },
                        "region": {
                            "type": "string",
                            "description": "Preferred region bias (e.g., 'us', 'fr')",
                            "default": "",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for results",
                            "default": "en",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="maps_nearby_search",
                description="Search for places near a specified location using Google Maps Places API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location to search near (latitude,longitude)",
                        },
                        "radius": {
                            "type": "integer",
                            "description": "Search radius in meters (max 50000)",
                            "default": 1000,
                        },
                        "type": {
                            "type": "string",
                            "description": "Place type (e.g., restaurant, cafe, park, etc.)",
                            "default": "",
                        },
                        "keyword": {
                            "type": "string",
                            "description": "Additional keyword to filter by",
                            "default": "",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                        },
                    },
                    "required": ["location"],
                },
            ),
            Tool(
                name="maps_get_directions",
                description="Get detailed directions between locations using Google Maps Directions API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Origin location (address or lat,lng)",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination location (address or lat,lng)",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Travel mode (driving, walking, bicycling, transit)",
                            "default": "driving",
                        },
                        "waypoints": {
                            "type": "string",
                            "description": "Comma-separated waypoints (optional)",
                            "default": "",
                        },
                        "avoid": {
                            "type": "string",
                            "description": "Features to avoid (tolls, highways, ferries, indoor)",
                            "default": "",
                        },
                        "units": {
                            "type": "string",
                            "description": "Unit system (metric, imperial)",
                            "default": "metric",
                        },
                    },
                    "required": ["origin", "destination"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        try:
            client = await create_maps_client(server.user_id, api_key=server.api_key)

            try:
                if name == "maps_get_route":
                    return await handle_get_route(client, arguments)
                elif name == "maps_text_search":
                    return await handle_text_search(client, arguments)
                elif name == "maps_nearby_search":
                    return await handle_nearby_search(client, arguments)
                elif name == "maps_get_directions":
                    return await handle_get_directions(client, arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            finally:
                await client.aclose()
        except Exception as e:
            logger.error(f"Error calling tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def handle_get_route(client, arguments):
        """Handle Google Maps Routes API requests"""
        if not arguments or "origin" not in arguments or "destination" not in arguments:
            return [
                TextContent(
                    type="text",
                    text="Error: Missing required parameters (origin, destination)",
                )
            ]

        origin = arguments["origin"]
        destination = arguments["destination"]
        mode = arguments.get("mode", "driving")
        alternatives = arguments.get("alternatives", False)

        url = "https://routes.googleapis.com/directions/v2:computeRoutes"

        payload = {
            "origin": {
                "address": origin if "," not in origin else None,
                "location": (
                    {
                        "latLng": {
                            "latitude": float(origin.split(",")[0]),
                            "longitude": float(origin.split(",")[1]),
                        }
                    }
                    if "," in origin
                    else None
                ),
            },
            "destination": {
                "address": destination if "," not in destination else None,
                "location": (
                    {
                        "latLng": {
                            "latitude": float(destination.split(",")[0]),
                            "longitude": float(destination.split(",")[1]),
                        }
                    }
                    if "," in destination
                    else None
                ),
            },
            "travelMode": mode.upper(),
            "routingPreference": "TRAFFIC_AWARE",
            "computeAlternativeRoutes": alternatives,
            "languageCode": "en-US",
            "units": "METRIC",
        }

        # Remove None values to make the payload valid
        if payload["origin"]["address"] is None:
            del payload["origin"]["address"]
        if payload["origin"].get("location") is None:
            del payload["origin"]["location"]
        if payload["destination"]["address"] is None:
            del payload["destination"]["address"]
        if payload["destination"].get("location") is None:
            del payload["destination"]["location"]

        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "X-Goog-FieldMask": "*"},
        )

        if response.status_code != 200:
            error_msg = f"Error: API request failed with status {response.status_code}"
            try:
                error_details = response.json()
                if "error" in error_details:
                    error_msg += f" - {error_details['error']['message']}"
            except:
                pass
            return [TextContent(type="text", text=error_msg)]

        data = response.json()
        if "routes" not in data or not data["routes"]:
            return [TextContent(type="text", text="No routes found")]

        # Process the routes
        routes = data["routes"]
        result = []

        for i, route in enumerate(routes):
            distance = route.get("distanceMeters", 0)
            duration = route.get("duration", "")
            if duration:
                duration = f"{int(duration[:-1]) // 3600}h {(int(duration[:-1]) % 3600) // 60}m"

            legs = route.get("legs", [])

            leg_summaries = []
            for leg in legs:
                steps = leg.get("steps", [])
                steps_text = []

                for step in steps:
                    instruction = step.get("navigationInstruction", {}).get(
                        "instructions", ""
                    )
                    distance = step.get("distanceMeters", 0)
                    duration = step.get("duration", "")
                    if duration:
                        duration = (
                            f"{int(duration[:-1]) // 60}m {int(duration[:-1]) % 60}s"
                        )

                    steps_text.append(f"• {instruction} ({distance}m, {duration})")

                leg_summaries.append("\n".join(steps_text))

            result.append(
                f"Route {i+1}:\n"
                f"Distance: {distance / 1000:.1f} km\n"
                f"Duration: {duration}\n"
                f"Steps:\n" + "\n".join(leg_summaries)
            )

        return [TextContent(type="text", text="\n\n---\n\n".join(result))]

    async def handle_text_search(client, arguments):
        """Handle Google Maps Places API text search requests"""
        if not arguments or "query" not in arguments:
            return [
                TextContent(
                    type="text", text="Error: Missing required parameter (query)"
                )
            ]

        query = arguments["query"]
        region = arguments.get("region", "")
        language = arguments.get("language", "en")
        max_results = min(
            int(arguments.get("max_results", 5)), 20
        )  # Limit to reasonable number

        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {"query": query, "language": language}

        if region:
            params["region"] = region

        response = await client.get(url, params=params)
        if response.status_code != 200:
            return [
                TextContent(
                    type="text",
                    text=f"Error: API request failed with status {response.status_code}",
                )
            ]

        data = response.json()
        if data.get("status") != "OK":
            return [
                TextContent(
                    type="text",
                    text=f"Error: {data.get('status')} - {data.get('error_message', 'No places found')}",
                )
            ]

        # Process the results
        places = data.get("results", [])[:max_results]
        result_texts = []

        for place in places:
            name = place.get("name", "Unnamed")
            address = place.get("formatted_address", "No address available")
            rating = place.get("rating", "Not rated")
            total_ratings = place.get("user_ratings_total", 0)
            types = ", ".join(place.get("types", []))

            place_id = place.get("place_id", "")
            maps_url = (
                f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                if place_id
                else ""
            )

            lat = place.get("geometry", {}).get("location", {}).get("lat", "")
            lng = place.get("geometry", {}).get("location", {}).get("lng", "")

            result_texts.append(
                f"Name: {name}\n"
                f"Address: {address}\n"
                f"Rating: {rating}/5 ({total_ratings} reviews)\n"
                f"Types: {types}\n"
                f"Coordinates: {lat}, {lng}\n"
                f"Google Maps: {maps_url}"
            )

        return [TextContent(type="text", text="\n\n---\n\n".join(result_texts))]

    async def handle_nearby_search(client, arguments):
        """Handle Google Maps Places API nearby search requests"""
        if not arguments or "location" not in arguments:
            return [
                TextContent(
                    type="text", text="Error: Missing required parameter (location)"
                )
            ]

        location = arguments["location"]
        radius = min(int(arguments.get("radius", 1000)), 50000)  # Max 50km
        place_type = arguments.get("type", "")
        keyword = arguments.get("keyword", "")
        max_results = min(
            int(arguments.get("max_results", 5)), 20
        )  # Limit to reasonable number

        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {"location": location, "radius": radius}

        if place_type:
            params["type"] = place_type

        if keyword:
            params["keyword"] = keyword

        response = await client.get(url, params=params)
        if response.status_code != 200:
            return [
                TextContent(
                    type="text",
                    text=f"Error: API request failed with status {response.status_code}",
                )
            ]

        data = response.json()
        if data.get("status") != "OK":
            return [
                TextContent(
                    type="text",
                    text=f"Error: {data.get('status')} - {data.get('error_message', 'No places found')}",
                )
            ]

        # Process the results
        places = data.get("results", [])[:max_results]
        result_texts = []

        for place in places:
            name = place.get("name", "Unnamed")
            address = place.get("vicinity", "No address available")
            rating = place.get("rating", "Not rated")
            total_ratings = place.get("user_ratings_total", 0)
            types = ", ".join(place.get("types", []))

            place_id = place.get("place_id", "")
            maps_url = (
                f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                if place_id
                else ""
            )

            lat = place.get("geometry", {}).get("location", {}).get("lat", "")
            lng = place.get("geometry", {}).get("location", {}).get("lng", "")

            open_now = "Unknown"
            if "opening_hours" in place and "open_now" in place["opening_hours"]:
                open_now = (
                    "Open now" if place["opening_hours"]["open_now"] else "Closed"
                )

            result_texts.append(
                f"Name: {name}\n"
                f"Address: {address}\n"
                f"Rating: {rating}/5 ({total_ratings} reviews)\n"
                f"Status: {open_now}\n"
                f"Types: {types}\n"
                f"Coordinates: {lat}, {lng}\n"
                f"Google Maps: {maps_url}"
            )

        return [TextContent(type="text", text="\n\n---\n\n".join(result_texts))]

    async def handle_get_directions(client, arguments):
        """Handle Google Maps Directions API requests"""
        if not arguments or "origin" not in arguments or "destination" not in arguments:
            return [
                TextContent(
                    type="text",
                    text="Error: Missing required parameters (origin, destination)",
                )
            ]

        origin = arguments["origin"]
        destination = arguments["destination"]
        mode = arguments.get("mode", "driving")
        waypoints = arguments.get("waypoints", "")
        avoid = arguments.get("avoid", "")
        units = arguments.get("units", "metric")

        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "units": units,
        }

        if waypoints:
            params["waypoints"] = waypoints

        if avoid:
            params["avoid"] = avoid

        response = await client.get(url, params=params)
        if response.status_code != 200:
            return [
                TextContent(
                    type="text",
                    text=f"Error: API request failed with status {response.status_code}",
                )
            ]

        data = response.json()
        if data.get("status") != "OK":
            return [
                TextContent(
                    type="text",
                    text=f"Error: {data.get('status')} - {data.get('error_message', 'Unable to calculate directions')}",
                )
            ]

        # Process the routes with detailed step-by-step directions
        routes = data.get("routes", [])
        result = []

        for i, route in enumerate(routes):
            summary = route.get("summary", "No summary")
            warnings = route.get("warnings", [])
            legs = route.get("legs", [])

            leg_details = []
            for leg_idx, leg in enumerate(legs):
                distance = leg.get("distance", {}).get("text", "Unknown")
                duration = leg.get("duration", {}).get("text", "Unknown")
                start_address = leg.get("start_address", "Unknown")
                end_address = leg.get("end_address", "Unknown")

                steps_text = []
                for step_idx, step in enumerate(leg.get("steps", [])):
                    instruction = step.get("html_instructions", "")
                    instruction = (
                        instruction.replace("<b>", "")
                        .replace("</b>", "")
                        .replace("<div>", "\n")
                        .replace("</div>", "")
                    )
                    distance = step.get("distance", {}).get("text", "Unknown")
                    duration = step.get("duration", {}).get("text", "Unknown")
                    steps_text.append(
                        f"{step_idx+1}. {instruction} ({distance}, {duration})"
                    )

                    # Include transit details if available
                    if mode == "transit" and "transit_details" in step:
                        transit = step["transit_details"]
                        line = transit.get("line", {}).get("name", "Unknown line")
                        vehicle = (
                            transit.get("line", {})
                            .get("vehicle", {})
                            .get("name", "transit")
                        )
                        departure_stop = transit.get("departure_stop", {}).get(
                            "name", "Unknown"
                        )
                        arrival_stop = transit.get("arrival_stop", {}).get(
                            "name", "Unknown"
                        )
                        num_stops = transit.get("num_stops", "Unknown")

                        steps_text.append(
                            f"   Take {vehicle} {line} from {departure_stop} to {arrival_stop} ({num_stops} stops)"
                        )

                leg_details.append(
                    f"Leg {leg_idx+1}: {start_address} to {end_address}\n"
                    f"Distance: {distance}\n"
                    f"Duration: {duration}\n"
                    f"Steps:\n" + "\n".join(steps_text)
                )

            warnings_text = ""
            if warnings:
                warnings_text = "\n\nWarnings:\n" + "\n".join(
                    [f"• {warning}" for warning in warnings]
                )

            result.append(
                f"Route {i+1}: {summary}\n"
                f"Total Distance: {legs[0].get('distance', {}).get('text', 'Unknown')}\n"
                f"Total Duration: {legs[0].get('duration', {}).get('text', 'Unknown')}\n\n"
                + "\n\n".join(leg_details)
                + warnings_text
            )

        return [
            TextContent(type="text", text="\n\n===================\n\n".join(result))
        ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="google-maps-server",
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
        print("Note: To run the server normally, use the GuMCP server framework.")
