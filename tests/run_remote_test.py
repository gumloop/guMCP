import asyncio
import argparse

from clients.RemoteMCPTestClient import RemoteMCPTestClient


async def main():
    parser = argparse.ArgumentParser(description="Remote MCP Client")
    parser.add_argument(
        "--endpoint", 
        default="http://localhost:8000/api/simple-tools-server/sse", 
        help="SSE endpoint URL (default: http://localhost:8000/api/simple-tools-server/sse)"
    )
    
    args = parser.parse_args()
    
    client = RemoteMCPTestClient()
    try:
        await client.connect_to_server(args.endpoint)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
