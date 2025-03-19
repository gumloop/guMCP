#!/usr/bin/env python3
"""
Remote server implementation for the Simple Tools Server.
This module provides the Starlette/SSE transport mechanism for web-based usage.
"""

import argparse
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse

from mcp.server.sse import SseServerTransport

from server import server, get_initialization_options, logger

def create_starlette_app():
    """Create a Starlette app with SSE transport"""
    # Create SSE transport
    sse_transport = SseServerTransport("/api/messages/")
    
    async def handle_sse(request):
        """Handle SSE connection requests"""
        logger.info("New SSE connection requested")
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            logger.info("SSE connection established")
            await server.run(
                streams[0],
                streams[1],
                get_initialization_options(),
            )
    
    async def health_check(request):
        """Health check endpoint"""
        return JSONResponse({"status": "ok"})
    
    # Define routes for the Starlette app
    routes = [
        Route("/api/sse", endpoint=handle_sse),
        Route("/health", endpoint=health_check),
        Mount("/api/messages", app=sse_transport.handle_post_message),
    ]
    
    # Create and return the Starlette app
    app = Starlette(
        debug=True,
        routes=routes,
    )
    
    return app

def main():
    """Main entry point for the Starlette server"""
    parser = argparse.ArgumentParser(description="Simple Tools Server (Starlette)")
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