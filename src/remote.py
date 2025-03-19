#!/usr/bin/env python3
"""
Central MCP server that loads all integration servers from the servers directory.
This provides a single entry point with multiple SSE endpoints, one for each integration.
"""

import argparse
import importlib.util
import os
import sys
import logging
import uvicorn
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse

from mcp.server.sse import SseServerTransport

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("central-mcp-server")

# Dictionary to store integration servers
integration_servers = {}

def discover_integrations():
    """Discover and load all integration servers from the servers directory"""
    # Get the path to the servers directory
    current_dir = Path(__file__).parent.absolute()
    servers_dir = current_dir / "servers"  # Look in the servers subdirectory
    
    logger.info(f"Looking for integrations in {servers_dir}")
    
    # Iterate through all directories in the servers directory
    for item in servers_dir.iterdir():
        if item.is_dir():
            integration_name = item.name
            server_file = item / "main.py"
            
            if server_file.exists():
                try:
                    # Load the server module
                    spec = importlib.util.spec_from_file_location(
                        f"{integration_name}.server", server_file
                    )
                    server_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(server_module)
                    
                    # Get the server and initialization options from the module
                    if hasattr(server_module, "server") and hasattr(server_module, "get_initialization_options"):
                        server = server_module.server
                        get_init_options = server_module.get_initialization_options
                        
                        # Store the integration
                        integration_servers[integration_name] = {
                            "server": server,
                            "get_initialization_options": get_init_options,
                        }
                        logger.info(f"Loaded integration: {integration_name}")
                    else:
                        logger.warning(f"Integration {integration_name} does not have required server or get_initialization_options")
                except Exception as e:
                    logger.error(f"Failed to load integration {integration_name}: {e}")
    
    logger.info(f"Discovered {len(integration_servers)} integrations")

def create_starlette_app():
    """Create a Starlette app with multiple SSE transports for different integrations"""
    # Discover and load all integrations
    discover_integrations()
    
    # Define routes for the Starlette app
    routes = []
    
    # Health check endpoint
    async def health_check(request):
        """Health check endpoint"""
        return JSONResponse({
            "status": "ok",
            "integrations": list(integration_servers.keys())
        })
    
    routes.append(Route("/health", endpoint=health_check))
    
    # Create an SSE endpoint for each integration
    for integration_name, integration in integration_servers.items():
        # Create SSE transport for this integration
        sse_path = f"/api/{integration_name}/messages/"
        sse_transport = SseServerTransport(sse_path)
        
        # Create handler for this integration
        def create_handler(integration_name, integration_server, get_init_options):
            async def handle_sse(request):
                """Handle SSE connection requests for a specific integration"""
                logger.info(f"New SSE connection requested for {integration_name}")
                async with sse_transport.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    logger.info(f"SSE connection established for {integration_name}")
                    await integration_server.run(
                        streams[0],
                        streams[1],
                        get_init_options(),
                    )
            return handle_sse
        
        # Create a bound handler for this specific integration
        # This closure approach ensures each handler gets the correct integration
        handler = create_handler(
            integration_name,
            integration["server"], 
            integration["get_initialization_options"]
        )
        
        # Add routes for this integration
        routes.append(Route(f"/api/{integration_name}/sse", endpoint=handler))
        routes.append(Mount(sse_path, app=sse_transport.handle_post_message))
        
        logger.info(f"Added routes for integration: {integration_name}")
    
    # Create and return the Starlette app
    app = Starlette(
        debug=True,
        routes=routes,
    )
    
    return app

def main():
    """Main entry point for the Starlette server"""
    parser = argparse.ArgumentParser(description="Central MCP Server")
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host for Starlette server"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port for Starlette server"
    )
    
    args = parser.parse_args()
    
    # Run the Starlette server
    app = create_starlette_app()
    logger.info(f"Starting Starlette server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main() 
