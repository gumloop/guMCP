import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing files from Google Drive"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_file(client):
    """Test reading a google docs file"""
    # First list files to get a valid file ID
    response = await client.list_resources()

    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    resources = response.resources

    for resource in resources:
        response = await client.read_resource(resource.uri)

        assert len(
            response.contents[0].text
        ), f"Response should contain file contents: {response}"

        print("File read:")
        print(f"\t{response.contents[0].text}")

        print("✅ Successfully read gdrive file")
        return


@pytest.mark.asyncio
async def test_search_files(client):
    """Test searching for files"""
    response = await client.process_query(
        f"Use the search tool to search for ALL my google drive files (*). If you find anything, start your response with 'Here are your search results' and then list them."
    )

    # Verify search results
    assert (
        "here are your search results" in response.lower()
    ), f"Search results could not files: {response}"

    print("Search results:")
    print(f"\t{response}")

    print("✅ Search functionality working")
