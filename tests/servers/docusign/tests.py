import pytest
import uuid
from datetime import datetime

# Global variables to store created IDs
created_template_id = None
created_envelope_id = None
created_user_id = None
current_date = datetime.now().strftime("%Y-%m-%d")


# TEMPLATE MANAGEMENT TESTS


@pytest.mark.asyncio
async def test_create_template(client):
    """Create a new template.

    Verifies that the template is created successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_template_id
    template_name = "Standard NDA Template " + str(uuid.uuid4())
    subject_line = "Please sign this NDA"
    document_name = "TemplateDoc.txt"
    document_content = "This is a dummy NDA with a /sign_here/ placeholder."
    recipient_name = "John Doe"
    recipient_email = "john@example.com"

    response = await client.process_query(
        f"Use the create_template tool to create a template named '{template_name}' with subject line '{subject_line}', "
        f"including a text file named {document_name} with the content '{document_content}', "
        f"assigning the role of Client to {recipient_name} at {recipient_email}, "
        f"and placing a signHere field anchored to '/sign_here/' on page 1 with no offset. "
        "If successful, start your response with 'Template created successfully' and include the template ID."
        "Your template id should be in format Template ID: <id>"
    )

    assert (
        "template created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_template"

    # Extract template id from response
    try:
        created_template_id = response.lower().split("template id: ")[1].split()[0]
        print(f"Created template ID: {created_template_id}")
    except IndexError:
        pytest.fail("Could not extract template ID from response")

    print(f"Response: {response}")
    print("✅ create_template passed.")


@pytest.mark.asyncio
async def test_list_templates(client):
    """List all templates.

    Verifies that templates are listed successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    response = await client.process_query(
        "Use the list_templates tool to list all available templates in the current DocuSign account. "
        "If successful, start your response with 'Here are the available templates' and then list them."
    )

    assert (
        "here are the available templates" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_templates"

    print(f"Response: {response}")
    print("✅ list_templates passed.")


@pytest.mark.asyncio
async def test_get_template(client):
    """Get details of a specific template.

    Verifies that the template details are fetched successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_template_id

    response = await client.process_query(
        f"Use the get_template tool to get detailed information about the template with ID {created_template_id}. "
        "If successful, start your response with 'Here are the template details' and then list them."
    )

    assert (
        "here are the template details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_template"

    print(f"Response: {response}")
    print("✅ get_template passed.")


# ENVELOPE MANAGEMENT TESTS


@pytest.mark.asyncio
async def test_create_envelope(client):
    """Create a new envelope.

    Verifies that the envelope is created successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_envelope_id
    subject_line = "Please sign this agreement " + str(uuid.uuid4())
    document_name = "Contract.txt"
    document_content = "This is a dummy contract with a /sign_here/ placeholder."
    recipient_name = "John Doe"
    recipient_email = "john@example.com"

    response = await client.process_query(
        f"Use the create_envelope tool to create an envelope with subject line '{subject_line}', "
        f"containing a text file named {document_name} with the content '{document_content}', "
        f"assigned to {recipient_name} at {recipient_email} as recipient ID 1 with routing order 1, "
        f"and including a signature field anchored to '/sign_here/' on page 1 with no offset, but do not send the envelope yet. "
        f"If successful, start your response with 'Envelope created successfully' and include the envelope ID."
        "Your envolope id response should be in format Envelope ID: <id>"
    )

    assert (
        "envelope created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_envelope"

    # Extract envelope id from response
    try:
        created_envelope_id = response.lower().split("envelope id: ")[1].split()[0]
        print(f"Created envelope ID: {created_envelope_id}")
    except IndexError:
        pytest.fail("Could not extract envelope ID from response")

    print(f"Response: {response}")
    print("✅ create_envelope passed.")


@pytest.mark.asyncio
async def test_get_envelope(client):
    """Get details of a specific envelope.

    Verifies that the envelope details are fetched successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_envelope_id

    response = await client.process_query(
        f"Use the get_envelope tool to get details of the envelope with ID {created_envelope_id}. "
        "If successful, start your response with 'Here are the envelope details' and then list them."
    )

    assert (
        "here are the envelope details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_envelope"

    print(f"Response: {response}")
    print("✅ get_envelope passed.")


@pytest.mark.asyncio
async def test_send_envelope(client):
    """Send a draft envelope.

    Verifies that the envelope is sent successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_envelope_id

    document_name = "Contract.txt"
    document_content = "This is a dummy contract with a /sign_here/ placeholder."
    recipient_name = "John Doe"
    recipient_email = "john@example.com"
    subject_line = "Please sign this agreement"

    response = await client.process_query(
        f"Use the send_envelope tool to send the envelope with ID {created_envelope_id} which was created in draft mode, "
        f"containing a text file named {document_name} with the content '{document_content}', "
        f"assigned to {recipient_name} at {recipient_email} as recipient ID 1 with routing order 1, "
        f"and including a signature field anchored to '/sign_here/' on page 1 with no offset, "
        f"using the subject line '{subject_line}'. "
        "If successful, start your response with 'Envelope sent successfully'."
    )

    assert (
        "envelope sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_envelope"

    print(f"Response: {response}")
    print("✅ send_envelope passed.")


@pytest.mark.asyncio
async def test_get_envelope_status_bulk(client):
    """Get status of multiple envelopes.

    Verifies that the envelope statuses are fetched successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_envelope_id

    # Using created_envelope_id and two dummy IDs for bulk status check
    dummy_id_1 = "5d1a8a2b-884c-4d65-93b0-111111111111"
    dummy_id_2 = "6e2a4f1b-a9b2-41a3-bbb2-222222222222"

    response = await client.process_query(
        f"Use the get_envelope_status_bulk tool to get the status of envelopes with IDs {created_envelope_id}, {dummy_id_1}, and {dummy_id_2}. "
        "If successful, start your response with 'Here are the envelope statuses' and then list them."
    )

    assert (
        "here are the envelope statuses" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_envelope_status_bulk"

    print(f"Response: {response}")
    print("✅ get_envelope_status_bulk passed.")


# USER MANAGEMENT TESTS


@pytest.mark.asyncio
async def test_create_user(client):
    """Create a new user.

    Verifies that the user is created successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_user_id
    user_name = "John Doe " + str(uuid.uuid4())
    user_email = f"john.doe.{uuid.uuid4()}@example.com"

    response = await client.process_query(
        f"Use the create_user tool to create a new user with the name '{user_name}' and email address '{user_email}'. "
        "If successful, start your response with 'User created successfully' and include the user ID."
        "Your response for ID should be in format User ID: <id>"
    )

    assert (
        "user created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_user"

    # Extract user id from response
    try:
        created_user_id = response.lower().split("user id: ")[1].split()[0]
        print(f"Created user ID: {created_user_id}")
    except IndexError:
        pytest.fail("Could not extract user ID from response")

    print(f"Response: {response}")
    print("✅ create_user passed.")


@pytest.mark.asyncio
async def test_list_users(client):
    """List all users.

    Verifies that users are listed successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    response = await client.process_query(
        "Use the list_users tool to list all users in the current DocuSign account"
        "If successful, start your response with 'Here are the users' and then list them."
    )

    assert (
        "here are the users" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_users"

    print(f"Response: {response}")
    print("✅ list_users passed.")


@pytest.mark.asyncio
async def test_get_user(client):
    """Get details of a specific user.

    Verifies that the user details are fetched successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_user_id

    response = await client.process_query(
        f"Use the get_user tool to retrieve user with ID {created_user_id}. "
        "If successful, start your response with 'Here is the user profile' and then list the details."
    )

    assert (
        "here is the user profile" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_user"

    print(f"Response: {response}")
    print("✅ get_user passed.")
