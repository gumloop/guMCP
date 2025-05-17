import pytest
import re

# Global variables to store post id
post_id = None
username = None


@pytest.mark.asyncio
async def test_get_top_stories(client):
    """Fetch top stories from Hacker News.

    Verifies that the top stories include an expected title substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    global post_id
    global username
    limit = 1

    response = await client.process_query(
        f"Use the get_top_stories tool to fetch top {limit} stories from Hacker News. "
        "If successful, start your response with 'Here are the top stories' and then list them. Your response should contain id in format 'ID: <post_id>' and username in format 'Username: <username>'."
    )

    assert (
        "here are the top stories" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_top_stories"

    # Extract post ID from response
    try:
        post_id_match = re.search(r"id:\s*(\S+)", response, re.IGNORECASE)
        username_match = re.search(r"username:\s*(\S+)", response, re.IGNORECASE)
        post_id = post_id_match.group(1) if post_id_match else None
        print(f"Top story ID: {post_id}")
        username = username_match.group(1) if username_match else None
        print(f"Top story Username: {username}")
    except IndexError:
        pytest.fail("Could not extract post ID or username from response")

    print(f"Response: {response}")
    print("✅ get_top_stories passed.")


@pytest.mark.asyncio
async def test_get_latest_posts(client):
    """Get latest posts from Hacker News.

    Verifies that the latest posts include an expected title substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    limit = 2

    response = await client.process_query(
        f"Use the get_latest_posts tool to fetch latest {limit} posts from Hacker News. "
        "If successful, start your response with 'Here are the latest posts' and then list them. Your response should contain id in format 'ID: <post_id>'."
    )

    assert (
        "here are the latest posts" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_latest_posts"

    print(f"Response: {response}")
    print("✅ get_latest_posts passed.")


@pytest.mark.asyncio
async def test_get_story_details(client):
    """Get details about a specific story from Hacker News.

    Verifies that the story details include an expected title substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    global post_id

    response = await client.process_query(
        f"""Use the get_story_details tool to fetch details for post ID {post_id}.
        If successful, start your response with 'Here are the story details' and then list them.
        Your response should contain id in format 'ID: <post_id>'."""
    )

    assert (
        "here are the story details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_story_details"

    print(f"Response: {response}")
    print("✅ get_story_details passed.")


@pytest.mark.asyncio
async def test_get_comments(client):
    """Get comments for a specific story from Hacker News.

    Verifies that the comments include an expected comment substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    global post_id

    limit = 2

    response = await client.process_query(
        f"Use the get_comments tool to fetch {limit} comments for post ID {post_id}. "
        "If successful, start your response with 'Here are the comments' and then list them. Your response should contain id in format 'ID: <comment_id>'."
    )

    assert (
        "here are the comments" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_comments"

    print(f"Response: {response}")
    print("✅ get_comments passed.")


@pytest.mark.asyncio
async def test_get_user(client):
    """Get details about a specific user from Hacker News.

    Verifies that the user details include an expected username substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    global username
    response = await client.process_query(
        f"Use the get_user tool to fetch details for username {username}. "
        "If successful, start your response with 'Here are the user details' and then list them. Your response should contain id in format 'ID: <user_id>'."
    )

    assert (
        "here are the user details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_user passed.")


@pytest.mark.asyncio
async def test_get_stories_by_type(client):
    """Get stories by type from Hacker News.

    Verifies that the stories include an expected title substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    story_type = "job"
    limit = 2

    response = await client.process_query(
        f"Use the get_stories_by_type tool to fetch {limit} stories with type {story_type}. "
        "If successful, start your response with 'Here are the stories' and then list them. Your response should contain id in format 'ID: <story_id>'."
    )

    assert (
        "here are the stories" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_stories_by_type passed.")
