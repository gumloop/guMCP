import re
import pytest
import uuid
import time
import logging


def handle_rate_limit(response, client=None):
    """Check if response contains rate limit error (HTTP 429) and skip test if detected

    Args:
        response: The response text or object to check
        client: Optional client object that might contain logs with rate limit information
    """
    # Convert response to string for text checking
    response_str = str(response)

    # Check for HTTP 429 status code or "Too Many Requests" message
    if "429" in response_str or "too many requests" in response_str.lower():
        print("⚠️ Rate limit hit (HTTP 429). Skipping test.")
        pytest.skip("Rate limit exceeded. Try again later.")

    # If client is provided, also check its logs for 429 errors
    if client and hasattr(client, "last_log"):
        client_log = str(getattr(client, "last_log", ""))
        if "429" in client_log or "too many requests" in client_log.lower():
            print("⚠️ Rate limit hit (HTTP 429 in logs). Skipping test.")
            pytest.skip("Rate limit exceeded. Try again later.")


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing tweets from timeline"""
    response = await client.list_resources()

    # Check for rate limit (HTTP 429)
    handle_rate_limit(response, client)

    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    print("Tweets found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    # If no tweets were found, it might be due to rate limiting that wasn't detected earlier
    if len(response.resources) == 0:
        print(
            "⚠️ No tweets found. This may be due to authentication issues or API restrictions."
        )

    print("✅ Successfully listed tweets")


@pytest.mark.asyncio
async def test_read_tweet(client):
    """Test reading a tweet by URI"""
    # First list tweets to get a valid tweet ID
    list_response = await client.list_resources()
    handle_rate_limit(list_response, client)

    # Skip test if no tweets found
    if not list_response.resources:
        print("⚠️ No tweets found to test reading")
        pytest.skip("No tweets available for testing")
        return

    # Get the first tweet resource
    tweet_resource = list_response.resources[0]
    response = await client.read_resource(tweet_resource.uri)
    handle_rate_limit(response, client)

    assert (
        response and response.contents
    ), f"Response should contain tweet contents: {response}"
    assert len(response.contents[0].text) > 0, "Tweet content should be available"

    print("Tweet read:")
    print(f"  - Content: {response.contents[0].text[:100]}...")

    print("✅ Successfully read tweet")


@pytest.mark.asyncio
async def test_search_recent_tweet(client):
    """Test searching for recent tweets"""
    response = await client.process_query(
        "Use the search_recent_tweet tool to search for tweets containing 'test'. If you find any tweets, start your response with 'SEARCH_SUCCESS:' followed by the results. If there are no results or if there's an error, start with 'SEARCH_FAILED:' and explain why."
    )

    handle_rate_limit(response, client)

    # Verify response contains specific search success prefix
    assert (
        "SEARCH_SUCCESS:" in response or "SEARCH_FAILED:" in response
    ), f"Search operation did not return expected format: {response}"

    # If search failed, check if it's due to no results rather than a tool error
    if "SEARCH_FAILED:" in response:
        assert (
            "no tweets" in response.lower() or "no results" in response.lower()
        ), f"Search failed with error: {response}"

    print("Search results:")
    print(f"{response}")

    print("✅ Search recent tweets functionality working")


@pytest.mark.asyncio
async def test_get_user_profile(client):
    """Test getting a user profile"""
    # Use the current official account
    test_username = "X"

    response = await client.process_query(
        f"Use the get_user_profile tool to get information about the user @{test_username}. Start your response with 'PROFILE_SUCCESS:' if you successfully retrieved the profile, or 'PROFILE_FAILED:' if there was an error."
    )

    handle_rate_limit(response, client)

    # Verify response contains specific profile success prefix
    assert (
        "PROFILE_SUCCESS:" in response
    ), f"User profile retrieval did not succeed: {response}"
    # Also verify the response contains the username we searched for
    assert (
        test_username.lower() in response.lower()
    ), f"Response does not contain the requested username: {response}"

    print("User profile results:")
    print(f"{response}")

    print("✅ Get user profile functionality working")


@pytest.mark.asyncio
async def test_get_user_posts(client):
    """Test getting user posts"""
    # Use the current official account
    test_username = "X"

    response = await client.process_query(
        f"Use the get_user_posts tool to get the latest tweets from @{test_username}. Set max_results to 5. Start your response with 'POSTS_SUCCESS:' if you successfully retrieved the posts, or 'POSTS_FAILED:' if there was an error."
    )

    handle_rate_limit(response, client)

    # Verify response contains specific posts success prefix
    assert (
        "POSTS_SUCCESS:" in response
    ), f"User posts retrieval did not succeed: {response}"
    assert (
        test_username.lower() in response.lower()
    ), f"Response does not contain the requested username: {response}"

    print("User posts results:")
    print(f"{response}")

    print("✅ Get user posts functionality working")


@pytest.mark.asyncio
async def test_get_user_home_timeline(client):
    """Test getting user home timeline"""
    # Use the current official account since we need a username
    test_username = "gumloop_ai"

    response = await client.process_query(
        f"Use the get_user_home_timeline tool to get tweets from @{test_username}'s home timeline. Set max_results to 5. Start your response with 'TIMELINE_SUCCESS:' if you successfully retrieved the timeline, or 'TIMELINE_FAILED:' if there was an error."
    )

    handle_rate_limit(response, client)

    # Verify response contains specific timeline success prefix
    assert (
        "TIMELINE_SUCCESS:" in response
    ), f"Home timeline retrieval did not succeed: {response}"
    assert (
        "timeline" in response.lower()
    ), f"Response does not mention timeline: {response}"

    print("Home timeline results:")
    print(f"{response}")

    print("✅ Get user home timeline functionality working")


@pytest.mark.asyncio
async def test_get_user_mentions(client):
    """Test getting user mentions"""
    # Use the current official account
    test_username = "X"

    response = await client.process_query(
        f"Use the get_user_mentions tool to get tweets mentioning @{test_username}. Set max_results to 5. Start your response with 'MENTIONS_SUCCESS:' if you successfully retrieved mentions, or 'MENTIONS_FAILED:' if there was an error."
    )

    handle_rate_limit(response, client)

    # Verify response contains specific mentions success prefix
    assert (
        "MENTIONS_SUCCESS:" in response
    ), f"User mentions retrieval did not succeed: {response}"
    assert (
        "mention" in response.lower()
    ), f"Response does not mention mentions: {response}"

    print("User mentions results:")
    print(f"{response}")

    print("✅ Get user mentions functionality working")


@pytest.mark.asyncio
async def test_get_tweet_by_id(client):
    """Test getting a tweet by ID"""
    # Use a known, popular tweet ID instead of relying on listing resources
    # This is Elon Musk's "the bird is freed" tweet when he acquired Twitter
    test_tweet_id = "1585841080431321088"

    response = await client.process_query(
        f"Use the get_tweet_by_id tool to get information about the tweet with ID {test_tweet_id}. Start your response with 'TWEET_SUCCESS:' if you successfully retrieved the tweet, or 'TWEET_FAILED:' if there was an error."
    )

    handle_rate_limit(response, client)

    # Verify response contains specific tweet success prefix
    assert "TWEET_SUCCESS:" in response, f"Tweet retrieval did not succeed: {response}"
    assert (
        test_tweet_id in response
    ), f"Response does not contain the requested tweet ID: {response}"

    print("Get tweet by ID results:")
    print(f"{response}")

    print("✅ Get tweet by ID functionality working")


@pytest.mark.asyncio
async def test_create_and_delete_tweet(client):
    """Test creating and then deleting a tweet"""
    # Create a unique test message to avoid duplicates
    test_message = f"This tweet is being made from guMCP! {uuid.uuid4()} - Please ignore this automated test."

    # Create the tweet
    create_response = await client.process_query(
        f"Use the create_tweet tool to post a new tweet with the text: '{test_message}'. Start your response with 'TWEET_CREATED:' followed by the tweet ID if successful, or 'TWEET_CREATION_FAILED:' if there was an error."
    )

    handle_rate_limit(create_response, client)

    # Verify the tweet was created and extract the ID
    assert (
        "TWEET_CREATED:" in create_response
    ), f"Tweet creation did not succeed: {create_response}"

    # Extract tweet ID using regex - be more flexible with the pattern
    id_match = re.search(r"TWEET_CREATED:\s*(\d+)", create_response)
    if not id_match:
        id_match = re.search(r"ID:?\s*(\d+)", create_response)

    tweet_id = id_match.group(1) if id_match else None

    if not tweet_id:
        print("⚠️ Could not extract tweet ID from response, skipping deletion test")
        pytest.skip("Could not extract tweet ID")
        return

    print(f"Created tweet with ID: {tweet_id}")

    # Small delay to ensure the tweet is processed before deletion
    time.sleep(1)

    # Now delete the tweet
    delete_response = await client.process_query(
        f"Use the delete_tweet tool to delete the tweet with ID {tweet_id}. Start your response with 'TWEET_DELETED:' if successful, or 'TWEET_DELETION_FAILED:' if there was an error."
    )

    handle_rate_limit(delete_response, client)

    # Verify the tweet was deleted
    assert (
        "TWEET_DELETED:" in delete_response
    ), f"Tweet deletion did not succeed: {delete_response}"
    assert (
        tweet_id in delete_response
    ), f"Response does not reference the deleted tweet ID: {delete_response}"

    print(f"Deleted tweet with ID: {tweet_id}")

    print("✅ Create and delete tweet functionality working")
