import pytest

# Global variables to store IDs across tests
test_post_uri = None

# Replace with your handle
test_handle = "<handle>.bsky.social"


@pytest.mark.asyncio
async def test_get_my_profile(client):
    """Get the current user's profile information.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_my_profile tool to fetch your profile information. "
        "If successful, start your response with 'Profile information' and include your handle."
    )

    assert (
        "profile information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert "handle" in response.lower(), f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_my_profile passed.")


@pytest.mark.asyncio
async def test_create_post(client):
    """Create a new post.

    Args:
        client: The test client fixture for the MCP server.
    """
    global test_post_uri
    test_text = "This is a test post from the Bluesky MCP server."

    response = await client.process_query(
        f"Use the create_post tool to create a new post with text '{test_text}'. "
        "If successful, start your response with 'Post created'"
        "and include the post URI in the response in format 'URI: <post_uri>'"
    )

    assert (
        "post created" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    try:
        test_post_uri = response.split("URI: ")[1].strip()
        print(f"Post URI: {test_post_uri}")
    except IndexError:
        print("No post URI found in response")
        pytest.fail("No post URI found in response")

    print(f"Response: {response}")
    print("✅ create_post passed.")


@pytest.mark.asyncio
async def test_get_posts(client):
    """Get recent posts from a user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_posts tool to fetch recent posts from handle '{test_handle}'. "
        "If successful, start your response with 'Recent posts' and list them."
    )

    assert (
        "recent posts" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert test_handle in response, f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_posts passed.")


@pytest.mark.asyncio
async def test_get_liked_posts(client):
    """Get posts liked by the user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_liked_posts tool to fetch posts you have liked. "
        "If successful, start your response with 'Liked posts' and list them."
    )

    assert (
        "liked posts" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_liked_posts passed.")


@pytest.mark.asyncio
async def test_search_posts(client):
    """Search for posts.

    Args:
        client: The test client fixture for the MCP server.
    """
    search_query = "test"

    response = await client.process_query(
        f"Use the search_posts tool to search for posts containing '{search_query}'. "
        "If successful, start your response with 'Search results' and list them."
    )

    assert (
        "search results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        search_query in response.lower()
    ), f"Search query not found in response: {response}"

    print(f"Response: {response}")
    print("✅ search_posts passed.")


@pytest.mark.asyncio
async def test_search_profiles(client):
    """Search for user profiles.

    Args:
        client: The test client fixture for the MCP server.
    """
    search_query = "test"

    response = await client.process_query(
        f"Use the search_profiles tool to search for profiles containing '{search_query}'. "
        "If successful, start your response with 'Profile search results' and list them."
    )

    assert (
        "profile search results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        search_query in response.lower()
    ), f"Search query not found in response: {response}"

    print(f"Response: {response}")
    print("✅ search_profiles passed.")


@pytest.mark.asyncio
async def test_get_follows(client):
    """Get list of accounts the user follows.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_follows tool to fetch accounts you follow. "
        "If successful, start your response with 'Following' and list the accounts."
    )

    assert (
        "following" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_follows passed.")


@pytest.mark.asyncio
async def test_follow_user(client):
    """Follow another user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the follow_user tool to follow the user with handle '{test_handle}'. "
        "If successful, start your response with 'User followed' and include the handle."
    )

    assert (
        "user followed" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert test_handle in response, f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ follow_user passed.")


@pytest.mark.asyncio
async def test_unfollow_user(client):
    """Unfollow a user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the unfollow_user tool to unfollow the user with handle '{test_handle}'. "
        "If successful, start your response with 'User unfollowed' and include the handle."
    )

    assert (
        "user unfollowed" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert test_handle in response, f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ unfollow_user passed.")


@pytest.mark.asyncio
async def test_mute_user(client):
    """Mute a user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the mute_user tool to mute the user with handle '{test_handle}'. "
        "If successful, start your response with 'User muted' and include the handle."
    )

    assert (
        "user muted" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert test_handle in response, f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ mute_user passed.")


@pytest.mark.asyncio
async def test_unmute_user(client):
    """Unmute a user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the unmute_user tool to unmute the user with handle '{test_handle}'. "
        "If successful, start your response with 'User unmuted' and include the handle."
    )

    assert (
        "user unmuted" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert test_handle in response, f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ unmute_user passed.")


@pytest.mark.asyncio
async def test_block_user(client):
    """Block a user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the block_user tool to block the user with handle '{test_handle}' with reason 'other'. "
        "If successful, start your response with 'User blocked' and include the handle."
    )

    assert (
        "user blocked" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert test_handle in response, f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ block_user passed.")


@pytest.mark.asyncio
async def test_unblock_user(client):
    """Unblock a user.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the unblock_user tool to unblock the user with handle '{test_handle}'. "
        "If successful, start your response with 'User unblocked' and include the handle."
    )

    assert (
        "user unblocked" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert test_handle in response, f"Handle not found in response: {response}"

    print(f"Response: {response}")
    print("✅ unblock_user passed.")


@pytest.mark.asyncio
async def test_delete_post(client):
    """
    Delete a post.
    """
    # Now delete the post
    delete_response = await client.process_query(
        f"Use the delete_post tool to delete the post with URI '{test_post_uri}'"
        "If successful, start your response with 'Post deleted'"
    )

    assert (
        "post deleted" in delete_response.lower()
    ), f"Expected success phrase not found in response: {delete_response}"

    print(f"Delete Response: {delete_response}")
    print("✅ delete_post passed.")
