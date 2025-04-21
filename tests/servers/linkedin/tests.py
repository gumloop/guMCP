import pytest
import uuid

# Add image path to test create image post
image_path = "src/servers/linkedin/assets/icon.png"


@pytest.mark.asyncio
async def test_get_user_info(client):
    """Get information about the authenticated user.

    Verifies that the user info is returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_user_info tool to fetch information about the authenticated user. "
        "If successful, start your response with 'User Information:' and then list the details."
    )

    assert (
        "user information:" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_user_info"

    print(f"Response: {response}")
    print("✅ get_user_info passed.")


@pytest.mark.asyncio
async def test_create_text_post(client):
    """Create a new text post on LinkedIn.

    Verifies that the post is created successfully.
    Stores the created post ID for use in fetch test.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_post_id

    text = f"Test post created by guMCP test suite - {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_text_post tool to create a new post with text: {text}. "
        "If successful, start your response with 'Post created successfully!' and then list the post ID."
    )

    assert (
        "post created successfully!" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_text_post"

    print(f"Response: {response}")
    print("✅ create_text_post passed.")


@pytest.mark.asyncio
async def test_create_article_post(client):
    """Create a new article post on LinkedIn.

    Verifies that the article post is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    post_content = f"Check out this interesting article! - {uuid.uuid4()}"
    article_url = "https://example.com/article"
    article_title = "Test Article Title"
    article_description = (
        "This is a test article description created by guMCP test suite."
    )

    response = await client.process_query(
        f"Use the create_article_post tool to create a new post with content: {post_content}, "
        f"article URL: {article_url}, title: {article_title}, and description: {article_description}. "
        "If successful, start your response with 'Post created successfully!' and then list the post ID."
    )

    assert (
        "post created successfully!" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_article_post"

    print(f"Response: {response}")
    print("✅ create_article_post passed.")


@pytest.mark.asyncio
async def test_create_image_post(client):
    """Create a new image post on LinkedIn.

    Verifies that the image post is created successfully.
    Creates a temporary test image and cleans it up after the test.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_image_path

    # Create a random test image
    caption = f"Test image post created by guMCP test suite - {uuid.uuid4()}"
    image_description = "This is a test image description"
    image_title = "Test Image Title"

    response = await client.process_query(
        f"Use the create_image_post tool to create a new post with image path: {image_path}, "
        f"caption: {caption}, image description: {image_description}, and image title: {image_title}. "
        "If successful, start your response with 'Post created successfully!' and then list the post ID."
    )

    assert (
        "post created successfully!" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_image_post"

    print(f"Response: {response}")
    print("✅ create_image_post passed.")


@pytest.mark.asyncio
async def test_fetch_user_posts(client):
    """Fetch recent posts created by the authenticated user.

    Verifies that the posts are fetched successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the fetch_user_posts tool to fetch recent posts created by the authenticated user. "
        "If successful, start your response with 'Fetched Posts:' and then list them."
    )

    assert (
        "fetched posts:" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from fetch_user_posts"

    print(f"Response: {response}")
    print("✅ fetch_user_posts passed.")
