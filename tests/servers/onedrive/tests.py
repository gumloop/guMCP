import pytest
import os
import uuid
import tempfile

# Global variables to store created test file paths
local_test_file_path = None
remote_test_folder_name = None
remote_test_file_name = None


def create_test_file(content="Test content"):
    """Create a temporary test file with specified content."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


@pytest.mark.asyncio
async def test_list_files(client):
    """Test listing files in a OneDrive directory.

    Args:
        client: The test client fixture for the MCP server.
    """
    folder_path = "/"  # Root folder

    response = await client.process_query(
        f"Use the list_files tool to list files and folders in '{folder_path}'. "
        "If successful, start your response with 'Here are the OneDrive contents' and include the results."
    )

    assert (
        "here are the onedrive contents" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_files"

    print(f"Response: {response}")
    print("✅ list_files passed.")


@pytest.mark.asyncio
async def test_create_folder(client):
    """Test creating a folder in OneDrive.

    Args:
        client: The test client fixture for the MCP server.
    """
    global remote_test_folder_name

    folder_path = "/"
    remote_test_folder_name = f"TestFolder_{str(uuid.uuid4())[:8]}"

    response = await client.process_query(
        f"Use the create_folder tool to create a new folder at path '{folder_path}' with the name '{remote_test_folder_name}'. "
        "If successful, start your response with 'Folder created successfully' and include the folder details."
    )

    assert (
        "folder created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        remote_test_folder_name.lower() in response.lower()
    ), f"Folder name not found in response: {response}"

    print(f"Response: {response}")
    print("✅ create_folder passed.")


@pytest.mark.asyncio
async def test_upload_file(client):
    """Test uploading a file to OneDrive.

    Args:
        client: The test client fixture for the MCP server.
    """
    global local_test_file_path, remote_test_file_name

    # Create a local test file
    local_test_file_path = create_test_file(
        f"OneDrive Test File Content {uuid.uuid4()}"
    )
    remote_test_file_name = f"TestFile_{str(uuid.uuid4())[:8]}.txt"
    destination_path = f"/{remote_test_folder_name}/{remote_test_file_name}"

    response = await client.process_query(
        f"Use the upload_file tool to upload the file located at '{local_test_file_path}' "
        f"to OneDrive path '{destination_path}'. "
        "If successful, start your response with 'File uploaded successfully' and include the file details."
    )

    assert (
        "file uploaded successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        destination_path.lower() in response.lower()
        or remote_test_file_name.lower() in response.lower()
    ), f"File path not found in response: {response}"

    print(f"Response: {response}")
    print("✅ upload_file passed.")


@pytest.mark.asyncio
async def test_search_files(client):
    """Test searching for files in OneDrive.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not remote_test_file_name:
        pytest.skip("No file uploaded - run upload_file test first")

    # Use part of the filename as search term to ensure it's unique but will match
    response = await client.process_query(
        f"Use the search_files tool to search for files with the term '{remote_test_file_name}'. "
        "If successful, start your response with 'Search results' and include the found files."
    )

    assert (
        "search results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    # The search should find our uploaded file
    assert (
        remote_test_file_name.lower() in response.lower()
    ), f"Uploaded file name not found in search results: {response}"

    print(f"Response: {response}")
    print("✅ search_files passed.")


@pytest.mark.asyncio
async def test_get_file_sharing_link(client):
    """Test getting a sharing link for a file in OneDrive.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not remote_test_folder_name or not remote_test_file_name:
        pytest.skip("No file uploaded - run upload_file test first")

    response = await client.process_query(
        f"Get the file sharing link for the file {remote_test_file_name} inside directory {remote_test_folder_name}."
        "If successful, start your response with 'Sharing link generated' and include the link."
    )

    assert (
        "sharing link generated" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_file_sharing_link passed.")


@pytest.mark.asyncio
async def test_download_file(client):
    """Test downloading a file from OneDrive.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not remote_test_folder_name or not remote_test_file_name:
        pytest.skip("No file uploaded - run upload_file test first")

    file_path = f"/{remote_test_folder_name}/{remote_test_file_name}"
    local_destination = tempfile.mktemp(suffix="_downloaded.txt")

    response = await client.process_query(
        f"Use the download_file tool to download the file from '{file_path}' "
        f"to local path '{local_destination}'. "
        "If successful, start your response with 'File downloaded successfully' and include the file path."
    )

    assert (
        "file downloaded successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        local_destination in response
    ), f"Local destination path not found in response: {response}"

    # Verify the file exists locally
    assert os.path.exists(
        local_destination
    ), f"Downloaded file does not exist at {local_destination}"

    # Clean up the downloaded file
    os.remove(local_destination)

    print(f"Response: {response}")
    print("✅ download_file passed.")


@pytest.mark.asyncio
async def test_delete_item_file(client):
    """Test deleting a file from OneDrive.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not remote_test_folder_name or not remote_test_file_name:
        pytest.skip("No file uploaded - run upload_file test first")

    file_path = f"/{remote_test_folder_name}/{remote_test_file_name}"

    response = await client.process_query(
        f"Use the delete_item tool to delete the file at path '{file_path}'. "
        "If successful, start your response with 'Item deleted successfully' and include the path."
    )

    assert (
        "item deleted successfully" in response.lower()
        or "deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        file_path.lower() in response.lower()
        or remote_test_file_name.lower() in response.lower()
    ), f"File path not found in response: {response}"

    print(f"Response: {response}")
    print("✅ delete_item_file passed.")


@pytest.mark.asyncio
async def test_delete_item_folder(client):
    """Test deleting a folder from OneDrive.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not remote_test_folder_name:
        pytest.skip("No folder created - run create_folder test first")

    folder_path = f"/{remote_test_folder_name}"

    response = await client.process_query(
        f"Use the delete_item tool to delete the folder at path '{folder_path}'. "
        "If successful, start your response with 'Item deleted successfully' and include the path."
    )

    assert (
        "item deleted successfully" in response.lower()
        or "deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        folder_path.lower() in response.lower()
        or remote_test_folder_name.lower() in response.lower()
    ), f"Folder path not found in response: {response}"

    print(f"Response: {response}")
    print("✅ delete_item_folder passed.")


def teardown_module(module):
    """Clean up any remaining test files after all tests are run."""
    if local_test_file_path and os.path.exists(local_test_file_path):
        os.remove(local_test_file_path)
        print(f"Cleaned up local test file: {local_test_file_path}")
