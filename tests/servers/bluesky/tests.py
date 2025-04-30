import pytest

# Global variables to store IDs across tests
test_post_uri = None

# Replace with your handle
test_handle = "<handle>.bsky.social"

# ================================
# Test list and read resources
# ================================


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing channels from Teams"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Channels found:")
    for i, resource in enumerate(response.resources):
        print(f"  - {i}: {resource.name} ({resource.uri}) {resource.description}")

    print("✅ Successfully listed channels")


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading a resource from Bluesky"""
    list_response = await client.list_resources()

    profile_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("bluesky://profile/")
    ]

    if len(profile_resource_uri) > 0:
        profile_resource_uri = profile_resource_uri[0]
        response = await client.read_resource(profile_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for profile passed.")

    posts_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("bluesky://posts/")
    ]

    if len(posts_resource_uri) > 0:
        posts_resource_uri = posts_resource_uri[0]
        response = await client.read_resource(posts_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for posts passed.")

    likes_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("bluesky://likes/")
    ]

    if len(likes_resource_uri) > 0:
        likes_resource_uri = likes_resource_uri[0]
        response = await client.read_resource(likes_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for likes passed.")

    follows_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("bluesky://follows/")
    ]

    if len(follows_resource_uri) > 0:
        follows_resource_uri = follows_resource_uri[0]
        response = await client.read_resource(follows_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for follows passed.")

    followers_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("bluesky://followers/")
    ]

    if len(followers_resource_uri) > 0:
        followers_resource_uri = followers_resource_uri[0]
        response = await client.read_resource(followers_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for followers passed.")


@pytest.mark.asyncio
async def test_get_my_profile(client):
    """Get the current user's profile information.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_my_profile tool to fetch your profile information. "
        "If successful, start your response with 'Profile information retrieved successfully' and include your handle."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "profile information retrieved successfully" in response.lower()
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
        "If successful, start your response with 'Post created successfully' "
        "and include the post URI in the response in format 'URI: <post_uri>'"
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "post created successfully" in response.lower()
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
        "If successful, start your response with 'Successfully retrieved posts' and list them."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully retrieved posts" in response.lower()
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
        "If successful, start your response with 'Successfully retrieved liked posts' and list them."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully retrieved liked posts" in response.lower()
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
        "If successful, start your response with 'Successfully found search results' and list them."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully found search results" in response.lower()
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
        "If successful, start your response with 'Successfully found profile search results' and list them."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully found profile search results" in response.lower()
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
        "If successful, start your response with 'Successfully retrieved following list' and list the accounts."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully retrieved following list" in response.lower()
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
        "If successful, start your response with 'Successfully followed user' and include the handle."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully followed user" in response.lower()
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
        "If successful, start your response with 'Successfully unfollowed user' and include the handle."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully unfollowed user" in response.lower()
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
        "If successful, start your response with 'Successfully muted user' and include the handle."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully muted user" in response.lower()
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
        "If successful, start your response with 'Successfully unmuted user' and include the handle."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully unmuted user" in response.lower()
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
        "If successful, start your response with 'Successfully blocked user' and include the handle."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully blocked user" in response.lower()
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
        "If successful, start your response with 'Successfully unblocked user' and include the handle."
    )

    # Check for HTTP error codes
    if "status_code=4" in response:
        pytest.fail(f"HTTP error encountered: {response}")

    assert (
        "successfully unblocked user" in response.lower()
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
        "If successful, start your response with 'Successfully deleted post'"
    )

    # Check for HTTP error codes
    if "status_code=4" in delete_response:
        pytest.fail(f"HTTP error encountered: {delete_response}")

    assert (
        "successfully deleted post" in delete_response.lower()
    ), f"Expected success phrase not found in response: {delete_response}"

    print(f"Delete Response: {delete_response}")
    print("✅ delete_post passed.")
