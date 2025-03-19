import logging
import uvicorn
import argparse
import importlib.util
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse

from mcp.server.sse import SseServerTransport

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gumcp-server")

# Dictionary to store servers
servers = {}

def discover_servers():
    """Discover and load all servers from the servers directory"""
    # Get the path to the servers directory
    current_dir = Path(__file__).parent.absolute()
    servers_dir = current_dir / "servers"  # Look in the servers subdirectory
    
    logger.info(f"Looking for servers in {servers_dir}")
    
    # Iterate through all directories in the servers directory
    for item in servers_dir.iterdir():
        if item.is_dir():
            server_name = item.name
            server_file = item / "main.py"
            
            if server_file.exists():
                try:
                    # Load the server module
                    spec = importlib.util.spec_from_file_location(
                        f"{server_name}.server", server_file
                    )
                    server_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(server_module)
                    
                    # Get the server and initialization options from the module
                    if hasattr(server_module, "server") and hasattr(server_module, "get_initialization_options"):
                        server = server_module.server
                        get_init_options = server_module.get_initialization_options
                        
                        # Store the server
                        servers[server_name] = {
                            "server": server,
                            "get_initialization_options": get_init_options,
                        }
                        logger.info(f"Loaded server: {server_name}")
                    else:
                        logger.warning(f"Server {server_name} does not have required server or get_initialization_options")
                except Exception as e:
                    logger.error(f"Failed to load server {server_name}: {e}")
    
    logger.info(f"Discovered {len(servers)} servers")

def create_starlette_app():
    """Create a Starlette app with multiple SSE transports for different servers"""
    # Discover and load all servers
    discover_servers()
    
    # Define routes for the Starlette app
    routes = []
    
    # Health check endpoint
    async def health_check(request):
        """Health check endpoint"""
        return JSONResponse({
            "status": "ok",
            "servers": list(servers.keys())
        })
    
    routes.append(Route("/health", endpoint=health_check))
    
    # Create an SSE endpoint for each server
    for server_name, server_info in servers.items():
        # Create SSE transport for this server
        sse_path = f"/api/{server_name}/messages/"
        sse_transport = SseServerTransport(sse_path)
        
        # Create handler for this server
        def create_handler(server_name, server_instance, get_init_options):
            async def handle_sse(request):
                """Handle SSE connection requests for a specific server"""
                logger.info(f"New SSE connection requested for {server_name}")
                async with sse_transport.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    logger.info(f"SSE connection established for {server_name}")
                    await server_instance.run(
                        streams[0],
                        streams[1],
                        get_init_options(),
                    )
            return handle_sse
        
        # Create a bound handler for this specific server
        # This closure approach ensures each handler gets the correct server
        handler = create_handler(
            server_name,
            server_info["server"], 
            server_info["get_initialization_options"]
        )
        
        # Add routes for this server
        routes.append(Route(f"/api/{server_name}/sse", endpoint=handler))
        routes.append(Mount(sse_path, app=sse_transport.handle_post_message))
        
        logger.info(f"Added routes for server: {server_name}")
    
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
