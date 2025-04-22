import pytest

# Global variables to store campaign and post IDs
campaign_id = None
post_id = None


@pytest.mark.asyncio
async def test_get_identity(client):
    """Get the current user's identity information.

    Verifies that the identity information is returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_identity tool to fetch the current user's information. "
        "If successful, start your response with 'Here is your identity information' and then list the details."
    )

    assert (
        "here is your identity information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_identity"

    print(f"Response: {response}")
    print("✅ get_identity passed.")


@pytest.mark.asyncio
async def test_get_campaigns(client):
    """Get campaigns owned by the authorized user.

    Verifies that the campaigns are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global campaign_id

    response = await client.process_query(
        "Use the get_campaigns tool to fetch campaigns owned by the user. "
        "If successful, start your response with 'Here are your campaigns' and then list them. "
        "Your response should contain campaign_id in format 'ID: <campaign_id>'."
    )

    assert (
        "here are your campaigns" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaigns"

    # Extract campaign ID from response
    try:
        campaign_id = response.lower().split("id: ")[1].split()[0]
        print(f"Campaign ID: {campaign_id}")
    except IndexError:
        pytest.fail("Could not extract campaign ID from response")

    print(f"Response: {response}")
    print("✅ get_campaigns passed.")


@pytest.mark.asyncio
async def test_get_campaign(client):
    """Get details about a specific campaign.

    Verifies that the campaign details are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global campaign_id

    response = await client.process_query(
        f"Use the get_campaign tool to fetch details for campaign ID {campaign_id}. "
        "If successful, start your response with 'Here are the campaign details' and then list them."
    )

    assert (
        "here are the campaign details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign"

    print(f"Response: {response}")
    print("✅ get_campaign passed.")


@pytest.mark.asyncio
async def test_get_campaign_members(client):
    """Get members of a specific campaign.

    Verifies that the campaign members are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global campaign_id

    response = await client.process_query(
        f"Use the get_campaign_members tool to fetch members for campaign ID {campaign_id}. "
        "If successful, start your response with 'Here are the campaign members' and then list them."
    )

    assert (
        "here are the campaign members" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign_members"

    print(f"Response: {response}")
    print("✅ get_campaign_members passed.")


@pytest.mark.asyncio
async def test_get_campaign_posts(client):
    """Get posts from a specific campaign.

    Verifies that the campaign posts are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global campaign_id, post_id

    response = await client.process_query(
        f"Use the get_campaign_posts tool to fetch posts for campaign ID {campaign_id}. "
        "If successful, start your response with 'Here are the campaign posts' and then list them. "
        "Your response should contain post_id in format 'ID: <post_id>'."
    )

    assert (
        "here are the campaign posts" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign_posts"

    # Extract post ID from response
    try:
        post_id = response.lower().split("id: ")[1].split()[0]
        print(f"Post ID: {post_id}")
    except IndexError:
        pytest.fail("Could not extract post ID from response")

    print(f"Response: {response}")
    print("✅ get_campaign_posts passed.")


@pytest.mark.asyncio
async def test_get_post(client):
    """Get details about a specific post.

    Verifies that the post details are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global post_id

    response = await client.process_query(
        f"Use the get_post tool to fetch details for post ID {post_id}. "
        "If successful, start your response with 'Here are the post details' and then list them."
    )

    assert (
        "here are the post details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_post"

    print(f"Response: {response}")
    print("✅ get_post passed.")
