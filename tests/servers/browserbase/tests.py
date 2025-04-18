import pytest

WEB_URL = "gumloop.com"


@pytest.mark.asyncio
async def test_load_webpage_tool(client):
    """Test Load Webpage Tool

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the load_webpage_tool tool to fetch content from the website - {WEB_URL}"
        "If successful, start your response with 'Here is the content' and then provide the content"
    )

    assert (
        "here is the content" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from load_webpage_tool"

    print(f"Response: {response}")
    print("✅ load_webpage_tool passed.")
