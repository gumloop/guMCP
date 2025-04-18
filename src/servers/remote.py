import logging
import uvicorn
import argparse
import importlib.util
from pathlib import Path
import threading

from starlette.routing import Route
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

from mcp.server.sse import SseServerTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gumcp-server")

# Dictionary to store servers
servers = {}

# Store user-specific SSE transports and server instances
user_session_transports = {}
user_server_instances = {}

# Prometheus metrics
active_connections = Gauge(
    "gumcp_active_connections", "Number of active SSE connections", ["server"]
)
connection_total = Counter(
    "gumcp_connection_total", "Total number of SSE connections", ["server"]
)

# Default metrics port
METRICS_PORT = 9091


def discover_servers():
    """Discover and load all servers from the servers directory"""
    # Get the path to the servers directory
    servers_dir = Path(__file__).parent.absolute()

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
                    if hasattr(server_module, "server") and hasattr(
                        server_module, "get_initialization_options"
                    ):
                        server = server_module.server
                        get_init_options = server_module.get_initialization_options

                        # Store the server
                        servers[server_name] = {
                            "server": server,
                            "get_initialization_options": get_init_options,
                        }
                        logger.info(f"Loaded server: {server_name}")
                    else:
                        logger.warning(
                            f"Server {server_name} does not have required server or get_initialization_options"
                        )
                except Exception as e:
                    logger.error(f"Failed to load server {server_name}: {e}")

    logger.info(f"Discovered {len(servers)} servers")


def create_metrics_app():
    """Create a separate Starlette app just for metrics"""

    async def metrics_endpoint(request):
        """Prometheus metrics endpoint"""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    routes = [Route("/metrics", endpoint=metrics_endpoint)]

    app = Starlette(
        debug=True,
        routes=routes,
    )

    return app


def create_starlette_app():
    """Create a Starlette app with multiple SSE transports for different servers"""
    # Discover and load all servers
    discover_servers()

    # Define routes for the Starlette app
    routes = []

    # Create an SSE endpoint for each server
    for server_name, server_info in servers.items():
        # Create handler for user-specific SSE sessions
        def create_handler(server_name, server_factory, get_init_options):
            async def handle_sse(request):
                """Handle SSE connection requests for a specific server and session"""
                # Get session_key from route parameter (For Gumloop, this is a URL encoded version of "{user_id}:{api_key}")
                session_key_encoded = request.path_params["session_key"]
                # Using the server_name and encoded session_key as the actual session key
                session_key = f"{server_name}:{session_key_encoded}"

                user_id = None
                api_key = None

                if ":" in session_key_encoded:
                    user_id = session_key_encoded.split(":")[0]
                    api_key = session_key_encoded.split(":")[1]
                else:
                    user_id = session_key_encoded

                logger.info(
                    f"New SSE connection requested for {server_name} with session: {user_id}"
                )

                # Create an SSE transport for this session
                sse_transport = SseServerTransport(
                    f"/{server_name}/{session_key_encoded}/messages/"
                )

                # Store the transport
                user_session_transports[session_key] = sse_transport

                # Create a new server instance for this user if it doesn't exist
                # or reuse the existing one to maintain state between reconnections
                if session_key not in user_server_instances:
                    server_instance = server_factory(user_id, api_key)
                    user_server_instances[session_key] = server_instance
                else:
                    server_instance = user_server_instances[session_key]

                # Get standard initialization options
                init_options = get_init_options(server_instance)

                try:
                    # Increment metrics

                    # Only increment active connections for new sessions
                    if not session_key in user_server_instances:
                        active_connections.labels(server=server_name).inc()

                    # Always increment total connections counter
                    connection_total.labels(server=server_name).inc()

                    async with sse_transport.connect_sse(
                        request.scope, request.receive, request._send
                    ) as streams:
                        logger.info(
                            f"SSE connection established for {server_name} session: {user_id}"
                        )
                        await server_instance.run(
                            streams[0],
                            streams[1],
                            init_options,
                        )
                finally:
                    # Clean up the transport when the connection closes
                    if session_key in user_session_transports:
                        del user_session_transports[session_key]
                        # Decrement active connections metric
                        active_connections.labels(server=server_name).dec()
                        logger.info(
                            f"Closed SSE connection for {server_name} session: {user_id}"
                        )

            return handle_sse

        # Add routes for this server with session_key as path parameter
        handler = create_handler(
            server_name,
            server_info["server"],
            server_info["get_initialization_options"],
        )

        # Add the SSE connection route with path parameter for session_key
        routes.append(Route(f"/{server_name}/{{session_key}}", endpoint=handler))

        # Message handler for sending messages to a specific session
        def create_message_handler(server_name):
            async def handle_message(request):
                """Handle messages sent to a specific user session"""
                session_key_encoded = request.path_params["session_key"]
                session_key = f"{server_name}:{session_key_encoded}"

                if session_key not in user_session_transports:
                    return Response(
                        f"Session not found or expired",
                        status_code=404,
                    )

                transport = user_session_transports[session_key]
                return transport.handle_post_message

            return handle_message

        # Add the message posting route with the custom handler
        message_handler = create_message_handler(server_name)
        routes.append(
            Route(
                f"/{server_name}/{{session_key}}/messages/",
                endpoint=message_handler,
                methods=["POST"],
            )
        )

        logger.info(f"Added user-specific routes for server: {server_name}")

    # Health checks
    async def root_handler(request):
        """Root endpoint that returns a simple 200 OK response"""
        return JSONResponse(
            {
                "status": "ok",
                "message": "guMCP server running",
                "servers": list(servers.keys()),
            }
        )

    routes.append(Route("/", endpoint=root_handler))

    async def health_check(request):
        """Health check endpoint"""
        return JSONResponse({"status": "ok", "servers": list(servers.keys())})

    routes.append(Route("/health_check", endpoint=health_check))

    app = Starlette(
        debug=True,
        routes=routes,
    )

    return app


def run_metrics_server(host, port):
    """Run a separate metrics server on the specified port"""
    metrics_app = create_metrics_app()
    logger.info(f"Starting metrics server on {host}:{port}")
    uvicorn.run(metrics_app, host=host, port=port)


def main():
    """Main entry point for the Starlette server"""
    parser = argparse.ArgumentParser(description="guMCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host for Starlette server")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for Starlette server"
    )

    args = parser.parse_args()

    metrics_thread = threading.Thread(
        target=run_metrics_server, args=(args.host, METRICS_PORT), daemon=True
    )
    metrics_thread.start()
    logger.info(f"Starting Metrics server on http://{args.host}:{METRICS_PORT}/metrics")

    # Run the main Starlette server
    app = create_starlette_app()
    logger.info(f"Starting Starlette server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
