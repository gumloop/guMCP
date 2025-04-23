import pytest
import uuid
import os
import tempfile

# Global variables to store test data
test_list_id = None
test_item_id = None
test_folder_id = None
test_file_id = None
test_page_id = None
local_test_file_path = None

# Add your site id here
site_id = "https://cognida.sharepoint.com/sites/CognidaPvtLimited"


def unique_name(prefix):
    return f"{prefix}_{str(uuid.uuid4())[:8]}"


def create_test_file(content="Test content"):
    """Create a temporary test file with specified content."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


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
async def test_list_site_lists(client):
    response = await client.process_query(
        f"Use the list_site_lists tool to list all lists in SharePoint site '{site_id}'. "
        "If successful, start your response with 'Lists retrieved successfully' and include the results."
    )
    assert (
        "lists retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    print(f"Response: {response}")
    print("✅ list_site_lists passed.")


@pytest.mark.asyncio
async def test_create_list(client):
    """Test creating a list in SharePoint.

    Args:
        client: The test client fixture for the MCP server.
    """
    global test_list_id
    test_list_name = unique_name("TestList")

    response = await client.process_query(
        f"Use the create_list tool to create a new list in SharePoint site '{site_id}' with name '{test_list_name}'. "
        "If successful, start your response with 'List created successfully' and include the list details. "
        "Return the creates list id in format 'ID: <list_id>'"
    )

    assert (
        "list created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        test_list_name.lower() in response.lower()
    ), f"List name not found in response: {response}"

    try:
        test_list_id = response.split("ID: ")[1].strip().split()[0]
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

    test_fields = {"Title": unique_name("TestItem")}

    response = await client.process_query(
        f"Use the create_list_item tool to create a new item in list '{test_list_id}' at site '{site_id}' with fields {test_fields}. "
        "If successful, start your response with 'List item created successfully' and include the item details. "
        "Return the created item id in format 'ID: <item_id>'"
    )

    assert (
        "list item created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        test_fields["Title"].lower() in response.lower()
    ), f"Item title not found in response: {response}"

    try:
        test_item_id = response.split("ID: ")[1].strip().split()[0]
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
async def test_update_list_item(client):
    if not test_list_id or not test_item_id:
        pytest.skip(
            "No list or item created - run create_list and create_list_item tests first"
        )
    update_fields = {"Title": unique_name("UpdatedItem")}
    response = await client.process_query(
        f"Use the update_list_item tool to update item with ID '{test_item_id}' in list '{test_list_id}' at site '{site_id}' with fields {update_fields}. "
        "If successful, start your response with 'List item updated successfully' and include the updated item details."
    )
    assert (
        "list item updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    print(f"Response: {response}")
    print("✅ update_list_item passed.")


@pytest.mark.asyncio
async def test_delete_list_item(client):
    """Test deleting an item from a SharePoint list.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_list_id or not test_item_id:
        pytest.skip(
            "No list or item created - run create_list and create_list_item tests first"
        )

    response = await client.process_query(
        f"Use the delete_list_item tool to delete item with ID '{test_item_id}' from list '{test_list_id}' at site '{site_id}'. "
        "If successful, start your response with 'List item deleted successfully' and include the item ID."
    )

    assert (
        "list item deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert str(test_item_id) in response, f"Item ID not found in response: {response}"

    print(f"Response: {response}")
    print("✅ delete_list_item passed.")


@pytest.mark.asyncio
async def test_create_folder(client):
    global test_folder_id
    folder_name = unique_name("TestFolder")
    response = await client.process_query(
        f"Use the create_folder tool to create a new folder named '{folder_name}' in your OneDrive. "
        "If successful, start your response with 'Folder created successfully' and include the folder details. "
        "Return the created folder id in format 'ID: <folder_id>'"
    )
    assert (
        "folder created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    try:
        test_folder_id = response.split("ID: ")[1].strip().split()[0]
        assert test_folder_id, "Folder ID not found in response"
    except Exception as e:
        pytest.fail(f"Failed to extract folder ID from response:{e} {response}")
    print(f"Response: {response}")
    print("✅ create_folder passed.")


@pytest.mark.asyncio
async def test_upload_file(client):
    """Test uploading a file to SharePoint.

    Args:
        client: The test client fixture for the MCP server.
    """
    global local_test_file_path, test_file_id

    if not test_folder_id:
        pytest.skip("No folder created - run create_folder test first")

    # Create a local test file
    local_test_file_path = create_test_file(
        f"SharePoint Test File Content {uuid.uuid4()}"
    )

    response = await client.process_query(
        f"Use the upload_file tool to upload the file at '{local_test_file_path}' to the folder with ID '{test_folder_id}' in your OneDrive. "
        "If successful, start your response with 'File uploaded successfully' and include the file details. "
        "Return the created file id in format 'ID: <file_id>'"
    )

    assert (
        "file uploaded successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    try:
        test_file_id = response.split("ID: ")[1].strip().split()[0]
        assert test_file_id, "File ID not found in response"
    except Exception as e:
        pytest.fail(f"Failed to extract file ID from response:{e} {response}")

    print(f"Response: {response}")
    print("✅ upload_file passed.")


@pytest.mark.asyncio
async def test_download_file(client):
    if not test_file_id:
        pytest.skip("No file uploaded - run upload_file test first")
    response = await client.process_query(
        f"Use the download_file tool to download the file with ID '{test_file_id}' from your OneDrive. "
        "If successful, start your response with 'File downloaded successfully' and include the file details."
    )
    assert (
        "file downloaded successfully" in response.lower()
        or "successfully retrieved file content" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    print(f"Response: {response}")
    print("✅ download_file passed.")


@pytest.mark.asyncio
async def test_create_site_page(client):
    global test_page_id
    page_name = unique_name("TestPage")
    page_title = "Test Page Title"
    response = await client.process_query(
        f"Use the create_site_page tool to create a new site page named '{page_name}' with title '{page_title}' in SharePoint site '{site_id}'. "
        "If successful, start your response with 'Site page created successfully' and include the page details. "
        "Return the created page id in format 'ID: <page_id>'"
    )
    assert (
        "site page created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    try:
        test_page_id = response.split("ID: ")[1].strip().split()[0]
        assert test_page_id, "Page ID not found in response"
    except Exception as e:
        pytest.fail(f"Failed to extract page ID from response:{e} {response}")
    print(f"Response: {response}")
    print("✅ create_site_page passed.")


@pytest.mark.asyncio
async def test_get_site_page(client):
    if not test_page_id:
        pytest.skip("No site page created - run create_site_page test first")
    response = await client.process_query(
        f"Use the get_site_page tool to get the page with ID '{test_page_id}' from SharePoint site '{site_id}'. "
        "If successful, start your response with 'Site page retrieved successfully' and include the page details."
    )
    assert (
        "site page retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    print(f"Response: {response}")
    print("✅ get_site_page passed.")


@pytest.mark.asyncio
async def test_list_site_pages(client):
    response = await client.process_query(
        f"Use the list_site_pages tool to list all pages in SharePoint site '{site_id}'. "
        "If successful, start your response with 'Site pages retrieved successfully' and include the results."
    )
    assert (
        "site pages retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    print(f"Response: {response}")
    print("✅ list_site_pages passed.")


@pytest.mark.asyncio
async def test_get_site_info(client):
    response = await client.process_query(
        f"Use the get_site_info tool to get information about SharePoint site '{site_id}'. "
        "If successful, start your response with 'Site info retrieved successfully' and include the site details."
    )
    assert (
        "site info retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    print(f"Response: {response}")
    print("✅ get_site_info passed.")


@pytest.mark.asyncio
async def test_search_sites(client):
    response = await client.process_query(
        f"Use the search_sites tool to search for sites with the query 'test'. "
        "If successful, start your response with 'Sites search successful' and include the results."
    )
    assert (
        "sites search successful" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    print(f"Response: {response}")
    print("✅ search_sites passed.")


def teardown_module(module):
    """Clean up any remaining test files after all tests are run."""
    if local_test_file_path and os.path.exists(local_test_file_path):
        os.remove(local_test_file_path)
        print(f"Cleaned up local test file: {local_test_file_path}")
