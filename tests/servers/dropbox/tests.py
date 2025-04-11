import pytest
import uuid
import os
from datetime import datetime

# Global variables to store created paths and test file info
test_folder_path = None
test_file_path = None
test_file_name = None
local_download_path = "/tmp/dropbox_test_downloads"  # Directory for downloaded files
current_date = datetime.now().strftime("%Y-%m-%d")


# Create a test file to upload
def setup_test_file():
    """Create a temporary test file for upload tests."""
    global test_file_path, test_file_name

    # Create test file with unique name
    test_file_name = f"test_file_{uuid.uuid4()}.txt"
    test_file_path = f"/tmp/{test_file_name}"

    # Write some content to the file
    with open(test_file_path, "w") as f:
        f.write(
            f"This is a test file created for Dropbox API testing on {current_date}."
        )

    # Ensure download directory exists
    os.makedirs(local_download_path, exist_ok=True)

    return test_file_path, test_file_name


@pytest.fixture(scope="module", autouse=True)
def prepare_test_environment():
    """Set up the test environment."""
    setup_test_file()
    yield
    # Clean up test files after tests
    if os.path.exists(test_file_path):
        os.remove(test_file_path)

    for file in os.listdir(local_download_path):
        file_path = os.path.join(local_download_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)


# USER INFO TEST (Read user info first to verify connection)


@pytest.mark.asyncio
async def test_get_user_info(client):
    """Get information about the current user.

    Verifies that user information is retrieved successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    response = await client.process_query(
        "Use the get_user_info tool to fetch information about my Dropbox account. "
        "If successful, start your response with 'Here is your Dropbox account info' and then show the details."
    )

    assert (
        "here is your dropbox account info" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_user_info"

    print(f"Response: {response}")
    print("✅ get_user_info passed.")


# FOLDER CREATION TEST


@pytest.mark.asyncio
async def test_create_folder(client):
    """Create a new folder in Dropbox.

    Verifies that the folder is created successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_folder_path
    folder_name = f"test_folder_{uuid.uuid4()}"
    path = ""  # Root directory

    response = await client.process_query(
        f"Use the create_folder tool to create a folder named '{folder_name}' in the root directory path '{path}'. "
        "If successful, start your response with 'Folder created successfully' and include the folder path."
    )

    assert (
        "folder created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_folder"

    # Extract folder path from response
    try:
        test_folder_path = f"/{folder_name}"  # Constructing expected path
        print(f"Created folder path: {test_folder_path}")
    except Exception:
        pytest.fail("Could not determine folder path from response")

    print(f"Response: {response}")
    print("✅ create_folder passed.")


# FILE UPLOAD TEST


@pytest.mark.asyncio
async def test_upload_file(client):
    """Upload a file to Dropbox.

    Verifies that the file is uploaded successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_folder_path, test_file_path, test_file_name

    response = await client.process_query(
        f"Use the upload_file tool to upload the file at local path '{test_file_path}' "
        f"with file name '{test_file_name}' to the Dropbox path '{test_folder_path}' in 'add' mode. "
        "If successful, start your response with 'File uploaded successfully' and include the file path."
    )

    assert (
        "file uploaded successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from upload_file"

    print(f"Response: {response}")
    print("✅ upload_file passed.")


# LIST FILES TEST


@pytest.mark.asyncio
async def test_list_files(client):
    """List files in a Dropbox folder.

    Verifies that files are listed successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_folder_path

    response = await client.process_query(
        f"Use the list_files tool to list all files and folders in the path '{test_folder_path}'. "
        "If successful, start your response with 'Files listed successfully' and include the file listing."
    )

    assert (
        "files listed successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_files"
    assert (
        test_file_name.lower() in response.lower()
    ), f"Expected file name not found in response: {response}"

    print(f"Response: {response}")
    print("✅ list_files passed.")


# FILE METADATA TEST


@pytest.mark.asyncio
async def test_get_file_metadata(client):
    """Get metadata for a file in Dropbox.

    Verifies that file metadata is retrieved successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_folder_path, test_file_name
    file_path = f"{test_folder_path}/{test_file_name}"

    response = await client.process_query(
        f"Use the get_file_metadata tool to get metadata for the file at path '{file_path}'. "
        "If successful, start your response with 'File metadata retrieved successfully' and include the details."
    )

    assert (
        "file metadata retrieved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_file_metadata"
    assert (
        test_file_name.lower() in response.lower()
    ), f"Expected file name not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_file_metadata passed.")


# SEARCH TEST


@pytest.mark.asyncio
async def test_search(client):
    """Search for a file in Dropbox.

    Verifies that search returns results successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_file_name

    response = await client.process_query(
        f"Use the search tool to search for files with the query '{test_file_name}'. "
        "If successful, start your response with 'Search completed successfully' and include the search results."
    )

    assert (
        "search completed successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from search"
    assert (
        test_file_name.lower() in response.lower()
    ), f"Expected file name not found in response: {response}"

    print(f"Response: {response}")
    print("✅ search passed.")


# DOWNLOAD TEST


@pytest.mark.asyncio
async def test_download(client):
    """Download a file from Dropbox.

    Verifies that file is downloaded successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_folder_path, test_file_name, local_download_path
    file_path = f"{test_folder_path}/{test_file_name}"

    response = await client.process_query(
        f"Use the download tool to download the file at path '{file_path}' "
        f"to the local path '{local_download_path}' with the file name '{test_file_name}'. "
        "If successful, start your response with 'File downloaded successfully' and include the local file path."
    )

    assert (
        "file downloaded successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from download"

    # Verify the file exists locally
    local_file_path = os.path.join(local_download_path, test_file_name)
    assert os.path.exists(
        local_file_path
    ), f"Downloaded file not found at {local_file_path}"

    print(f"Response: {response}")
    print("✅ download passed.")


# MOVE TEST


@pytest.mark.asyncio
async def test_move(client):
    """Move a file in Dropbox.

    Verifies that file is moved successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_folder_path, test_file_name
    from_path = f"{test_folder_path}/{test_file_name}"
    to_path = ""  # Root directory

    response = await client.process_query(
        f"Use the move tool to move the file from path '{from_path}' "
        f"to the path '{to_path}' with the file name '{test_file_name}'. "
        "If successful, start your response with 'File moved successfully' and include the new file path."
    )

    assert (
        "file moved successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from move"

    print(f"Response: {response}")
    print("✅ move passed.")


# DELETE TESTS


@pytest.mark.asyncio
async def test_delete_file(client):
    """Delete a file from Dropbox.

    Verifies that the file is deleted successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_file_name
    file_path = f"/{test_file_name}"  # File was moved to root in previous test

    response = await client.process_query(
        f"Use the delete tool to delete the file at path '{file_path}'. "
        "If successful, start your response with 'File deleted successfully' and include the deleted file path."
    )

    assert (
        "deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete"

    print(f"Response: {response}")
    print("✅ delete_file passed.")


@pytest.mark.asyncio
async def test_delete_folder(client):
    """Delete a folder from Dropbox.

    Verifies that the folder is deleted successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global test_folder_path

    response = await client.process_query(
        f"Use the delete tool to delete the folder at path '{test_folder_path}'. "
        "If successful, start your response with 'Folder deleted successfully' and include the deleted folder path."
    )

    assert (
        "deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete"

    print(f"Response: {response}")
    print("✅ delete_folder passed.")
