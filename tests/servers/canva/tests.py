import pytest
import uuid

created_design_id = None
created_thread_id = None
created_reply_id = None
created_folder_id = None


@pytest.mark.asyncio
async def test_get_user_profile(client):
    """Test retrieving the user's profile information.

    Verifies that the user profile information is successfully retrieved.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_user_profile tool to fetch my Canva profile information. "
        "If successful, start your response with 'Here is your Canva profile' and then list the details."
    )

    assert (
        "here is your canva profile" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_user_profile"

    print(f"Response: {response}")
    print("✅ get_user_profile passed.")


@pytest.mark.asyncio
async def test_get_user_details(client):
    """Test retrieving the user's details including user ID and team ID.

    Verifies that the user details are successfully retrieved.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_user_details tool to fetch my user ID and team ID from Canva. "
        "If successful, start your response with 'Here are your Canva user details' and then list them."
    )

    assert (
        "here are your canva user details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_user_details"

    print(f"Response: {response}")
    print("✅ get_user_details passed.")


@pytest.mark.asyncio
async def test_create_design(client):
    """Test creating a new design in Canva.

    Verifies that a new design is successfully created.
    Stores the created design ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_design_id
    title = "Test Design " + str(uuid.uuid4())
    design_type = "presentation"

    response = await client.process_query(
        f"""Use the create_design tool to create a new Canva design with
        title "{title}" and type {design_type}. If successful, start your response with
        'Created Canva design successfully' and then list the design ID in format 'ID: <design_id>'."""
    )

    assert (
        "created canva design successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_design"

    # Extract design ID from response
    try:
        created_design_id = response.split("ID: ")[1].split()[0]
        print(f"Created design ID: {created_design_id}")
    except IndexError:
        pytest.fail("Could not extract design ID from response")

    print(f"Response: {response}")
    print("✅ create_design passed.")


@pytest.mark.asyncio
async def test_get_design(client):
    """Test retrieving details for a specific design.

    Verifies that design details are successfully retrieved.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_design_id:
        pytest.skip("No design ID available - run create_design test first")

    design_id = created_design_id

    response = await client.process_query(
        f"Use the get_design tool to fetch details for design ID {design_id}. "
        "If successful, start your response with 'Here are the design details' and then list them."
    )

    assert (
        "here are the design details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_design"

    print(f"Response: {response}")
    print("✅ get_design passed.")


@pytest.mark.asyncio
async def test_list_designs(client):
    """Test listing user's designs with optional parameters.

    Verifies that designs are successfully retrieved with limit and sorting.

    Args:
        client: The test client fixture for the MCP server.
    """
    limit = 2
    sort_by = "modified_descending"

    response = await client.process_query(
        f"Use the list_designs tool to fetch my latest {limit} designs sorted by {sort_by}. "
        "If successful, start your response with 'Here are your Canva designs' and then list them."
    )

    assert (
        "here are your canva designs" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_designs"

    print(f"Response: {response}")
    print("✅ list_designs passed.")


@pytest.mark.asyncio
async def test_create_thread(client):
    """Test creating a new comment thread on a design.

    Verifies that a new comment thread is successfully created.
    Stores the created thread ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_thread_id
    design_id = created_design_id
    message = (
        "This is a test comment thread created by the test_create_thread tool in guMCP."
    )

    response = await client.process_query(
        f"""Use the create_thread tool to create a new comment thread on design ID {design_id}
        with message_plaintext "{message}". If successful, start your response with
        'Created comment thread successfully' and then list the thread ID in format 'ID: <thread_id>'."""
    )

    assert (
        "created comment thread successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_thread"

    # Extract thread ID from response
    try:
        created_thread_id = response.split("ID: ")[1].split()[0]
        print(f"Created thread ID: {created_thread_id}")
    except IndexError:
        pytest.fail("Could not extract thread ID from response")

    print(f"Response: {response}")
    print("✅ create_thread passed.")


@pytest.mark.asyncio
async def test_get_thread(client):
    """Test retrieving a specific comment thread.

    Verifies that thread details are successfully retrieved.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_thread_id:
        pytest.skip("No thread ID available - run create_thread test first")

    design_id = created_design_id
    thread_id = created_thread_id

    response = await client.process_query(
        f"Use the get_thread tool to fetch details for thread ID {thread_id} on design ID {design_id}. "
        "If successful, start your response with 'Here are the thread details' and then list them."
    )

    assert (
        "here are the thread details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_thread"

    print(f"Response: {response}")
    print("✅ get_thread passed.")


@pytest.mark.asyncio
async def test_create_reply(client):
    """Test creating a reply to a comment thread.

    Verifies that a new reply is successfully created.
    Stores the created reply ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_reply_id
    if not created_thread_id:
        pytest.skip("No thread ID available - run create_thread test first")

    design_id = created_design_id
    thread_id = created_thread_id
    message = "This is a test reply created by the test_create_reply tool in guMCP."

    response = await client.process_query(
        f"""Use the create_reply tool to create a new reply on thread ID {thread_id} of design ID {design_id}
        with message_plaintext "{message}". If successful, start your response with
        'Created reply successfully' and then list the reply ID in format 'ID: <reply_id>'."""
    )

    assert (
        "created reply successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_reply"

    # Extract reply ID from response
    try:
        created_reply_id = response.split("ID: ")[1].split()[0]
        print(f"Created reply ID: {created_reply_id}")
    except IndexError:
        pytest.fail("Could not extract reply ID from response")

    print(f"Response: {response}")
    print("✅ create_reply passed.")


@pytest.mark.asyncio
async def test_get_reply(client):
    """Test retrieving a specific reply.

    Verifies that reply details are successfully retrieved.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_reply_id or not created_thread_id:
        pytest.skip("No reply or thread ID available - run create_reply test first")

    design_id = created_design_id
    thread_id = created_thread_id
    reply_id = created_reply_id

    response = await client.process_query(
        f"""Use the get_reply tool to fetch details for reply ID {reply_id} on thread ID {thread_id}
        of design ID {design_id}. If successful, start your response with
        'Here are the reply details' and then list them."""
    )

    assert (
        "here are the reply details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_reply"

    print(f"Response: {response}")
    print("✅ get_reply passed.")


@pytest.mark.asyncio
async def test_list_replies(client):
    """Test listing replies to a comment thread.

    Verifies that replies are successfully retrieved.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_thread_id:
        pytest.skip("No thread ID available - run create_thread test first")

    design_id = created_design_id
    thread_id = created_thread_id
    limit = 5

    response = await client.process_query(
        f"Use the list_replies tool to fetch up to {limit} replies for thread ID {thread_id} on design ID {design_id}. "
        "If successful, start your response with 'Here are the thread replies' and then list them."
    )

    assert (
        "here are the thread replies" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_replies"

    print(f"Response: {response}")
    print("✅ list_replies passed.")


@pytest.mark.asyncio
async def test_create_folder(client):
    """Test creating a new folder in the user's Projects.

    Verifies that a new folder is successfully created.
    Stores the created folder ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_folder_id
    parent_folder_id = "root"
    folder_name = "Test Folder " + str(uuid.uuid4())

    response = await client.process_query(
        f"""Use the create_folder tool to create a new folder with name "{folder_name}"
        under parent folder ID {parent_folder_id}. If successful, start your response with
        'Created folder successfully' and then list the folder ID in format 'ID: <folder_id>'."""
    )

    assert (
        "created folder successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_folder"

    try:
        created_folder_id = response.split("ID: ")[1].split()[0]
        print(f"Created folder ID: {created_folder_id}")
    except IndexError:
        pytest.fail("Could not extract folder ID from response")

    print(f"Response: {response}")
    print("✅ create_folder passed.")


@pytest.mark.asyncio
async def test_get_folder(client):
    """Test retrieving details for a specific folder.

    Verifies that folder details are successfully retrieved.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_folder_id:
        pytest.skip("No folder ID available - run create_folder test first")

    folder_id = created_folder_id

    response = await client.process_query(
        f"Use the get_folder tool to fetch details for folder ID {folder_id}. "
        "If successful, start your response with 'Here are the folder details' and then list them."
    )

    assert (
        "here are the folder details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_folder"

    print(f"Response: {response}")
    print("✅ get_folder passed.")


@pytest.mark.asyncio
async def test_update_folder(client):
    """Test updating a folder's metadata.

    Verifies that the folder is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_folder_id:
        pytest.skip("No folder ID available - run create_folder test first")

    folder_id = created_folder_id
    new_name = "Updated Test Folder " + str(uuid.uuid4())

    response = await client.process_query(
        f"""Use the update_folder tool to update folder ID {folder_id} with new name "{new_name}".
        If successful, start your response with 'Updated folder successfully' and then list the folder ID in format 'ID: <folder_id>'."""
    )

    assert (
        "updated folder successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_folder"

    try:
        updated_folder_id = response.split("ID: ")[1].split()[0]
        assert (
            updated_folder_id == created_folder_id
        ), "Updated folder ID doesn't match created folder ID"
    except IndexError:
        pytest.fail("Could not extract folder ID from response")

    print(f"Response: {response}")
    print("✅ update_folder passed.")


@pytest.mark.asyncio
async def test_delete_folder(client):
    """Test deleting a folder.

    Verifies that the folder is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_folder_id:
        pytest.skip("No folder ID available - run create_folder test first")

    folder_id = created_folder_id

    response = await client.process_query(
        f"""Use the delete_folder tool to delete folder ID {folder_id}.
        If successful, start your response with 'Deleted folder successfully' and then list the folder ID in format 'ID: <folder_id>'."""
    )

    assert (
        "deleted folder successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_folder"

    try:
        deleted_folder_id = response.split("ID: ")[1].split()[0]
        assert (
            deleted_folder_id == created_folder_id
        ), "Deleted folder ID doesn't match created folder ID"
    except IndexError:
        pytest.fail("Could not extract folder ID from response")

    print(f"Response: {response}")
    print("✅ delete_folder passed.")
