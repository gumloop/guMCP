import sys
import asyncio
import logging
import argparse
import importlib.util
from pathlib import Path

import mcp.server.stdio

from fastmcp_utils import load_fastmcp_server

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gumcp-local-stdio")


async def run_stdio_server(server, get_initialization_options):
    """Run the server using stdin/stdout streams"""
    logger.info("Starting stdio server")

    # Check if this is a FastMCP server (different interface)
    from mcp.server.fastmcp import FastMCP

    if isinstance(server, FastMCP):
        # Need to use FastMCP's async interface instead of the direct run() method
        # to avoid event loop conflicts
        await server.run_stdio_async()
    else:
        # guMCP server approach
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                get_initialization_options(),
            )


async def load_server(server_name):
    """Load a server module by name"""
    # Get the path to the servers directory
    servers_dir = Path(__file__).parent.absolute()

    server_dir = servers_dir / server_name
    server_file = server_dir / "main.py"

    # Check if server file exists
    if not server_file.exists():
        logger.error(f"Server '{server_name}' not found at {server_file}")
        print("Available servers:")
        for item in servers_dir.iterdir():
            if item.is_dir() and (item / "main.py").exists():
                print(f"  - {item.name}")
        sys.exit(1)

    # First try to load as a FastMCP server
    server_factory, init_options_factory = load_fastmcp_server(server_file, server_name)
    if server_factory and init_options_factory:
        logger.info(f"Loading as FastMCP server: {server_name}")
        return server_factory, init_options_factory

    # Load the standard server module
    try:
        spec = importlib.util.spec_from_file_location(
            f"{server_name}.server", server_file
        )
        server_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server_module)

        # Verify required attributes
        if not hasattr(server_module, "server") or not hasattr(
            server_module, "get_initialization_options"
        ):
            logger.error(
                f"Server '{server_name}' does not have required server or get_initialization_options"
            )
            sys.exit(1)

        return server_module.server, server_module.get_initialization_options
    except Exception as e:
        logger.error(f"Failed to load server {server_name}: {e}")
        sys.exit(1)


async def main():
    """Main entry point for the stdio server"""
    parser = argparse.ArgumentParser(description="guMCP Local Stdio Server")
    parser.add_argument(
        "--server",
        required=True,
        help="Name of the server to run (e.g., simple-tools-server, slack)",
    )
    parser.add_argument(
        "--user-id", default="local", help="User ID for server context (optional)"
    )

    args = parser.parse_args()

    logger.info(f"Loading server: {args.server}")
    server_creator, get_initialization_options = await load_server(args.server)

    # Create the server instance with user_id if provided
    server_instance = server_creator(user_id=args.user_id)

    logger.info(
        f"Starting local stdio server for server: {args.server} with user: {args.user_id or 'None'}"
    )
    await run_stdio_server(
        server_instance, lambda: get_initialization_options(server_instance)
    )


if __name__ == "__main__":
    logger.info("Starting guMCP local stdio server")
    asyncio.run(main())
