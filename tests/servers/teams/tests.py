import pytest
import uuid
from datetime import datetime, timedelta

# Global variables to store created resources
created_team_id = None
created_channel_id = None
created_meeting_id = None


# Add the below variables to the tests.py file before running the tests
chat_id = ""  # Hardcoded chat ID for testing
test_user_email = ""  # Hardcoded test user email for testing


# ===== LIST RESOURCE Operations =====


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


# ===== CREATE Operations =====


@pytest.mark.asyncio
async def test_create_team(client):
    """Create a new Microsoft Teams team.

    Verifies that the team is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    team_name = f"Test Team {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the create_team tool to create a new team with name "{team_name}".
        If successful, start your response with 'Team created successfully' and then include the team ID.
        Your format for ID will be ID: <created_team_id>"""
    )

    assert (
        "team created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_team"

    try:
        global created_team_id
        created_team_id = response.split("ID: ")[1].split()[0]
        print(f"Created team ID: {created_team_id}")
    except IndexError:
        pytest.fail("Could not extract team ID from response")

    print(f"Response: {response}")
    print("✅ create_team passed.")


# ===== READ Operations =====


@pytest.mark.asyncio
async def test_get_teams(client):
    """Get the list of teams the user is a member of.

    Verifies that the teams list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        """Use the get_teams tool to list all teams.
        If successful, start your response with 'Here are the Teams' and then list them."""
    )

    assert (
        "here are the teams" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_teams"

    print(f"Response: {response}")
    print("✅ get_teams passed.")


@pytest.mark.asyncio
async def test_get_team_details(client):
    """Get details of a specific team.

    Verifies that team details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id:
        pytest.skip("No team ID available - run create_team test first")

    response = await client.process_query(
        f"""Use the get_team_details tool to fetch details for team ID {created_team_id}.
        If successful, start your response with 'Here are the team details' and then list them."""
    )

    assert (
        "here are the team details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_team_details"

    print(f"Response: {response}")
    print("✅ get_team_details passed.")


@pytest.mark.asyncio
async def test_get_team_members(client):
    """Get the list of members in a team.

    Verifies that team members are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id:
        pytest.skip("No team ID available - run create_team test first")

    response = await client.process_query(
        f"""Use the get_team_members tool to fetch members from team ID {created_team_id}.
        If successful, start your response with 'Here are the team members' and then list them."""
    )

    assert (
        "here are the team members" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_team_members"

    print(f"Response: {response}")
    print("✅ get_team_members passed.")


@pytest.mark.asyncio
async def test_get_channels(client):
    """Get the list of channels in a team.

    Verifies that the channels list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id:
        pytest.skip("No team ID available - run create_team test first")

    response = await client.process_query(
        f"""Use the get_channels tool to list channels for team ID {created_team_id}.
        If successful, start your response with 'Here are the channels' and then list them."""
    )

    assert (
        "here are the channels" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_channels"

    print(f"Response: {response}")
    print("✅ get_channels passed.")


@pytest.mark.asyncio
async def test_get_chats(client):
    """Get the list of chats for the user.

    Verifies that the chats list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        """Use the get_chats tool to list all chats.
        If successful, start your response with 'Here are the chats' and then list them."""
    )

    assert (
        "here are the chats" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_chats"

    print(f"Response: {response}")
    print("✅ get_chats passed.")


@pytest.mark.asyncio
async def test_get_chat_messages(client):
    """Get messages from a specific chat.

    Verifies that chat messages are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not chat_id:
        pytest.skip("No chat ID available - run get_chats test first and set chat_id")

    response = await client.process_query(
        f"""Use the get_chat_messages tool to fetch messages from chat ID {chat_id}.
        If successful, start your response with 'Here are the chat messages' and then list them."""
    )

    assert (
        "here are the chat messages" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_chat_messages"

    print(f"Response: {response}")
    print("✅ get_chat_messages passed.")


# ===== CREATE Operations =====


@pytest.mark.asyncio
async def test_create_channel(client):
    """Create a new channel in a team.

    Verifies that the channel is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id:
        pytest.skip("No team ID available - run create_team test first")

    # Set channel details
    display_name = f"Test Channel {uuid.uuid4()}"
    description = "This is a test channel created by the test_create_channel tool."
    membership_type = "standard"

    response = await client.process_query(
        f"""Use the create_channel tool to create a new channel in team ID {created_team_id}
        with display name "{display_name}", description "{description}", and membership type "{membership_type}".
        If successful, start your response with 'Created channel successfully' and then include the channel ID.
        Your format for ID will be ID: <channel_id>"""
    )

    assert (
        "created channel successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_channel"

    # Extract channel ID from response
    try:
        global created_channel_id
        created_channel_id = response.split("ID: ")[1].split()[0]
        print(f"Created channel ID: {created_channel_id}")
    except IndexError:
        pytest.fail("Could not extract channel ID from response")

    print(f"Response: {response}")
    print("✅ create_channel passed.")


@pytest.mark.asyncio
async def test_create_meeting(client):
    """Create a new online meeting in Microsoft Teams.

    Verifies that the meeting is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    # Set meeting details
    subject = f"Test Meeting {uuid.uuid4()}"
    # Schedule meeting for tomorrow
    start_time = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = (datetime.utcnow() + timedelta(days=1, hours=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    content = "This is a test meeting created by the test_create_meeting tool."

    response = await client.process_query(
        f"""Use the create_meeting tool to create a new meeting
        with subject "{subject}", start time "{start_time}", end time "{end_time}", 
        and content "{content}". If successful, start your response with 
        'Created Teams meeting successfully' and then include the meeting ID.
        Your format for ID will be ID: <meeting_id>"""
    )

    assert (
        "created teams meeting successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_meeting"

    # Extract meeting ID from response
    try:
        global created_meeting_id
        created_meeting_id = response.split("ID: ")[1].split()[0]
        print(f"Created meeting ID: {created_meeting_id}")
    except IndexError:
        pytest.fail("Could not extract meeting ID from response")

    print(f"Response: {response}")
    print("✅ create_meeting passed.")


@pytest.mark.asyncio
async def test_get_channel_messages(client):
    """Get messages from a channel.

    Verifies that channel messages are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id or not created_channel_id:
        pytest.skip(
            "No team ID or channel ID available - created_team_id needs to be set at the top of the file and create_channel test needs to be run first"
        )

    response = await client.process_query(
        f"""Use the get_channel_messages tool to fetch messages from team ID {created_team_id}
        and channel ID {created_channel_id}.
        If successful, start your response with 'Here are the channel messages' and then list them."""
    )

    assert (
        "here are the channel messages" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_channel_messages"

    print(f"Response: {response}")
    print("✅ get_channel_messages passed.")


@pytest.mark.asyncio
async def test_add_team_member(client):
    """Add a user to a team.

    Verifies that the user is added successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id:
        pytest.skip("No team ID available - run create_team test first")

    # Get a user ID to add (this would typically be a test user)

    response = await client.process_query(
        f"""Use the add_team_member tool to add user {test_user_email}
        to team ID {created_team_id} with roles ["member"].
        If successful, start your response with 'Member added successfully'."""
    )

    assert (
        "member added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_team_member"

    print(f"Response: {response}")
    print("✅ add_team_member passed.")


# ===== UPDATE Operations =====


@pytest.mark.asyncio
async def test_send_channel_message(client):
    """Send a message to a channel.

    Verifies that the message is sent successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id or not created_channel_id:
        pytest.skip(
            "No team ID or channel ID available - created_team_id needs to be set at the top of the file and create_channel test needs to be run first"
        )

    message_content = f"Test message {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the send_channel_message tool to send a message to team ID {created_team_id}
        and channel ID {created_channel_id} with content "{message_content}".
        If successful, start your response with 'Message sent successfully'."""
    )

    assert (
        "message sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_channel_message"

    print(f"Response: {response}")
    print("✅ send_channel_message passed.")


@pytest.mark.asyncio
async def test_send_chat_message(client):
    """Send a message in a chat.

    Verifies that the message is sent successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    message_content = f"Test chat message {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the send_chat_message tool to send a message to chat ID {chat_id}
        with content "{message_content}".
        If successful, start your response with 'Message sent successfully'."""
    )

    assert (
        "message sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_chat_message"

    print(f"Response: {response}")
    print("✅ send_chat_message passed.")


@pytest.mark.asyncio
async def test_post_message_reply(client):
    """Post a reply to a message in a Teams channel.

    Verifies that the reply is posted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id or not created_channel_id:
        pytest.skip(
            "No team ID or channel ID available - created_team_id needs to be set at the top of the file and create_channel test needs to be run first"
        )

    # First get a message ID to reply to
    response = await client.process_query(
        f"""Use the get_channel_messages tool to fetch messages from team ID {created_team_id}
        and channel ID {created_channel_id}.
        If successful, start your response with 'Here are the channel messages' and then list them.
        Your format for ID will be ID: <message_id>"""
    )

    # Extract a message ID from the response
    try:
        message_id = response.split("ID: ")[1].split()[0]
    except IndexError:
        pytest.skip("No messages found in channel to reply to")

    reply_content = f"Test reply {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the post_message_reply tool to post a reply to message ID {message_id}
        in team ID {created_team_id} and channel ID {created_channel_id}
        with content "{reply_content}".
        If successful, start your response with 'Reply posted successfully'."""
    )

    assert (
        "reply posted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from post_message_reply"

    print(f"Response: {response}")
    print("✅ post_message_reply passed.")


# ===== DELETE Operations =====


@pytest.mark.asyncio
async def test_remove_team_member(client):
    """Remove a user from a team.

    Verifies that the user is removed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_team_id:
        pytest.skip("No team ID available - run create_team test first")

    response = await client.process_query(
        f"""Use the remove_team_member tool to remove user {test_user_email}
        from team ID {created_team_id}.
        If successful, start your response with 'Member removed successfully'."""
    )

    assert (
        "member removed successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from remove_team_member"

    print(f"Response: {response}")
    print("✅ remove_team_member passed.")


# ===== READ RESOURCE Operations =====


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading a resource from Teams"""
    list_response = await client.list_resources()
    channel_url = list_response.resources[0].uri
    response = await client.read_resource(channel_url)
    assert response, "No response returned from read_resource"
    print(f"Response: {response}")
    print("✅ read_resource passed.")
