import pytest


@pytest.mark.asyncio
async def test_get_video_details(client):
    """Fetch metadata about a single YouTube video.

    Verifies that the video details include an expected title substring.

    Args:
        client: The test client fixture for the MCP server.
    """
    video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up

    response = await client.process_query(
        f"Use the get_video_details tool to fetch details for video ID {video_id}. If successful, start your response with 'Here are the video details' and then list them."
    )

    assert (
        "here are the video details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_video_details"
    assert (
        "never gonna give you up" in response.lower()
    ), f"Unexpected video details: {response}"
    print(f"Response: {response}")
    print("✅ get_video_details passed.")


@pytest.mark.asyncio
async def test_get_video_statistics(client):
    """Fetch view count, likes, and comment count of a video.

    Args:
        client: The test client fixture for the MCP server.
    """
    video_id = "dQw4w9WgXcQ"

    response = await client.process_query(
        f"Use the get_video_statistics tool to fetch statistics for video ID {video_id}. If successful, start your response with 'Here are the video statistics' and then list them."
    )

    assert (
        "here are the video statistics" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_video_statistics"
    assert "view" in response.lower(), f"Unexpected video statistics: {response}"
    print(f"Response: {response}")
    print("✅ get_video_statistics passed.")


@pytest.mark.asyncio
async def test_search_videos(client):
    """Search YouTube globally using a keyword.

    Args:
        client: The test client fixture for the MCP server.
    """
    query = "machine learning"

    response = await client.process_query(
        f"Use the search_videos tool to search for videos about {query}. If you find any videos, start your response with 'Here are the search results' and then list them."
    )

    assert (
        "here are the search results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from search_videos"
    assert any(
        word in response.lower() for word in query.split()
    ), f"Unexpected search result: {response}"
    print(f"Response: {response}")
    print("✅ search_videos passed.")


@pytest.mark.asyncio
async def test_list_channel_videos(client):
    """List recent uploads from a YouTube channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"  # Google Developers

    response = await client.process_query(
        f"Use the list_channel_videos tool to list videos from channel ID {channel_id}. If you find any videos, start your response with 'Here are the channel videos' and then list them."
    )

    assert (
        "here are the channel videos" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No videos returned from list_channel_videos"
    assert "video" in response.lower(), f"Unexpected video content: {response}"
    print(f"Response: {response}")
    print("✅ list_channel_videos passed.")


@pytest.mark.asyncio
async def test_get_channel_details(client):
    """Retrieve metadata such as title and description of a channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    response = await client.process_query(
        f"Use the get_channel_details tool to fetch metadata for channel ID {channel_id}. If successful, start your response with 'Here are the channel details' and then list them."
    )

    assert (
        "here are the channel details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_channel_details"
    assert (
        "google for developers" in response.lower()
    ), f"Unexpected channel details: {response}"
    print(f"Response: {response}")
    print("✅ get_channel_details passed.")


@pytest.mark.asyncio
async def test_get_channel_statistics(client):
    """Fetch subscriber count and total views for a channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    response = await client.process_query(
        f"Use the get_channel_statistics tool to fetch stats for channel ID {channel_id}. If successful, start your response with 'Here are the channel statistics' and then list them."
    )

    assert (
        "here are the channel statistics" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response from get_channel_statistics"
    assert "subscriber" in response.lower(), f"Unexpected channel stats: {response}"
    print(f"Response: {response}")
    print("✅ get_channel_statistics passed.")


@pytest.mark.asyncio
async def test_list_channel_playlists(client):
    """List all playlists created by a YouTube channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    response = await client.process_query(
        f"Use the list_channel_playlists tool to get playlists for channel ID {channel_id}. If you find any playlists, start your response with 'Here are the channel playlists' and then list them."
    )

    assert (
        "here are the channel playlists" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_channel_playlists"
    assert "playlist" in response.lower(), f"No playlist info found: {response}"
    print(f"Response: {response}")
    print("✅ list_channel_playlists passed.")


@pytest.mark.asyncio
async def test_list_playlist_items(client):
    """Fetch the list of videos inside a specific playlist.

    Args:
        client: The test client fixture for the MCP server.
    """
    playlist_id = "PL8WEHjU-hK_6SSza5t3DJ57ruDs4pBKhk"

    response = await client.process_query(
        f"Use the list_playlist_items tool to list videos from playlist ID {playlist_id}. If you find any videos, start your response with 'Here are the playlist items' and then list them."
    )

    assert (
        "here are the playlist items" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response from list_playlist_items"
    assert (
        "video" in response.lower()
    ), f"Unexpected content in playlist items: {response}"
    print(f"Response: {response}")
    print("✅ list_playlist_items passed.")


@pytest.mark.asyncio
async def test_get_playlist_details(client):
    """Retrieve metadata such as title and description of a playlist.

    Args:
        client: The test client fixture for the MCP server.
    """
    playlist_id = "PL8WEHjU-hK_6SSza5t3DJ57ruDs4pBKhk"

    response = await client.process_query(
        f"Use the get_playlist_details tool to get details of playlist ID {playlist_id}. If successful, start your response with 'Here are the playlist details' and then list them."
    )

    assert (
        "here are the playlist details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_playlist_details"
    assert "title" in response.lower(), f"Unexpected playlist metadata: {response}"
    print(f"Response: {response}")
    print("✅ get_playlist_details passed.")
