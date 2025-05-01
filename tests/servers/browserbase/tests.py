import pytest
import json

WEB_URL = "gumloop.com"


@pytest.mark.asyncio
async def test_load_webpage_tool(client):
    """Test Load Webpage Tool

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the load_webpage_tool tool to fetch content from the website - {WEB_URL}. "
        "Parse the JSON response and verify it has status, url, and content fields."
    )

    assert (
        "status" in response.lower()
        and "url" in response.lower()
        and "content" in response.lower()
    ), f"Expected JSON fields not found in response: {response}"
    assert response, "No response returned from load_webpage_tool"

    print(f"Response: {response}")
    print("✅ load_webpage_tool passed.")
