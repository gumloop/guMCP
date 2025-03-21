import os
import sys
import pytest
import argparse
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from clients.RemoteMCPTestClient import RemoteMCPTestClient

tests_path = os.path.join(os.path.dirname(__file__), "tests.py")
with open(tests_path) as f:
    exec(f.read())


def get_endpoint():
    parser = argparse.ArgumentParser(description="Remote MCP Test for simple-tools-server")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/simple-tools-server/local",
        help="SSE endpoint URL (default: http://localhost:8000/simple-tools-server/local)",
    )

    args, _ = parser.parse_known_args()
    return args.endpoint


@pytest_asyncio.fixture(scope="function")
async def client():
    """Fixture to provide a connected client for all tests"""
    endpoint = get_endpoint()
    client = RemoteMCPTestClient()

    await client.connect_to_server(endpoint)
    print(f"Connected to simple-tools-server at {endpoint}")
    yield client
    await client.cleanup()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
