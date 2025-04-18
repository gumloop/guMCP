import pytest
import uuid

# Global variables to store created post and comment IDs
created_post_id = None
created_comment_id = None


@pytest.mark.asyncio
async def test_retrieve_reddit_post(client):
    """Fetch top posts in a subreddit with optional size limit.

    Verifies that the reddit post details include an expected title substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    subreddit = "r/MCP"
    limit = 2

    response = await client.process_query(
        f"Use the retrieve_reddit_post tool to fetch top {limit} posts in subreddit {subreddit}. "
        "If successful, start your response with 'Here are the reddit posts' and then list them."
    )

    assert (
        "here are the reddit posts" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from retrieve_reddit_post"

    print(f"Response: {response}")
    print("✅ retrieve_reddit_post passed.")


@pytest.mark.asyncio
async def test_get_reddit_post_details(client):
    """Get detailed content about a specific Reddit post.

    Verifies that the reddit post details include an expected title substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    post_id = "1jp894d"  # guMCP post

    response = await client.process_query(
        f"Use the get_reddit_post_details tool to fetch details for post ID {post_id}. "
        "If successful, start your response with 'Here are the reddit post details' and then list them."
    )

    assert (
        "here are the reddit post details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_reddit_post_details"

    print(f"Response: {response}")
    print("✅ get_reddit_post_details passed.")


@pytest.mark.asyncio
async def test_create_reddit_post(client):
    """Create a new Reddit post.

    Verifies that the reddit post details include an expected title substring.
    Stores the created post ID for use in delete test.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_post_id
    subreddit = "r/test"
    title = "Test Post " + str(uuid.uuid4())
    content = (
        "This is a test post created by the test_create_reddit_post tool in guMCP."
    )

    response = await client.process_query(
        f"""Use the create_reddit_post tool to create a new post in subreddit {subreddit}
        with title {title} and content {content}. If successful, start your response with
        'Created reddit post successfully' and then list the post ID in format 'ID: <post_id>'."""
    )

    assert (
        "created reddit post successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_reddit_post"

    # Extract post ID from response
    try:
        created_post_id = response.lower().split("id: ")[1].split()[0]
        print(f"Created post ID: {created_post_id}")
    except IndexError:
        pytest.fail("Could not extract post ID from response")

    print(f"Response: {response}")
    print("✅ create_reddit_post passed.")


@pytest.mark.asyncio
async def test_create_reddit_comment(client):
    """Create a new Reddit comment.

    Verifies that the reddit comment details include an expected comment substring.
    Stores the created comment ID for use in delete test.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_comment_id

    content = "This is a test comment created by the test_create_reddit_comment tool in guMCP."

    response = await client.process_query(
        f"Use the create_reddit_comment tool to create a new comment on post ID {created_post_id} "
        f"with content {content}. If successful, start your response with 'Created reddit comment successfully' "
        "and then list the comment ID in format 'ID: <comment_id>'."
    )

    assert (
        "created reddit comment successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_reddit_comment"

    # Extract comment ID from response
    try:
        created_comment_id = response.lower().split("id: ")[1].split()[0]
        print(f"Created comment ID: {created_comment_id}")
    except IndexError:
        pytest.fail("Could not extract comment ID from response")

    print(f"Response: {response}")
    print("✅ create_reddit_comment passed.")


@pytest.mark.asyncio
async def test_fetch_post_comments(client):
    """Fetch comments for a specific Reddit post.

    Verifies that the comments include an expected comment substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    post_id = "1jp894d"  # guMCP post
    limit = 2
    sort = "new"
    response = await client.process_query(
        f"Use the fetch_post_comments tool to fetch {limit} comments with comment ids for post ID {post_id} sorted by {sort}. If successful, start your response with 'Here are the comments' and then list them."
    )

    assert (
        "here are the comments" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")

    print("✅ fetch_post_comments passed.")


@pytest.mark.asyncio
async def test_edit_reddit_post(client):
    """Edit a specific Reddit post.

    Verifies that the post is edited successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_post_id:
        pytest.skip("No post ID available - run create_reddit_post test first")

    content = "This is a test post edited by the test_edit_reddit_post tool in guMCP."

    response = await client.process_query(
        f"Use the edit_reddit_post tool to edit post ID {created_post_id} with content {content}. "
        "If successful, start your response with 'Here are the reddit post details' and then list them."
    )

    assert (
        "here are the reddit post details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ edit_reddit_post passed.")


@pytest.mark.asyncio
async def test_edit_reddit_comment(client):
    """Edit a specific Reddit comment.

    Verifies that the comment is edited successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_comment_id:
        pytest.skip("No comment ID available - run create_reddit_comment test first")

    content = (
        "This is a test comment edited by the test_edit_reddit_comment tool in guMCP."
    )

    response = await client.process_query(
        f"Use the edit_reddit_comment tool to edit comment ID {created_comment_id} with content {content}. "
        "If successful, start your response with 'Here are the reddit comment details' and then list them."
    )

    assert (
        "here are the reddit comment details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ edit_reddit_comment passed.")


@pytest.mark.asyncio
async def test_delete_reddit_comment(client):
    """Delete a specific Reddit comment.

    Verifies that the comment is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_comment_id:
        pytest.skip("No comment ID available - run create_reddit_comment test first")

    response = await client.process_query(
        f"Use the delete_reddit_comment tool to delete comment ID {created_comment_id}. "
        "If successful, start your response with 'Here are the reddit comment details' and then list them."
    )

    assert (
        "here are the reddit comment details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ delete_reddit_comment passed.")


@pytest.mark.asyncio
async def test_delete_reddit_post(client):
    """Delete a specific Reddit post.

    Verifies that the post is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_post_id:
        pytest.skip("No post ID available - run create_reddit_post test first")

    response = await client.process_query(
        f"Use the delete_reddit_post tool and delete post with ID {created_post_id}. "
        "If successful, start your response with 'Deleted reddit post successfully' and then list the post ID in format 'ID: <post_id>'."
    )

    assert (
        "deleted reddit post successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ delete_reddit_post passed.")
