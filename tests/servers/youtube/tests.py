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
        f"Use the get_video_details tool to fetch details for video ID {video_id}"
    )

    assert response, "No response returned from get_video_details"
    assert "never gonna give you up" in response.lower(), f"Unexpected video details: {response}"
    print("✅ get_video_details passed.")


@pytest.mark.asyncio
async def test_get_video_statistics(client):
    """Fetch view count, likes, and comment count of a video.

    Args:
        client: The test client fixture for the MCP server.
    """
    video_id = "dQw4w9WgXcQ"

    response = await client.process_query(
        f"Use the get_video_statistics tool to fetch statistics for video ID {video_id}"
    )

    assert response, "No response returned from get_video_statistics"
    assert "view" in response.lower(), f"Unexpected video statistics: {response}"
    print("✅ get_video_statistics passed.")


@pytest.mark.asyncio
async def test_search_videos(client):
    """Search YouTube globally using a keyword.

    Args:
        client: The test client fixture for the MCP server.
    """
    query = "machine learning"

    response = await client.process_query(
        f"Use the search_videos tool to search for videos about {query}"
    )

    assert response, "No response returned from search_videos"
    assert any(word in response.lower() for word in query.split()), f"Unexpected search result: {response}"
    print("✅ search_videos passed.")


@pytest.mark.asyncio
async def test_list_channel_videos(client):
    """List recent uploads from a YouTube channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"  # Google Developers

    response = await client.process_query(
        f"Use the list_channel_videos tool to list videos from channel ID {channel_id}"
    )

    assert response, "No videos returned from list_channel_videos"
    assert "video" in response.lower(), f"Unexpected video content: {response}"
    print("✅ list_channel_videos passed.")


@pytest.mark.asyncio
async def test_get_channel_details(client):
    """Retrieve metadata such as title and description of a channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    response = await client.process_query(
        f"Use the get_channel_details tool to fetch metadata for channel ID {channel_id}"
    )

    assert response, "No response returned from get_channel_details"
    assert "google developers" in response.lower(), f"Unexpected channel details: {response}"
    print("✅ get_channel_details passed.")


@pytest.mark.asyncio
async def test_get_channel_statistics(client):
    """Fetch subscriber count and total views for a channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    response = await client.process_query(
        f"Use the get_channel_statistics tool to fetch stats for channel ID {channel_id}"
    )

    assert response, "No response from get_channel_statistics"
    assert "subscriber" in response.lower(), f"Unexpected channel stats: {response}"
    print("✅ get_channel_statistics passed.")


@pytest.mark.asyncio
async def test_list_channel_playlists(client):
    """List all playlists created by a YouTube channel.

    Args:
        client: The test client fixture for the MCP server.
    """
    channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    response = await client.process_query(
        f"Use the list_channel_playlists tool to get playlists for channel ID {channel_id}"
    )

    assert response, "No response returned from list_channel_playlists"
    assert "playlist" in response.lower(), f"No playlist info found: {response}"
    print("✅ list_channel_playlists passed.")


@pytest.mark.asyncio
async def test_list_playlist_items(client):
    """Fetch the list of videos inside a specific playlist.

    Args:
        client: The test client fixture for the MCP server.
    """
    playlist_id = "PL590L5WQmH8fJ54FzE4OMo20Rgg1nV2fN"

    response = await client.process_query(
        f"Use the list_playlist_items tool to list videos from playlist ID {playlist_id}"
    )

    assert response, "No response from list_playlist_items"
    assert "video" in response.lower(), f"Unexpected content in playlist items: {response}"
    print("✅ list_playlist_items passed.")


@pytest.mark.asyncio
async def test_get_playlist_details(client):
    """Retrieve metadata such as title and description of a playlist.

    Args:
        client: The test client fixture for the MCP server.
    """
    playlist_id = "PL590L5WQmH8fJ54FzE4OMo20Rgg1nV2fN"

    response = await client.process_query(
        f"Use the get_playlist_details tool to get details of playlist ID {playlist_id}"
    )

    assert response, "No response returned from get_playlist_details"
    assert "title" in response.lower(), f"Unexpected playlist metadata: {response}"
    print("✅ get_playlist_details passed.")
