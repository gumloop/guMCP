import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing timelines from X"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Timelines found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri})")

    print("✅ Successfully listed timelines")


@pytest.mark.asyncio
async def test_read_home_timeline_tool(client):
    """Test reading tweets from home timeline"""
    # Test read_home_timeline tool
    response = await client.process_query(
        "Use the read_home_timeline tool to read tweets from my home timeline"
    )

    assert response, "No response received from read_home_timeline tool"
    print("Tweets read:")
    print(f"\t{response}")

    print("✅ Successfully read tweets from home timeline")


@pytest.mark.asyncio
async def test_read_user_tweets_tool(client):
    """Test reading tweets from a specific user"""
    # Test read_user_tweets tool with a known username
    test_username = "Twitter"  # Using official Twitter account for testing
    response = await client.process_query(
        f"Use the read_user_tweets tool to read tweets from user {test_username}"
    )

    assert response, "No response received from read_user_tweets tool"
    print("User tweets read:")
    print(f"\t{response}")

    print("✅ Successfully read user tweets")


@pytest.mark.asyncio
async def test_post_tweet_tool(client):
    """Test posting a tweet"""
    # Test post_tweet tool
    test_tweet = "This is a test tweet from the MCP server! " + \
                 "#testing #automated " + \
                 f"Timestamp: {pytest.helpers.get_timestamp()}"
    
    response = await client.process_query(
        f"Use the post_tweet tool to post '{test_tweet}'"
    )

    assert "successfully" in response.lower(), f"Failed to post tweet: {response}"
    print("Tweet posted:")
    print(f"\t{response}")

    print("✅ Successfully posted tweet")


@pytest.mark.asyncio
async def test_get_tweet_tool(client):
    """Test getting a specific tweet by ID"""
    # First post a tweet to get its ID
    test_tweet = "Test tweet for getting by ID " + \
                 f"Timestamp: {pytest.helpers.get_timestamp()}"
    
    post_response = await client.process_query(
        f"Use the post_tweet tool to post '{test_tweet}'"
    )
    
    # Extract tweet ID from response
    import re
    tweet_id_match = re.search(r"Tweet ID: (\d+)", post_response)
    assert tweet_id_match, "Could not find tweet ID in response"
    
    tweet_id = tweet_id_match.group(1)
    
    # Test get_tweet tool
    response = await client.process_query(
        f"Use the get_tweet tool to get the tweet with ID {tweet_id}"
    )

    assert response, "No response received from get_tweet tool"
    assert test_tweet in response, "Posted tweet content not found in retrieved tweet"
    
    print("Tweet retrieved:")
    print(f"\t{response}")

    print("✅ Successfully retrieved tweet by ID")


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading tweets directly from a timeline resource"""
    # First list resources to get a valid timeline URI
    response = await client.list_resources()
    assert len(response.resources) > 0, "No timelines found"

    # Get home timeline URI
    timeline_uri = next(
        (r.uri for r in response.resources if "home" in r.uri), 
        response.resources[0].uri
    )

    # Test reading the resource
    response = await client.read_resource(timeline_uri)
    assert len(response.contents) > 0, "No content received"
    assert response.contents[0].text, "Empty content received"

    print("Timeline content read:")
    print(f"\t{response.contents[0].text}")

    print("✅ Successfully read timeline resource")


# Helper for generating unique timestamps
@pytest.fixture(autouse=True)
def setup_helpers(monkeypatch):
    import time
    
    class Helpers:
        @staticmethod
        def get_timestamp():
            return str(int(time.time()))
    
    pytest.helpers = Helpers
