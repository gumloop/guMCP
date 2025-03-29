import os
import pytest
import asyncio
import pytest_asyncio
from typing import List

from tests.clients.LocalMCPTestClient import LocalMCPTestClient
from tests.clients.RemoteMCPTestClient import RemoteMCPTestClient

pytest_plugins = ["pytest_asyncio"]


# Set asyncio default fixture loop scope to function
def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"


def pytest_addoption(parser):
    """Add command-line options for tests"""
    parser.addoption(
        "--remote",
        action="store_true",
        help="Run tests in remote mode",
    )
    parser.addoption(
        "--endpoint",
        action="store",
        default=None,
        help="URL for the remote server endpoint (for remote tests)",
    )


def pytest_collection_modifyitems(items: List[pytest.Item]):
    """Mark tests to skip based on markers and command-line options"""
    for item in items:
        if (
            item.get_closest_marker("asyncio") is None
            and "async def" in item.function.__code__.co_code
        ):
            item.add_marker(pytest.mark.asyncio)


@pytest_asyncio.fixture(scope="function")
async def client(request):
    """Fixture to provide a connected client for all tests"""
    # Get server name from test path
    test_path = request.node.fspath.strpath
    server_name = os.path.basename(os.path.dirname(test_path))

    is_remote = request.config.getoption("--remote", False)

    if is_remote:
        endpoint = (
            request.config.getoption("--endpoint")
            or f"http://localhost:8000/{server_name}/local"
        )
        client = RemoteMCPTestClient()
        await client.connect_to_server(endpoint)
        print(f"Connected to {server_name} at {endpoint}")
    else:
        client = LocalMCPTestClient()
        await client.connect_to_server_by_name(server_name)
        print(f"Connected to {server_name}")

    try:
        yield client
    finally:
        cleanup_task = asyncio.create_task(client.cleanup())
        await cleanup_task
