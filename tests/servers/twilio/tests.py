import pytest
import uuid

# Global variables to store created resource IDs
created_message_sid = None
created_call_sid = None
created_conversation_sid = None
created_verify_service_sid = None
created_conversation_service_sid = None
created_video_room_sid = None

# Test phone numbers
# You can only send messages to verified numbers unless your account is upgraded
to_number = ""  # TODO: Add your phone number
from_number = ""  # TODO: Add phone number from Twilio

# Test verification code (for verification tests)
# The test case for verification code will fail if you run all tests at once as the verification code will a new one each time
# So run the other tests first to get the service SID, then run the verification code test separately
test_verification_code = (
    ""  # TODO: Add verification code that was sent to your phone number
)


@pytest.mark.asyncio
async def test_send_message(client):
    """Send a new SMS message."""
    global created_message_sid

    body = "Test message from guMCP Twilio tests " + str(uuid.uuid4())

    response = await client.process_query(
        f"Use the send_message tool to send a message from {from_number} to {to_number} "
        f"with body '{body}'. If successful, start your response with 'Message sent successfully' "
        "and then list the message SID in format 'SID: <message_sid>'."
    )

    assert (
        "message sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_message"

    try:
        created_message_sid = response.split("SID: ")[1].split()[0]
        print(f"Created message SID: {created_message_sid}")
    except IndexError:
        pytest.fail("Could not extract message SID from response")

    print(f"Response: {response}")
    print("✅ send_message passed.")


@pytest.mark.asyncio
async def test_list_messages(client):
    """List recent messages."""
    response = await client.process_query(
        "Use the list_messages tool to fetch recent messages. If successful, "
        "start your response with 'Here are the messages' and then list them."
    )

    assert (
        "here are the messages" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_messages"

    print(f"Response: {response}")
    print("✅ list_messages passed.")


@pytest.mark.asyncio
async def test_fetch_message(client):
    """Fetch a specific message by SID."""
    if not created_message_sid:
        pytest.skip("No message SID available - run send_message test first")

    response = await client.process_query(
        f"Use the fetch_message tool to fetch message with SID {created_message_sid}. "
        "If successful, start your response with 'Here are the message details' and then list them."
    )

    assert (
        "here are the message details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from fetch_message"

    print(f"Response: {response}")
    print("✅ fetch_message passed.")


@pytest.mark.asyncio
async def test_delete_message(client):
    """Delete a specific message by SID."""
    if not created_message_sid:
        pytest.skip("No message SID available - run send_message test first")

    response = await client.process_query(
        f"Use the delete_message tool to delete message with SID {created_message_sid}. "
        "If successful, start your response with 'Message deleted successfully'."
    )

    assert (
        "message deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_message"

    print(f"Response: {response}")
    print("✅ delete_message passed.")


@pytest.mark.asyncio
async def test_make_call(client):
    """Make a new voice call."""
    global created_call_sid

    text = "This is a test call from guMCP Twilio tests"

    response = await client.process_query(
        f"Use the make_call tool to make a call from {from_number} to {to_number} "
        f"with text '{text}'. If successful, start your response with 'Call initiated successfully' "
        "and then list the call SID in format 'SID: <call_sid>'."
    )

    assert (
        "call initiated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from make_call"

    try:
        created_call_sid = response.split("SID: ")[1].split()[0]
        print(f"Created call SID: {created_call_sid}")
    except IndexError:
        pytest.fail("Could not extract call SID from response")

    print(f"Response: {response}")
    print("✅ make_call passed.")


@pytest.mark.asyncio
async def test_list_calls(client):
    """List recent calls."""
    response = await client.process_query(
        "Use the list_calls tool to fetch recent calls. If successful, "
        "start your response with 'Here are the calls' and then list them."
    )

    assert (
        "here are the calls" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_calls"

    print(f"Response: {response}")
    print("✅ list_calls passed.")


@pytest.mark.asyncio
async def test_fetch_call(client):
    """Fetch a specific call by SID."""
    if not created_call_sid:
        pytest.skip("No call SID available - run make_call test first")

    response = await client.process_query(
        f"Use the fetch_call tool to fetch call with SID {created_call_sid}. "
        "If successful, start your response with 'Here are the call details' and then list them."
    )

    assert (
        "here are the call details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from fetch_call"

    print(f"Response: {response}")
    print("✅ fetch_call passed.")


@pytest.mark.asyncio
async def test_list_verify_services(client):
    """List all Twilio Verify services."""
    response = await client.process_query(
        "Use the list_verify_services tool to fetch all verify services. If successful, "
        "start your response with 'Here are the verify services' and then list them."
    )

    assert (
        "here are the verify services" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_verify_services"

    print(f"Response: {response}")
    print("✅ list_verify_services passed.")


@pytest.mark.asyncio
async def test_create_verify_service(client):
    """Create a new Twilio Verify service."""
    global created_verify_service_sid

    friendly_name = f"Test Verify Service {str(uuid.uuid4())[:4]}"

    response = await client.process_query(
        f"Use the create_verify_service tool to create a new verify service with friendly name '{friendly_name}'. "
        "If successful, start your response with 'Verify service created successfully' and then list the service SID in format 'SID: <service_sid>'."
    )

    assert (
        "verify service created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_verify_service"

    try:
        created_verify_service_sid = response.split("SID: ")[1].split()[0]
        print(f"Created verify service SID: {created_verify_service_sid}")
    except IndexError:
        pytest.fail("Could not extract verify service SID from response")

    print(f"Response: {response}")
    print("✅ create_verify_service passed.")


@pytest.mark.asyncio
async def test_start_verification(client):
    """Start a verification process."""
    if not created_verify_service_sid:
        pytest.skip(
            "No verify service SID available - run create_verify_service test first"
        )

    response = await client.process_query(
        f"Use the start_verification tool to start verification for phone number {to_number} "
        f"using service SID {created_verify_service_sid} and channel 'sms'. "
        "If successful, start your response with 'Verification started successfully'."
    )

    assert (
        "verification started successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from start_verification"

    print(f"Response: {response}")
    print("✅ start_verification passed.")


@pytest.mark.asyncio
async def test_check_verification(client):
    """Check a verification code."""
    if not created_verify_service_sid:
        pytest.skip(
            "No verify service SID available - run create_verify_service test first"
        )

    response = await client.process_query(
        f"Use the check_verification tool to check verification code '{test_verification_code}' "
        f"for phone number {to_number} using service SID {created_verify_service_sid}. "
        "If successful, start your response with 'Verification check completed'."
    )

    assert (
        "verification check completed" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from check_verification"

    print(f"Response: {response}")
    print("✅ check_verification passed.")


@pytest.mark.asyncio
async def test_lookup_phone_number(client):
    """Lookup phone number information."""
    response = await client.process_query(
        f"Use the lookup_phone_number tool to lookup information for phone number {to_number}. "
        "If successful, start your response with 'Phone number lookup completed'."
    )

    assert (
        "phone number lookup completed" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from lookup_phone_number"

    print(f"Response: {response}")
    print("✅ lookup_phone_number passed.")


@pytest.mark.asyncio
async def test_list_conversation_services(client):
    """List all Twilio Conversation services."""
    response = await client.process_query(
        "Use the list_conversation_services tool to fetch all conversation services. "
        "If successful, start your response with 'Here are the conversation services'."
    )

    assert (
        "here are the conversation services" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_conversation_services"

    print(f"Response: {response}")
    print("✅ list_conversation_services passed.")


@pytest.mark.asyncio
async def test_create_conversation_service(client):
    """Create a new Twilio Conversation service."""
    global created_conversation_service_sid

    friendly_name = f"Test Conversation Service {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_conversation_service tool to create a new conversation service with friendly name '{friendly_name}'. "
        "If successful, start your response with 'Conversation service created successfully' and then list the service SID in format 'SID: <service_sid>'."
    )

    assert (
        "conversation service created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_conversation_service"

    try:
        created_conversation_service_sid = response.split("SID: ")[1].split()[0]
        print(f"Created conversation service SID: {created_conversation_service_sid}")
    except IndexError:
        pytest.fail("Could not extract conversation service SID from response")

    print(f"Response: {response}")
    print("✅ create_conversation_service passed.")


@pytest.mark.asyncio
async def test_list_conversations(client):
    """List conversations in a service."""
    if not created_conversation_service_sid:
        pytest.skip(
            "No conversation service SID available - run create_conversation_service test first"
        )

    response = await client.process_query(
        f"Use the list_conversations tool to fetch conversations for service SID {created_conversation_service_sid}. "
        "If successful, start your response with 'Here are the conversations'."
    )

    assert (
        "here are the conversations" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_conversations"

    print(f"Response: {response}")
    print("✅ list_conversations passed.")


@pytest.mark.asyncio
async def test_create_conversation(client):
    """Create a new conversation."""
    global created_conversation_sid

    if not created_conversation_service_sid:
        pytest.skip(
            "No conversation service SID available - run create_conversation_service test first"
        )

    friendly_name = f"Test Conversation {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_conversation tool to create a new conversation in service SID {created_conversation_service_sid} "
        f"with friendly name '{friendly_name}'. If successful, start your response with 'Conversation created successfully' and then list the conversation SID in format 'SID: <conversation_sid>'."
    )

    assert (
        "conversation created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_conversation"

    try:
        created_conversation_sid = response.split("SID: ")[1].split()[0]
        print(f"Created conversation SID: {created_conversation_sid}")
    except IndexError:
        pytest.fail("Could not extract conversation SID from response")

    print(f"Response: {response}")
    print("✅ create_conversation passed.")


@pytest.mark.asyncio
async def test_add_conversation_participant(client):
    """Add a participant to the conversation."""
    global test_participant_identity
    test_participant_identity = f"user_{uuid.uuid4()}"  # any unique string

    if not created_conversation_sid:
        pytest.skip("No conversation SID - run create_conversation test first")

    response = await client.process_query(
        f"Use the add_conversation_participant tool to add a participant with identity '{test_participant_identity}' "
        f"to conversation SID {created_conversation_sid} in service SID {created_conversation_service_sid}. "
        "If successful, start your response with 'Participant added successfully'."
    )

    assert (
        "participant added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print("✅ add_conversation_participant passed.")


@pytest.mark.asyncio
async def test_send_conversation_message(client):
    """Send a message in a conversation."""
    if not created_conversation_sid or not created_conversation_service_sid:
        pytest.skip(
            "No conversation SID or service SID available - run create_conversation test first"
        )

    body = f"Test message from guMCP Twilio tests {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the send_conversation_message tool to send a message in conversation SID {created_conversation_sid} "
        f"with body '{body}' in service SID {created_conversation_service_sid}. "
        "If successful, start your response with 'Message sent successfully'."
    )

    assert (
        "message sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_conversation_message"

    print(f"Response: {response}")
    print("✅ send_conversation_message passed.")


@pytest.mark.asyncio
async def test_list_video_rooms(client):
    """List all Twilio Video rooms."""
    response = await client.process_query(
        "Use the list_video_rooms tool to fetch all video rooms. "
        "If successful, start your response with 'Here are the video rooms'."
    )

    assert (
        "here are the video rooms" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_video_rooms"

    print(f"Response: {response}")
    print("✅ list_video_rooms passed.")


@pytest.mark.asyncio
async def test_create_video_room(client):
    """Create a new Twilio Video room."""
    global created_video_room_sid

    unique_name = f"test-room-{uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_video_room tool to create a new video room with unique name '{unique_name}'. "
        "If successful, start your response with 'Video room created successfully' and then list the room SID in format 'SID: <room_sid>'."
    )

    assert (
        "video room created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_video_room"

    try:
        created_video_room_sid = response.split("SID: ")[1].split()[0]
        print(f"Created video room SID: {created_video_room_sid}")
    except IndexError:
        pytest.fail("Could not extract video room SID from response")

    print(f"Response: {response}")
    print("✅ create_video_room passed.")


@pytest.mark.asyncio
async def test_fetch_video_room(client):
    """Fetch a specific video room by SID."""
    if not created_video_room_sid:
        pytest.skip("No video room SID available - run create_video_room test first")

    response = await client.process_query(
        f"Use the fetch_video_room tool to fetch video room with SID {created_video_room_sid}. "
        "If successful, start your response with 'Here are the video room details'."
    )

    assert (
        "here are the video room details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from fetch_video_room"

    print(f"Response: {response}")
    print("✅ fetch_video_room passed.")


@pytest.mark.asyncio
async def test_complete_video_room(client):
    """Complete (end) a video room."""
    if not created_video_room_sid:
        pytest.skip("No video room SID available - run create_video_room test first")

    response = await client.process_query(
        f"Use the complete_video_room tool to complete video room with SID {created_video_room_sid}. "
        "If successful, start your response with 'Video room completed successfully'."
    )

    assert (
        "video room completed successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from complete_video_room"

    print(f"Response: {response}")
    print("✅ complete_video_room passed.")
