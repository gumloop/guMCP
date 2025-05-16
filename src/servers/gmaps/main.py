"""
This server provides a set of tools for interacting with the Google Maps API.
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional, Union
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
                        },
                        "region": {
                            "type": "string",
                            "description": "Country code for region biasing",
                        },
                        "components": {
                            "type": "object",
                            "description": "Filter results by component (country, postal_code, etc)",
                        },
                        "bounds": {
                            "type": "string",
                            "description": "Restrict results to a specific area (lat,lng|lat,lng)",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for results (e.g., en, es, fr)",
                        },
                    },
                    "required": ["address"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Geocoding results containing formatted address, location coordinates, and address components",
                    "examples": [
                        '{\n  "results": [\n    {\n      "formatted_address": "San Francisco, CA, USA",\n      "place_id": "ChIJIQBpAG2ahYAR_6128GcTUEo",\n      "geometry": {\n        "location": {\n          "lat": 37.7749295,\n          "lng": -122.4194155\n        },\n        "viewport": {\n          "northeast": {\n            "lat": 37.812,\n            "lng": -122.3482\n          },\n          "southwest": {\n            "lat": 37.7034,\n            "lng": -122.5270\n          }\n        }\n      },\n      "types": ["locality", "political"]\n    }\n  ],\n  "status": "OK"\n}'
                    ],
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
                        "result_type": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter results by type (street_address, country, etc)",
                        },
                        "location_type": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by location type (ROOFTOP, RANGE_INTERPOLATED, etc)",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for results (e.g., en, es, fr)",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reverse geocoding results containing formatted address and location details for the specified coordinates",
                    "examples": [
                        '{\n  "results": [\n    {\n      "formatted_address": "1 Market St, San Francisco, CA 94105, USA",\n      "place_id": "ChIJgWeAIhKBhYARCsQ5SbKvAJo",\n      "types": ["street_address"],\n      "address_components": [\n        {"long_name": "1", "short_name": "1", "types": ["street_number"]},\n        {"long_name": "Market Street", "short_name": "Market St", "types": ["route"]},\n        {"long_name": "Financial District", "short_name": "Financial District", "types": ["neighborhood", "political"]}\n      ]\n    }\n  ],\n  "status": "OK"\n}'
                    ],
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
                        "type": {
                            "type": "string",
                            "description": "Place type (restaurant, cafe, etc)",
                        },
                        "keyword": {
                            "type": "string",
                            "description": "Additional keyword to filter results",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for results (e.g., en, es, fr)",
                        },
                        "min_price": {
                            "type": "integer",
                            "description": "Minimum price level (0-4)",
                        },
                        "max_price": {
                            "type": "integer",
                            "description": "Maximum price level (0-4)",
                        },
                        "open_now": {
                            "type": "boolean",
                            "description": "Filter for places that are open now",
                        },
                    },
                    "required": ["query", "latitude", "longitude"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Nearby places search results containing place details like name, address, rating, and location",
                    "examples": [
                        '{\n  "results": [\n    {\n      "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",\n      "name": "Google Sydney",\n      "vicinity": "48 Pirrama Road, Pyrmont",\n      "rating": 4.5,\n      "user_ratings_total": 4000,\n      "geometry": {\n        "location": {\n          "lat": -33.866651,\n          "lng": 151.195827\n        }\n      },\n      "types": ["point_of_interest", "establishment"]\n    },\n    {\n      "place_id": "ChIJP3Sa8ziYEmsRUKgyFmh9AQM",\n      "name": "Sydney Opera House",\n      "vicinity": "Bennelong Point, Sydney",\n      "rating": 4.7,\n      "user_ratings_total": 75000,\n      "photos": [\n        {\n          "height": 1365,\n          "width": 2048,\n          "photo_reference": "PHOTO_REFERENCE"\n        }\n      ]\n    }\n  ],\n  "status": "OK"\n}'
                    ],
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
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific fields to return (name, address_component, etc)",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for results (e.g., en, es, fr)",
                        },
                        "region": {
                            "type": "string",
                            "description": "Region bias for results",
                        },
                    },
                    "required": ["place_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed place information including contact details, opening hours, reviews, and photos",
                    "examples": [
                        '{\n  "result": {\n    "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",\n    "name": "Google Sydney",\n    "formatted_address": "48 Pirrama Road, Pyrmont NSW 2009, Australia",\n    "formatted_phone_number": "(02) 9374 4000",\n    "rating": 4.5,\n    "opening_hours": {\n      "open_now": true,\n      "periods": [\n        {\n          "open": {"day": 0, "time": "0900"},\n          "close": {"day": 0, "time": "1700"}\n        }\n      ],\n      "weekday_text": [\n        "Monday: 9:00 AM – 5:00 PM"\n      ]\n    },\n    "website": "https://example.com/google-sydney"\n  },\n  "status": "OK"\n}'
                    ],
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
                        "language": {
                            "type": "string",
                            "description": "Language for results (e.g., en, es, fr)",
                        },
                    },
                    "required": ["place_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reviews for the specified place including rating, text content, and author details",
                    "examples": [
                        '{\n  "reviews": [\n    {\n      "author_name": "John Smith",\n      "rating": 5,\n      "relative_time_description": "a week ago",\n      "text": "Great place! Highly recommended.",\n      "time": 1577836800\n    },\n    {\n      "author_name": "Jane Doe",\n      "rating": 4,\n      "relative_time_description": "3 months ago",\n      "text": "Nice atmosphere but a bit crowded.",\n      "time": 1569888000\n    }\n  ],\n  "total": 50\n}'
                    ],
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
                        "mode": {
                            "type": "string",
                            "description": "Mode of transportation (driving, walking, bicycling, transit)",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for results (e.g., en, es, fr)",
                        },
                        "avoid": {
                            "type": "string",
                            "description": "Features to avoid (tolls, highways, ferries, indoor)",
                        },
                        "units": {
                            "type": "string",
                            "description": "Units system (metric, imperial)",
                        },
                        "departure_time": {
                            "type": "string",
                            "description": "Departure time (now or UNIX timestamp)",
                        },
                        "arrival_time": {
                            "type": "string",
                            "description": "Desired arrival time as UNIX timestamp",
                        },
                        "traffic_model": {
                            "type": "string",
                            "description": "Traffic model (best_guess, pessimistic, optimistic)",
                        },
                    },
                    "required": ["origins", "destinations"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Distance and duration information between origins and destinations with various travel metrics",
                    "examples": [
                        '{\n  "destination_addresses": ["Los Angeles, CA, USA"],\n  "origin_addresses": ["San Francisco, CA, USA"],\n  "rows": [\n    {\n      "elements": [\n        {\n          "distance": {\n            "text": "383 mi",\n            "value": 616617\n          },\n          "duration": {\n            "text": "5 hours 57 mins",\n            "value": 21420\n          },\n          "status": "OK"\n        }\n      ]\n    }\n  ],\n  "status": "OK"\n}'
                    ],
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
                        "samples": {
                            "type": "integer",
                            "description": "Number of sample points",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Elevation data for the specified coordinates in meters above sea level",
                    "examples": [
                        '[\n  {\n    "elevation": 5.13,\n    "location": {\n      "lat": 37.7749295,\n      "lng": -122.4194155\n    },\n    "resolution": 4.7\n  }\n]'
                    ],
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
                        "waypoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of waypoints",
                        },
                        "alternatives": {
                            "type": "boolean",
                            "description": "Whether to provide alternative routes",
                        },
                        "avoid": {
                            "type": "string",
                            "description": "Features to avoid (tolls, highways, ferries, indoor)",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for results (e.g., en, es, fr)",
                        },
                        "units": {
                            "type": "string",
                            "description": "Units system (metric, imperial)",
                        },
                        "region": {
                            "type": "string",
                            "description": "Region bias for results",
                        },
                        "departure_time": {
                            "type": "string",
                            "description": "Departure time (now or UNIX timestamp)",
                        },
                        "arrival_time": {
                            "type": "string",
                            "description": "Desired arrival time as UNIX timestamp",
                        },
                        "traffic_model": {
                            "type": "string",
                            "description": "Traffic model (best_guess, pessimistic, optimistic)",
                        },
                    },
                    "required": ["origin", "destination"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Directions between origin and destination including distance, duration, and turn-by-turn navigation steps",
                    "examples": [
                        '[\n  {\n    "legs": [\n      {\n        "distance": {\n          "text": "383 mi",\n          "value": 616617\n        },\n        "duration": {\n          "text": "5 hours 57 mins",\n          "value": 21420\n        },\n        "end_address": "Los Angeles, CA, USA",\n        "start_address": "San Francisco, CA, USA",\n        "steps": [\n          {\n            "distance": {\n              "text": "0.3 mi",\n              "value": 482\n            },\n            "duration": {\n              "text": "1 min",\n              "value": 63\n            },\n            "html_instructions": "Head south on Market St",\n            "travel_mode": "DRIVING"\n          },\n          {\n            "distance": {\n              "text": "2.6 mi",\n              "value": 4225\n            },\n            "duration": {\n              "text": "6 mins",\n              "value": 343\n            },\n            "html_instructions": "Turn right onto I-80 E",\n            "travel_mode": "DRIVING"\n          }\n        ]\n      }\n    ],\n    "summary": "I-5 S",\n    "warnings": [],\n    "waypoint_order": []\n  }\n]'
                    ],
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
                TextContent(
                    type="text",
                    text=json.dumps({"error": "Google Maps API key not provided"}),
                )
            ]

        gmaps = googlemaps.Client(key=api_key)

        try:
            if name == "address_to_coordinates":
                address = arguments.get("address")
                if not address:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Missing address parameter"}),
                        )
                    ]

                # Extract optional parameters
                geocode_params = {
                    key: arguments.get(key)
                    for key in ["region", "components", "bounds", "language"]
                    if arguments.get(key) is not None
                }

                geocode_result = gmaps.geocode(address, **geocode_params)
                if not geocode_result:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": "No results found"})
                        )
                    ]

                result = geocode_result

            elif name == "coordinates_to_address":
                lat = arguments.get("latitude")
                lng = arguments.get("longitude")
                if lat is None or lng is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Missing coordinates"}),
                        )
                    ]

                # Extract optional parameters
                reverse_geocode_params = {
                    key: arguments.get(key)
                    for key in ["result_type", "location_type", "language"]
                    if arguments.get(key) is not None
                }

                reverse_geocode_result = gmaps.reverse_geocode(
                    (lat, lng), **reverse_geocode_params
                )
                if not reverse_geocode_result:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": "No results found"})
                        )
                    ]

                result = reverse_geocode_result

            elif name == "search_places":
                query = arguments.get("query")
                lat = arguments.get("latitude")
                lng = arguments.get("longitude")
                limit = arguments.get("limit", 5)
                radius = arguments.get("radius", 20000)

                if not all([query, lat, lng]):
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Missing required parameters"}),
                        )
                    ]

                # Extract optional parameters
                places_params = {
                    "location": (lat, lng),
                    "radius": radius,
                    "keyword": query,
                }

                # Add optional parameters if provided
                for param_key, arg_key in {
                    "type": "type",
                    "language": "language",
                    "min_price": "min_price",
                    "max_price": "max_price",
                    "open_now": "open_now",
                }.items():
                    if arguments.get(arg_key) is not None:
                        places_params[param_key] = arguments.get(arg_key)

                places_result = gmaps.places_nearby(**places_params)

                if not places_result.get("results"):
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": "No places found"})
                        )
                    ]

                result = places_result

            elif name == "get_place_details":
                place_id = arguments.get("place_id")
                if not place_id:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Missing place_id parameter"}),
                        )
                    ]

                # Extract optional parameters
                place_details_params = {
                    key: arguments.get(key)
                    for key in ["fields", "language", "region"]
                    if arguments.get(key) is not None
                }

                place_details = gmaps.place(place_id, **place_details_params)
                if not place_details.get("result"):
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": "No details found"})
                        )
                    ]

                result = place_details

            elif name == "get_place_reviews":
                place_id = arguments.get("place_id")
                limit = arguments.get("limit", 5)
                language = arguments.get("language")

                if not place_id:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Missing place_id parameter"}),
                        )
                    ]

                # Extract optional parameters
                place_details_params = {}
                if language:
                    place_details_params["language"] = language

                place_details = gmaps.place(place_id, **place_details_params)
                if not place_details.get("result", {}).get("reviews"):
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": "No reviews found"})
                        )
                    ]

                # Return just the reviews array with the specified limit
                reviews = place_details["result"]["reviews"][:limit]
                result = {
                    "reviews": reviews,
                    "total": len(place_details["result"].get("reviews", [])),
                }

            elif name == "get_distance_matrix":
                origins = arguments.get("origins")
                destinations = arguments.get("destinations")
                if not all([origins, destinations]):
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": "Missing origins or destinations"}
                            ),
                        )
                    ]

                # Extract optional parameters
                distance_matrix_params = {
                    key: arguments.get(key)
                    for key in [
                        "mode",
                        "language",
                        "avoid",
                        "units",
                        "departure_time",
                        "arrival_time",
                        "traffic_model",
                    ]
                    if arguments.get(key) is not None
                }

                distance_matrix = gmaps.distance_matrix(
                    origins, destinations, **distance_matrix_params
                )
                if not distance_matrix.get("rows"):
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": "No results found"})
                        )
                    ]

                result = distance_matrix

            elif name == "get_elevation":
                lat = arguments.get("latitude")
                lng = arguments.get("longitude")
                samples = arguments.get("samples")

                if lat is None or lng is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Missing coordinates"}),
                        )
                    ]

                # Build parameters
                elevation_params = {}
                if samples:
                    elevation_params["samples"] = samples

                elevation_result = gmaps.elevation((lat, lng), **elevation_params)
                if not elevation_result:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "No elevation data found"}),
                        )
                    ]

                result = elevation_result

            elif name == "get_directions":
                origin = arguments.get("origin")
                destination = arguments.get("destination")
                mode = arguments.get("mode", "driving")

                if not all([origin, destination]):
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Missing origin or destination"}),
                        )
                    ]

                # Extract optional parameters
                directions_params = {
                    "mode": mode,
                }

                for param_key, arg_key in {
                    "waypoints": "waypoints",
                    "alternatives": "alternatives",
                    "avoid": "avoid",
                    "language": "language",
                    "units": "units",
                    "region": "region",
                    "departure_time": "departure_time",
                    "arrival_time": "arrival_time",
                    "traffic_model": "traffic_model",
                }.items():
                    if arguments.get(arg_key) is not None:
                        directions_params[param_key] = arguments.get(arg_key)

                directions_result = gmaps.directions(
                    origin, destination, **directions_params
                )
                if not directions_result:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "No directions found"}),
                        )
                    ]

                result = directions_result

            else:
                return [
                    TextContent(
                        type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
                    )
                ]

            # Handle the result - return raw JSON from the API
            if isinstance(result, list):
                # Remove polylines from directions output if present
                if name == "get_directions":
                    for route in result:
                        route.pop("overview_polyline", None)
                        route.pop("polyline", None)

                # Return each item in the list as a separate TextContent
                return [
                    TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result
                ]
            else:
                # Return a single TextContent with the JSON result
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error during Google Maps API call: {str(e)}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
