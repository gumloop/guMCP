import os
import sys
import pytest
from typing import List

pytest_plugins = ['pytest_asyncio']

# Make sure pytest can find the modules we need
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def pytest_addoption(parser):
    """Add command-line options for tests"""
    parser.addoption(
        "--endpoint",
        action="store",
        default="http://localhost:8000/simple-tools-server",
        help="URL for the remote server endpoint (for remote tests)"
    )
    
    parser.addoption(
        "--server-name",
        action="store",
        default="simple-tools-server",
        help="Name of the server to test (for local tests)"
    )


def pytest_collection_modifyitems(items: List[pytest.Item]):
    """Mark tests to skip based on markers and command-line options"""
    for item in items:
        # Add asyncio marker to all async tests if not already marked
        if item.get_closest_marker('asyncio') is None and 'async def' in item.function.__code__.co_code:
            item.add_marker(pytest.mark.asyncio) 