import os
import sys
import pytest
import asyncio
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from clients.LocalMCPTestClient import LocalMCPTestClient

tests_path = os.path.join(os.path.dirname(__file__), "tests.py")
with open(tests_path) as f:
    exec(f.read())


@pytest_asyncio.fixture(scope="function")
async def client():
    """Fixture to provide a connected client for all tests"""
    client = LocalMCPTestClient()

    await client.connect_to_server_by_name("discord")
    print("Connected to discord server")

    try:
        yield client
    finally:
        cleanup_task = asyncio.create_task(client.cleanup())
        await cleanup_task


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
