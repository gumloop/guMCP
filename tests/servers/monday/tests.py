import pytest
import uuid

# Global variables to store created IDs
created_board_id = None
created_item_id = None
created_group_id = None
created_column_id = None
created_subitem_id = None


workspace_id = ""  # Replace with actual workspace ID


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing resources from Monday.com"""
    response = await client.list_resources()
    print(f"Response: {response}")
    assert response, "No response returned from list_resources"

    for i, resource in enumerate(response.resources):
        print(f"  - {i}: {resource.name} ({resource.uri}) {resource.description}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading a resource from Monday.com"""
    list_response = await client.list_resources()

    board_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("monday://board/")
    ]

    if len(board_resource_uri) > 0:
        board_resource_uri = board_resource_uri[0]
        response = await client.read_resource(board_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for board passed.")

    workspace_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("monday://workspace/")
    ]

    if len(workspace_resource_uri) > 0:
        workspace_resource_uri = workspace_resource_uri[0]
        response = await client.read_resource(workspace_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for workspace passed.")

    item_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("monday://item/")
    ]

    if len(item_resource_uri) > 0:
        item_resource_uri = item_resource_uri[0]
        response = await client.read_resource(item_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for item passed.")

    group_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("monday://board/")
        and "group" in str(resource.uri)
    ]

    if len(group_resource_uri) > 0:
        group_resource_uri = group_resource_uri[0]
        response = await client.read_resource(group_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for group passed.")


# CRUD Test Order:
# 1. Create operations
# 2. Read operations
# 3. Update operations
# 4. Delete operations


# ===== CREATE OPERATIONS =====
@pytest.mark.asyncio
async def test_create_board(client):
    """Create a new board within a workspace."""
    global created_board_id
    board_name = f"Test Board {uuid.uuid4()}"
    board_kind = "public"
    description = "Test board created by guMCP"

    response = await client.process_query(
        f"Use the create_board tool to create a new board with name {board_name}, "
        f"kind {board_kind}, and description {description} in workspace {workspace_id}. "
        "If successful, start your response with 'Created board successfully' and then list the board ID in format 'ID: <board_id>'."
    )

    assert (
        "created board successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_board"

    try:
        created_board_id = response.split("ID: ")[1].split()[0]
        print(f"Created board ID: {created_board_id}")
    except IndexError:
        pytest.fail("Could not extract board ID from response")

    print(f"Response: {response}")
    print("✅ create_board passed.")


@pytest.mark.asyncio
async def test_create_group(client):
    """Create a new group in a board."""
    global created_group_id
    if not created_board_id:
        pytest.skip("No board ID available - run create_board test first")

    group_name = f"Test Group {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_group tool to create a new group with name {group_name} "
        f"in board {created_board_id}. "
        "If successful, start your response with 'Created group successfully' and then list the group ID in format 'ID: <group_id>'."
    )

    assert (
        "created group successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_group"

    try:
        created_group_id = response.split("ID: ")[1].split()[0]
        print(f"Created group ID: {created_group_id}")
    except IndexError:
        pytest.fail("Could not extract group ID from response")

    print(f"Response: {response}")
    print("✅ create_group passed.")


@pytest.mark.asyncio
async def test_create_column(client):
    """Create a new column in a board."""
    global created_column_id
    if not created_board_id:
        pytest.skip("No board ID available - run create_board test first")

    title = f"Test Column {uuid.uuid4()}"
    column_type = "text"

    response = await client.process_query(
        f"Use the create_column tool to create a new column with title {title} and type {column_type} "
        f"in board {created_board_id}. "
        "If successful, start your response with 'Created column successfully' and then list the column ID in format 'ID: <column_id>'."
    )

    assert (
        "created column successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_column"

    try:
        created_column_id = response.split("ID: ")[1].split()[0]
        print(f"Created column ID: {created_column_id}")
    except IndexError:
        pytest.fail("Could not extract column ID from response")

    print(f"Response: {response}")
    print("✅ create_column passed.")


@pytest.mark.asyncio
async def test_create_item(client):
    """Create a new item in a board."""
    global created_item_id
    if not created_board_id or not created_group_id:
        pytest.skip(
            "No board ID or group ID available - run create_board and create_group tests first"
        )

    item_name = f"Test Item {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_item tool to create a new item with name {item_name} in board {created_board_id} and group {created_group_id}. "
        "If successful, start your response with 'Created item successfully' and then list the item ID in format 'ID: <item_id>'."
    )

    assert (
        "created item successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_item"

    try:
        created_item_id = response.split("ID: ")[1].split()[0]
        print(f"Created item ID: {created_item_id}")
    except IndexError:
        pytest.fail("Could not extract item ID from response")

    print(f"Response: {response}")
    print("✅ create_item passed.")


@pytest.mark.asyncio
async def test_create_subitem(client):
    """Create a new sub-item under a parent item."""
    global created_subitem_id
    if not created_item_id:
        pytest.skip("No item ID available - run create_item test first")

    item_name = f"Test Subitem {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_subitem tool to create a new subitem with name {item_name} "
        f"under parent item {created_item_id}. "
        "If successful, start your response with 'Created subitem successfully' and then list the subitem ID in format 'ID: <subitem_id>'."
    )

    assert (
        "created subitem successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_subitem"

    try:
        created_subitem_id = response.split("ID: ")[1].split()[0]
        print(f"Created subitem ID: {created_subitem_id}")
    except IndexError:
        pytest.fail("Could not extract subitem ID from response")

    print(f"Response: {response}")
    print("✅ create_subitem passed.")


# ===== READ OPERATIONS =====
@pytest.mark.asyncio
async def test_get_me(client):
    """Get the current user's information."""
    response = await client.process_query(
        "Use the get_me tool to fetch current user information. "
        "If successful, start your response with 'Here is the user information' and then list the details."
    )

    assert (
        "here is the user information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_me"

    print(f"Response: {response}")
    print("✅ get_me passed.")


@pytest.mark.asyncio
async def test_get_workspaces(client):
    """Get all workspaces accessible to the user."""
    response = await client.process_query(
        "Use the get_workspaces tool to fetch all accessible workspaces. "
        "If successful, start your response with 'Here are the workspaces' and then list them."
    )

    assert (
        "here are the workspaces" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_workspaces"

    print(f"Response: {response}")
    print("✅ get_workspaces passed.")


@pytest.mark.asyncio
async def test_get_boards(client):
    """Get all boards accessible to the user."""
    response = await client.process_query(
        "Use the get_boards tool to fetch all accessible boards. "
        "If successful, start your response with 'Here are the boards' and then list them."
    )

    assert (
        "here are the boards" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_boards"

    print(f"Response: {response}")
    print("✅ get_boards passed.")


@pytest.mark.asyncio
async def test_get_board(client):
    """Get a specific board by ID."""
    if not created_board_id:
        pytest.skip("No board ID available - run create_board test first")

    response = await client.process_query(
        f"Use the get_board tool to fetch details for board ID {created_board_id}. "
        "If successful, start your response with 'Here are the board details' and then list them."
    )

    assert (
        "here are the board details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_board"

    print(f"Response: {response}")
    print("✅ get_board passed.")


@pytest.mark.asyncio
async def test_get_group(client):
    """Get a specific group within a board."""
    if not created_board_id or not created_group_id:
        pytest.skip(
            "No board ID or group ID available - run create_board and create_group tests first"
        )

    response = await client.process_query(
        f"Use the get_group tool to fetch details for group ID {created_group_id} in board {created_board_id}. "
        "If successful, start your response with 'Here are the group details' and then list them."
    )

    assert (
        "here are the group details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_group"

    print(f"Response: {response}")
    print("✅ get_group passed.")


@pytest.mark.asyncio
async def test_get_item(client):
    """Get a specific item by its ID."""
    if not created_item_id:
        pytest.skip("No item ID available - run create_item test first")

    response = await client.process_query(
        f"Use the get_item tool to fetch details for item ID {created_item_id}. "
        "If successful, start your response with 'Here are the item details' and then list them."
    )

    assert (
        "here are the item details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_item"

    print(f"Response: {response}")
    print("✅ get_item passed.")


@pytest.mark.asyncio
async def test_get_subitems(client):
    """Get all subitems of a specific item."""
    if not created_item_id:
        pytest.skip("No item ID available - run create_item test first")

    response = await client.process_query(
        f"Use the get_subitems tool to fetch all subitems for item ID {created_item_id}. "
        "If successful, start your response with 'Here are the subitems' and then list them."
    )

    assert (
        "here are the subitems" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_subitems"

    print(f"Response: {response}")
    print("✅ get_subitems passed.")


# ===== UPDATE OPERATIONS =====
@pytest.mark.asyncio
async def test_change_column_value(client):
    """Change the value of a column for a specific item."""
    if not created_item_id or not created_column_id:
        pytest.skip(
            "No item ID or column ID available - run create_item and create_column tests first"
        )

    value = "New test value"

    response = await client.process_query(
        f"Use the change_column_value tool to update column {created_column_id} with value {value} "
        f"for item {created_item_id} in board {created_board_id}. "
        "If successful, start your response with 'Updated column value successfully'."
    )

    assert (
        "updated column value successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from change_column_value"

    print(f"Response: {response}")
    print("✅ change_column_value passed.")


# ===== DELETE OPERATIONS =====
@pytest.mark.asyncio
async def test_delete_subitem(client):
    """Delete a sub-item by its ID."""
    if not created_subitem_id:
        pytest.skip("No subitem ID available - run create_subitem test first")

    response = await client.process_query(
        f"Use the delete_subitem tool to delete subitem ID {created_subitem_id}. "
        "If successful, start your response with 'Deleted subitem successfully'."
    )

    assert (
        "deleted subitem successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_subitem"

    print(f"Response: {response}")
    print("✅ delete_subitem passed.")


@pytest.mark.asyncio
async def test_delete_item(client):
    """Delete a specific item by its ID."""
    if not created_item_id:
        pytest.skip("No item ID available - run create_item test first")

    response = await client.process_query(
        f"Use the delete_item tool to delete item ID {created_item_id}. "
        "If successful, start your response with 'Deleted item successfully'."
    )

    assert (
        "deleted item successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_item"

    print(f"Response: {response}")
    print("✅ delete_item passed.")


@pytest.mark.asyncio
async def test_delete_group(client):
    """Delete a specific group from a board."""
    if not created_group_id:
        pytest.skip("No group ID available - run create_group test first")

    response = await client.process_query(
        f"Use the delete_group tool to delete group ID {created_group_id} from board {created_board_id}. "
        "If successful, start your response with 'Deleted group successfully'."
    )

    assert (
        "deleted group successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_group"

    print(f"Response: {response}")
    print("✅ delete_group passed.")


@pytest.mark.asyncio
async def test_archive_board(client):
    """Archive a specific board by its ID."""
    if not created_board_id:
        pytest.skip("No board ID available - run create_board test first")

    response = await client.process_query(
        f"Use the archive_board tool to archive board ID {created_board_id}. "
        "If successful, start your response with 'Archived board successfully'."
    )

    assert (
        "archived board successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from archive_board"

    print(f"Response: {response}")
    print("✅ archive_board passed.")
