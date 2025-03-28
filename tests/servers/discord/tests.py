import pytest
<<<<<<< HEAD


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing channels from Discord server"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources) >= 0
    ), f"Invalid list resources response: {response}"

    print("Discord channels found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed Discord channels")


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading messages from a Discord channel"""
    # First list channels to get a valid channel URI
    response = await client.list_resources()
    
    assert (
        response and hasattr(response, "resources")
    ), f"Invalid list resources response: {response}"
    
    if len(response.resources) == 0:
        pytest.skip("No Discord channels found to test reading messages")
    
    channel_uri = response.resources[0].uri
    response = await client.read_resource(channel_uri)
    
    assert (
        response and hasattr(response, "contents")
    ), f"Invalid read resource response: {response}"
    
    # Don't require messages to be present, just check if the response is valid
    print(f"Messages from channel:")
    if len(response.contents) > 0:
        print(f"\t{response.contents[0].text}")
    else:
        print("\tNo messages found in channel")
    
    print("✅ Successfully read Discord channel messages")


@pytest.mark.skip(reason="Skipping test that performs write operation: sending a message")
@pytest.mark.asyncio
async def test_send_message_tool(client):
    """Test sending a message to a Discord channel"""
    # First list channels to get a valid channel ID
    response = await client.list_resources()
    
    assert (
        response and hasattr(response, "resources")
    ), f"Invalid list resources response: {response}"
    
    if len(response.resources) == 0:
        pytest.skip("No Discord channels found to test sending messages")
    
    channel_uri = response.resources[0].uri
    channel_uri_str = str(channel_uri)
    parts = channel_uri_str.replace("discord:///", "").split("/", 1)
    guild_id = parts[0]
    channel_id = parts[1] if len(parts) > 1 else None
    
    if not channel_id:
        pytest.skip("Could not parse channel_id from URI")
    
    # Send a test message using process_query instead of call_tool
    response = await client.process_query(
        f"Use the send_message tool to send a message to channel {channel_id} with the content 'This is a test message from the Discord MCP tests'"
    )
    
    assert response, f"Invalid process_query response: {response}"
    
    print(f"Message response: {response}")
    print("✅ Successfully sent message to Discord channel")
    
   
    if "Message ID:" in response:
        message_id = response.split("Message ID:")[1].strip().split()[0]
        return channel_id, message_id
    else:
        return channel_id, None


@pytest.mark.skip(reason="Skipping test that requires call_tool functionality")
@pytest.mark.asyncio
async def test_read_messages_tool(client):
    """Test reading messages from a Discord channel using the tool"""
    # First list channels to get a valid channel ID
    response = await client.list_resources()
    
    assert (
        response and hasattr(response, "resources")
    ), f"Invalid list resources response: {response}"
    
    
    if len(response.resources) == 0:
        pytest.skip("No Discord channels found to test reading messages")
    
    channel_uri = response.resources[0].uri
    channel_uri_str = str(channel_uri)
    parts = channel_uri_str.replace("discord:///", "").split("/", 1)
    guild_id = parts[0]
    channel_id = parts[1] if len(parts) > 1 else None
    
    if not channel_id:
        pytest.skip("Could not parse channel_id from URI")
    

    response = await client.process_query(
        f"Use the read_messages tool to read messages from channel {channel_id}, limit to 5 messages."
    )
    
   
    assert response, f"Invalid process_query response: {response}"
    
    print(f"Read messages response: {response}")
    print("✅ Successfully read messages from Discord channel")


@pytest.mark.skip(reason="Skipping test that performs write operations: editing and deleting a message")
@pytest.mark.asyncio
async def test_edit_and_delete_message(client):
    """Test editing and deleting a message"""
    # Send a message first and get its ID
    try:
        channel_id, message_id = await test_send_message_tool(client)
        if message_id is None:
            pytest.skip("Could not get message ID from send message response")
    except Exception as e:
        pytest.skip(f"Unable to send message for edit/delete test: {e}")
    
    # Edit the message
    edit_response = await client.process_query(
        f"Use the edit_message tool to edit message {message_id} in channel {channel_id} with the content 'This message has been edited by the test'"
    )
    
    assert edit_response, f"Invalid process_query response: {edit_response}"
    
    print(f"Edit message response: {edit_response}")
    print("✅ Successfully edited Discord message")
    
    # Delete the message
    delete_response = await client.process_query(
        f"Use the delete_message tool to delete message {message_id} from channel {channel_id}"
    )
    
    assert delete_response, f"Invalid process_query response: {delete_response}"
    
    print(f"Delete message response: {delete_response}")
    print("✅ Successfully deleted Discord message")


@pytest.mark.skip(reason="Skipping test that performs write operation: adding a reaction")
@pytest.mark.asyncio
async def test_add_reaction(client):
    """Test adding a reaction to a message"""

    try:
        channel_id, message_id = await test_send_message_tool(client)
        if message_id is None:
            pytest.skip("Could not get message ID from send message response")
    except Exception as e:
        pytest.skip(f"Unable to send message for reaction test: {e}")
    
 
    reaction_response = await client.process_query(
        f"Use the add_reaction tool to add the reaction '👍' to message {message_id} in channel {channel_id}"
    )
    
    assert reaction_response, f"Invalid process_query response: {reaction_response}"
    
    print(f"Add reaction response: {reaction_response}")
    print("✅ Successfully added reaction to Discord message")
    
    await client.process_query(
        f"Use the delete_message tool to delete message {message_id} from channel {channel_id}"
    )


@pytest.mark.skip(reason="Skipping test that performs write operation: sending an embed message")
@pytest.mark.asyncio
async def test_send_embed(client):
    """Test sending an embed message"""
    response = await client.list_resources()
    
    assert (
        response and hasattr(response, "resources")
    ), f"Invalid list resources response: {response}"
    
    
    if len(response.resources) == 0:
        pytest.skip("No Discord channels found to test sending embed")
    
    channel_uri = response.resources[0].uri
    channel_uri_str = str(channel_uri)
    parts = channel_uri_str.replace("discord:///", "").split("/", 1)
    guild_id = parts[0]
    channel_id = parts[1] if len(parts) > 1 else None
    
    if not channel_id:
        pytest.skip("Could not parse channel_id from URI")
    
    # Send an embed message
    embed_response = await client.process_query(
        f"Use the send_embed tool to send an embed to channel {channel_id} with title 'Test Embed from MCP Tests', " +
        f"description 'This is a test embed message from the Discord MCP tests', color '#00FF00', " +
        f"footer 'Test footer', and fields: 'Field 1' with value 'Value 1' (inline), and 'Field 2' with value 'Value 2' (inline)"
    )
    
    assert embed_response, f"Invalid process_query response: {embed_response}"
    
    print(f"Send embed response: {embed_response}")
    print("✅ Successfully sent embed to Discord channel")
    
    message_id = None
    if "Message ID:" in embed_response:
        message_id = embed_response.split("Message ID:")[1].strip().split()[0]
    
    if message_id:
        await client.process_query(
            f"Use the delete_message tool to delete message {message_id} from channel {channel_id}"
        )


@pytest.mark.skip(reason="Skipping test that might require write operations: user info test")
@pytest.mark.asyncio
async def test_get_user_info(client):
    """Test getting user information"""
    response = await client.list_resources()
    
    if not response or not hasattr(response, "resources") or len(response.resources) == 0:
        pytest.skip("No Discord channels found to continue test")
    
   
    try:
        channel_id, message_id = await test_send_message_tool(client)
        if message_id is None:
            pytest.skip("Could not get message ID from send message response")
    except Exception as e:
        pytest.skip(f"Unable to send message to identify bot user: {e}")
        
    messages_response = await client.process_query(
        f"Use the read_messages tool to read messages from channel {channel_id}, limit to 1"
    )
    

    if message_id:
        await client.process_query(
            f"Use the delete_message tool to delete message {message_id} from channel {channel_id}"
        )
    
    try:
        message_text = messages_response
        if "Message ID:" in message_text:
            lines = message_text.split("\n")
            for line in lines:
                if "Message ID:" in line:
                    user_id = line.split("Message ID:")[1].strip().split()[0]
 
                    break
        else:
            pytest.skip("Could not find a user ID to test with")
    except Exception:
        pytest.skip("Could not parse message response to find user ID")
    

    try:
        user_info_response = await client.process_query(
            f"Use the get_user_info tool to get information about user {user_id}"
        )
        
        print(f"Get user info response: {user_info_response}")
        print("✅ Attempted to get user info")
    except Exception as e:
        print(f"Note: get_user_info test failed as expected without valid user ID: {e}")
        pass 


@pytest.mark.skip(reason="Skipping test that requires call_tool functionality")
@pytest.mark.asyncio
async def test_list_members(client):
    """Test listing members from a guild"""
    # List channels to get guild info
    response = await client.list_resources()
    
    if not response or not hasattr(response, "resources") or len(response.resources) == 0:
        pytest.skip("No Discord channels found to continue test")
    
    channel_uri = response.resources[0].uri
    channel_uri_str = str(channel_uri)
    parts = channel_uri_str.replace("discord:///", "").split("/", 1)
    guild_id = parts[0]
    
    members_response = await client.process_query(
        f"Use the list_members tool to list members in guild {guild_id}, limit to 5 members."
    )
    
    assert members_response, f"Invalid process_query response: {members_response}"
    
    print(f"List members response: {members_response}")
    print("✅ Successfully listed Discord members")


@pytest.mark.skip(reason="Skipping test that might perform write operations depending on query")
@pytest.mark.asyncio
async def test_process_query(client):
    """Test search functionality through process_query"""
    response = await client.process_query(
        "Use the read_messages tool to read messages from any channel you have access to."
    )

    assert response, f"Invalid process_query response: {response}"
    
    print("Process query response:")
    print(f"\t{response}")
    
    print("✅ Process query functionality working")
=======
import json
import asyncio


async def test_list_tools(client):
    """Test that the Discord server returns a list of available tools"""
    tools = await client.list_tools()
    
    # Verify that we got a list of tools
    assert isinstance(tools, list)
    assert len(tools) > 0
    
    # Check for some expected tools
    tool_names = {tool['name'] for tool in tools}
    expected_tools = {
        'send_message', 
        'read_messages', 
        'add_reaction',
        'edit_message',
        'delete_message',
        'send_embed'
    }
    
    # Verify that at least the core expected tools are present
    assert expected_tools.issubset(tool_names)
    
    # Basic structure verification
    for tool in tools:
        assert 'name' in tool
        assert 'description' in tool
        assert 'inputSchema' in tool
        assert isinstance(tool['inputSchema'], dict)


async def test_list_resources(client):
    """Test listing Discord channels as resources"""
    # This test might be skipped in CI environments where no Discord token is available
    try:
        resources_response = await client.list_resources()
        
        # Basic structure check
        assert 'resources' in resources_response
        
        # The test environment might not have access to Discord resources,
        # so we just check the structure
        for resource in resources_response['resources']:
            assert 'uri' in resource
            assert 'name' in resource
            assert 'mime_type' in resource
            
            # Check that URIs have the expected format
            assert resource['uri'].startswith('discord:///')
            
    except Exception as e:
        # If we're in a test environment without Discord credentials,
        # this might fail, so we'll skip rather than fail
        if "Credentials not found" in str(e):
            pytest.skip("Discord credentials not available")
        else:
            raise


# Tools tests
async def test_send_and_read_message(client):
    """Test sending and reading a message (if credentials are available)"""
    try:
        # First, list resources to find a channel
        resources_response = await client.list_resources()
        
        if not resources_response['resources']:
            pytest.skip("No Discord channels available for testing")
            
        # Get the first channel
        channel = resources_response['resources'][0]
        channel_id = channel['uri'].split('/')[-1]
        
        # Send a test message
        test_message = f"Test message from Discord MCP test {asyncio.get_event_loop().time()}"
        send_result = await client.call_tool('send_message', {
            'channel_id': channel_id,
            'content': test_message
        })
        
        assert isinstance(send_result, list)
        assert len(send_result) > 0
        
        # Extract message ID from response if available
        message_id = None
        message_text = send_result[0].get('text', '')
        if 'Message ID:' in message_text:
            message_id = message_text.split('Message ID:')[1].strip().split()[0]
        
        # Read messages back
        read_result = await client.call_tool('read_messages', {
            'channel_id': channel_id,
            'limit': 5
        })
        
        assert isinstance(read_result, list)
        assert len(read_result) > 0
        
        # Verify our test message is in the results
        found_message = False
        for content in read_result:
            if 'text' in content and test_message in content['text']:
                found_message = True
                break
                
        assert found_message, "Test message not found in channel messages"
        
        # Clean up - delete the message if we have its ID
        if message_id:
            await client.call_tool('delete_message', {
                'channel_id': channel_id,
                'message_id': message_id
            })
            
    except Exception as e:
        if "Credentials not found" in str(e):
            pytest.skip("Discord credentials not available")
        else:
            raise 
>>>>>>> 355f7aa79b9f45925ead2430a5e7b34656b1afd7
