#!/usr/bin/env python3
"""
Local stdio server implementation for the Simple Tools Server.
This module provides the stdio transport mechanism for local usage.
"""

import asyncio
import logging

import mcp.server.stdio

from server import server, get_initialization_options, logger

async def run_stdio_server():
    """Run the server using stdin/stdout streams"""
    logger.info("Starting stdio server")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            get_initialization_options(),
        )

async def main():
    """Main entry point for the stdio server"""
    await run_stdio_server()

if __name__ == "__main__":
    logger.info("Starting local stdio server")
    asyncio.run(main()) 