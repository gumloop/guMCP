#!/usr/bin/env python3
"""
Main entry point for the Simple Tools Server.
This script can launch the server in either local (stdio) or remote (FastAPI/SSE) mode.
"""

import argparse
import asyncio
import logging
import sys

# Configure logging for the main script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("simple-tools-server-main")

def main():
    """Parse arguments and launch the appropriate server mode"""
    parser = argparse.ArgumentParser(description="Simple Tools Server")
    parser.add_argument(
        "--mode", 
        choices=["stdio", "sse"], 
        default="stdio", 
        help="Server mode: stdio (default) or sse (FastAPI/SSE)"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host for FastAPI server (only used in sse mode)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port for FastAPI server (only used in sse mode)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "stdio":
        logger.info("Starting server in stdio mode")
        # Import and run the local stdio server
        from local import main as local_main
        asyncio.run(local_main())
    else:  # sse mode
        logger.info(f"Starting server in SSE mode on {args.host}:{args.port}")
        # Import and run the remote FastAPI server
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