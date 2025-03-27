import pytest
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