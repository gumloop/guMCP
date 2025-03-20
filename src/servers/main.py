import argparse
import logging
import sys

# Configure logging for the main script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gumcp-server")

def main():
    """Parse arguments and launch the GuMCP server"""
    parser = argparse.ArgumentParser(description="GuMCP Server")
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host for server"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port for server"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting GuMCP server on {args.host}:{args.port}")
    # Import and run the remote server
    from remote import main as remote_main
    # Pass the CLI arguments to the remote server
    sys.argv = [sys.argv[0]]  # Clear existing args
    if args.host:
        sys.argv.extend(["--host", args.host])
    if args.port:
        sys.argv.extend(["--port", str(args.port)])
    remote_main()

if __name__ == "__main__":
    main() 