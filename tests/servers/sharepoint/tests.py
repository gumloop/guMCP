import pytest
import uuid

# Global variables to store test data
test_list_id = None
test_item_id = None

# Add your site id here
site_id = "https://<domain>.sharepoint.com/sites/<site_name>"


@pytest.mark.asyncio
async def test_get_users(client):
    """Test getting users from SharePoint.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_users tool to list users from SharePoint. "
        "If successful, start your response with 'Users retrieved successfully' and include the results."
    )

    assert (
        "users retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_users"

    print(f"Response: {response}")
    print("✅ get_users passed.")


@pytest.mark.asyncio
async def test_create_list(client):
    """Test creating a list in SharePoint.

    Args:
        client: The test client fixture for the MCP server.
    """
    global test_list_id
    test_list_name = f"TestList_{str(uuid.uuid4())[:8]}"

    response = await client.process_query(
        f"Use the create_list tool to create a new list in SharePoint site '{site_id}' with name '{test_list_name}'. "
        "If successful, start your response with 'List created successfully' and include the list details."
        "Return the creates list id in format 'ID: <list_id>'"
    )

    assert (
        "list created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        test_list_name.lower() in response.lower()
    ), f"List name not found in response: {response}"

    try:
        test_list_id = response.split("ID: ")[1].strip()
        assert test_list_id, "List ID not found in response"
    except Exception as e:
        pytest.fail(f"Failed to extract list ID from response:{e} {response}")

    print(f"Response: {response}")
    print("✅ create_list passed.")


@pytest.mark.asyncio
async def test_get_list(client):
    """Test getting a list from SharePoint.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_list_id:
        pytest.skip("No list created - run create_list test first")

    response = await client.process_query(
        f"Use the get_list tool to get the list '{test_list_id}' from SharePoint site '{site_id}'. "
        "If successful, start your response with 'List retrieved successfully' and include the list details."
    )

    assert (
        "list retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_list passed.")


@pytest.mark.asyncio
async def test_create_list_item(client):
    """Test creating an item in a SharePoint list.

    Args:
        client: The test client fixture for the MCP server.
    """
    global test_item_id
    if not test_list_id:
        pytest.skip("No list created - run create_list test first")

    test_fields = {
        "Title": f"Test Item {str(uuid.uuid4())[:8]}",
    }

    response = await client.process_query(
        f"Use the create_list_item tool to create a new item in list '{test_list_id}' at site '{site_id}' with fields {test_fields}. "
        "If successful, start your response with 'List item created successfully' and include the item details."
        "Return the created item id in format 'ID: <item_id>'"
    )

    assert (
        "list item created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        test_fields["Title"].lower() in response.lower()
    ), f"Item title not found in response: {response}"

    try:
        test_item_id = response.split("ID: ")[1].strip()
        assert test_item_id, "Item ID not found in response"
    except Exception as e:
        pytest.fail(f"Failed to extract item ID from response:{e} {response}")

    print(f"Response: {response}")
    print("✅ create_list_item passed.")


@pytest.mark.asyncio
async def test_get_list_item(client):
    """Test getting a specific item from a SharePoint list.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_list_id or not test_item_id:
        pytest.skip(
            "No list or item created - run create_list and create_list_item tests first"
        )

    response = await client.process_query(
        f"Use the get_list_item tool to get item with ID '{test_item_id}' from list '{test_list_id}' at site '{site_id}'. "
        "If successful, start your response with 'List item retrieved successfully' and include the item details."
    )

    assert (
        "list item retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_list_item passed.")


@pytest.mark.asyncio
async def test_get_list_items(client):
    """Test getting items from a SharePoint list.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_list_id:
        pytest.skip("No list created - run create_list test first")

    response = await client.process_query(
        f"Use the get_list_items tool to get items from list '{test_list_id}' at site '{site_id}'. "
        "If successful, start your response with 'List items retrieved successfully' and include the items."
    )

    assert (
        "list items retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_list_items"

    print(f"Response: {response}")
    print("✅ get_list_items passed.")


@pytest.mark.asyncio
async def test_delete_list_item(client):
    """Test deleting an item from a SharePoint list.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_list_id:
        pytest.skip("No list created - run create_list test first")

    # First get the list items to find an item to delete
    response = await client.process_query(
        f"Use the get_list_items tool to get items from list '{test_list_id}' at site '{site_id}'."
    )

    if "no items found" in response.lower():
        pytest.skip("No items found in list to delete")

    # Extract the first item ID from the response
    # This is a simplified approach - in a real test you might want to parse the JSON response
    item_id = "1"  # Default to first item, adjust based on actual response

    response = await client.process_query(
        f"Use the delete_list_item tool to delete item with ID '{item_id}' from list '{test_list_id}' at site '{site_id}'. "
        "If successful, start your response with 'List item deleted successfully' and include the item ID."
    )

    assert (
        "list item deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert str(item_id) in response, f"Item ID not found in response: {response}"

    print(f"Response: {response}")
    print("✅ delete_list_item passed.")
