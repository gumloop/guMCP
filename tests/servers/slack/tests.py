import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing channels from Slack"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Channels found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri})")

    print("✅ Successfully listed channels")


@pytest.mark.asyncio
async def test_read_messages_tool(client):
    """Test reading messages from a channel"""
    # First list channels to get a valid channel
    response = await client.list_resources()
    assert len(response.resources) > 0, "No channels found"

    # Get first channel name
    channel_name = response.resources[0].name

    # Test read_messages tool
    response = await client.process_query(
        f"Use the read_messages tool to read messages from {channel_name}"
    )

    assert response, "No response received from read_messages tool"
    print("Messages read:")
    print(f"\t{response}")

    print("✅ Successfully read messages from channel")


@pytest.mark.asyncio
async def test_send_message_tool(client):
    """Test sending a message to a channel"""
    channel_name = "#tests-slack-mcp"

    # Test send_message tool
    test_message = "This is a test message from the MCP server!"
    response = await client.process_query(
        f"Use the send_message tool to send '{test_message}' to {channel_name}"
    )

    assert "successfully" in response.lower(), f"Failed to send message: {response}"
    print("Message sent:")
    print(f"\t{response}")

    print("✅ Successfully sent message")


@pytest.mark.asyncio
async def test_create_canvas_tool(client):
    """Test creating a canvas message"""
    channel_name = "#tests-slack-mcp"

    # Test create_canvas tool with simple blocks
    test_blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "This is a test canvas message"},
        }
    ]

    response = await client.process_query(
        f"""Use the create_canvas tool with these parameters:
        channel: {channel_name}
        title: Test Canvas
        blocks: {test_blocks}
        """
    )

    assert "successfully" in response.lower(), f"Failed to create canvas: {response}"
    print("Canvas created:")
    print(f"\t{response}")

    print("✅ Successfully created canvas")


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading messages directly from a channel resource"""
    # First list channels to get a valid channel URI
    response = await client.list_resources()
    assert len(response.resources) > 0, "No channels found"

    # Get first channel URI
    channel_uri = response.resources[0].uri

    # Test reading the resource
    response = await client.read_resource(channel_uri)
    assert len(response.contents) > 0, "No content received"
    assert response.contents[0].text, "Empty content received"

    print("Channel content read:")
    print(f"\t{response.contents[0].text}")

    print("✅ Successfully read channel resource")
