import sys
import asyncio
from clients.LocalMCPTestClient import LocalMCPTestClient


async def main():
    if len(sys.argv) < 2:
        print("Usage: python run_local_test.py <server_name>")
        sys.exit(1)

    client = LocalMCPTestClient()
    try:
        await client.connect_to_server_by_name(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
