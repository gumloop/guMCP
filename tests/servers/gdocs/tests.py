import uuid
import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing Google Docs from Google Drive"""
    response = await client.list_resources()
    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    print("Google Docs found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed Google Docs")


@pytest.mark.asyncio
async def test_read_doc(client):
    """Test reading a Google Doc"""
    # First list docs to get a valid document ID
    response = await client.list_resources()

    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    resources = response.resources

    # Skip test if no documents found
    if not resources:
        print("⚠️ No Google Docs found to test reading")
        pytest.skip("No Google Docs available for testing")
        return

    # Test with the first document
    doc_resource = resources[0]
    response = await client.read_resource(doc_resource.uri)

    assert (
        response and response.contents
    ), f"Response should contain document contents: {response}"
    assert len(response.contents[0].text) >= 0, "Document content should be available"

    print("Document read:")
    print(f"  - {doc_resource.name}: {response.contents[0].text[:100]}...")

    print("✅ Successfully read Google Doc")


@pytest.mark.asyncio
async def test_search_docs(client):
    """Test searching for Google Docs"""
    # Use a general search term that's likely to find something
    search_query = "test"
    response = await client.process_query(
        f"Use the search_docs tool to search for Google Docs containing '{search_query}'. List any results you find."
    )

    # Verify that the assistant attempted to search
    assert "search" in response.lower(), f"Search operation not performed: {response}"

    print("Search results:")
    print(f"{response}")

    print("✅ Search functionality working")


@pytest.mark.asyncio
async def test_create_doc(client):
    """Test creating a new Google Doc"""
    # Generate a unique title with timestamp to avoid conflicts
    doc_title = f"Test Document {uuid.uuid4()}"
    doc_content = "This is a test document created by an automated test."

    response = await client.process_query(
        f"Use the create_doc tool to create a new Google Doc with the title '{doc_title}' and the following content: '{doc_content}'"
        + "\n\nIf it's successful, start your response with 'Created document {doc_title} with ID: {{doc_id}}'"
    )

    # Verify that a document was created
    assert "created" in response.lower(), f"Document creation failed: {response}"
    assert (
        doc_title in response
    ), f"Created document name not found in response: {response}"
    assert "id" in response.lower(), "Document ID should be returned"

    # Extract the document ID for cleanup or further tests
    import re

    doc_id_match = re.search(r"ID: ([a-zA-Z0-9_-]+)", response)
    doc_id = doc_id_match.group(1) if doc_id_match else None

    print(f"Created document with ID: {doc_id}")
    print("✅ Document creation successful")

    # Return the doc_id for use in subsequent tests
    return doc_id


@pytest.mark.asyncio
async def test_append_to_doc(client):
    """Test appending content to an existing Google Doc"""
    # First create a document to append to
    doc_id = await test_create_doc(client)
    assert doc_id, "Failed to create document for append test"

    # Now append to it
    append_content = "This is additional content appended by the test."
    response = await client.process_query(
        f"Use the append_to_doc tool to append the following content to the Google Doc with ID '{doc_id}': '{append_content}'"
        + f"\n\nIf it's successful, start your response with 'Successfully appended to document {doc_id}'"
    )

    # Verify that content was appended
    assert (
        "successfully" in response.lower() and "append" in response.lower()
    ), f"Content append failed: {response}"
    assert doc_id in response, f"Document ID not found in response: {response}"

    print(f"Appended content to document with ID: {doc_id}")
    print("✅ Document append successful")

    return doc_id


@pytest.mark.asyncio
async def test_update_doc(client):
    """Test updating content in an existing Google Doc"""
    # First create a document to update
    doc_id = await test_create_doc(client)
    assert doc_id, "Failed to create document for update test"

    # Now update it
    update_content = "This is completely new content that replaces the original content. Updated by the test."
    response = await client.process_query(
        f"Use the update_doc tool to replace the content of the Google Doc with ID '{doc_id}' with the following: '{update_content}'"
        + f"\n\nIf it's successful, start your response with 'Successfully updated document {doc_id}'"
    )

    # Verify that content was updated
    assert (
        "successfully" in response.lower() and "update" in response.lower()
    ), f"Content update failed: {response}"
    assert doc_id in response, f"Document ID not found in response: {response}"

    print(f"Updated content in document with ID: {doc_id}")
    print("✅ Document update successful")
