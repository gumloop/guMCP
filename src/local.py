import sys
import asyncio
import logging
import argparse

import importlib.util
from pathlib import Path

import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gumcp-local-stdio")


async def run_stdio_server(server, get_initialization_options):
    """Run the server using stdin/stdout streams"""
    logger.info("Starting stdio server")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            get_initialization_options(),
        )

async def load_server(server_name):
    """Load a server module by name"""
    # Get the path to the servers directory
    current_dir = Path(__file__).parent.absolute()
    servers_dir = current_dir / "servers"
    
    server_dir = servers_dir / server_name
    server_file = server_dir / "main.py"
    
    if not server_file.exists():
        logger.error(f"Server '{server_name}' not found at {server_file}")
        print(f"Available servers:")
        for item in servers_dir.iterdir():
            if item.is_dir() and (item / "main.py").exists():
                print(f"  - {item.name}")
        sys.exit(1)
    
    # Load the server module
    spec = importlib.util.spec_from_file_location(
        f"{server_name}.server", server_file
    )
    server_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_module)
    
    # Verify required attributes
    if not hasattr(server_module, "server") or not hasattr(server_module, "get_initialization_options"):
        logger.error(f"Server '{server_name}' does not have required server or get_initialization_options")
        sys.exit(1)
    
    return server_module.server, server_module.get_initialization_options

async def main():
    """Main entry point for the stdio server"""
    parser = argparse.ArgumentParser(description="GuMCP Local Stdio Server")
    parser.add_argument(
        "--server", 
        required=True,
        help="Name of the server to run (e.g., simple-tools-server, slack)"
    )
    parser.add_argument(
        "--user-id",
        default="local",
        help="User ID for server context (optional)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Loading server: {args.server}")
    server_creator, get_initialization_options = await load_server(args.server)
    
    # Create the server instance with user_id if provided
    server_instance = server_creator(user_id=args.user_id)
    
    logger.info(f"Starting local stdio server for server: {args.server} with user: {args.user_id or 'None'}")
    await run_stdio_server(server_instance, lambda: get_initialization_options(server_instance))

if __name__ == "__main__":
    logger.info("Starting GuMCP local stdio server")
    asyncio.run(main()) 
