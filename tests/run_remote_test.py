import asyncio
import argparse

from clients.RemoteMCPTestClient import RemoteMCPTestClient


async def main():
    parser = argparse.ArgumentParser(description="Remote MCP Client")
    parser.add_argument(
        "--server", 
        default="http://localhost:8000", 
        help="Server URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    client = RemoteMCPTestClient()
    try:
        await client.connect_to_server(args.server)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
