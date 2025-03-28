import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing bases and tables from Airtable"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri})")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_table(client):
    """Test reading records from an Airtable table"""
    # First list resources to get a valid base/table ID
    response = await client.list_resources()

    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Take the first table found
    resource = response.resources[0]

    # Read the table contents
    response = await client.read_resource(resource.uri)

    assert len(response.contents) > 0, "Response should contain table contents"
    assert (
        response.contents[0].mimeType == "application/json"
    ), "Response should be JSON"

    print("Table contents:")
    print(f"\t{response.contents[0].text}")

    print("✅ Successfully read Airtable table")


@pytest.mark.asyncio
async def test_read_records_tool(client):
    """Test reading records using the read_records tool"""
    # First get a valid base/table ID from resources
    response = await client.list_resources()
    assert len(response.resources) > 0, "No resources found"

    # Parse the first resource URI to get base_id and table_id
    uri = str(response.resources[1].uri)
    base_id, table_id = uri.replace("airtable:///", "").split("/")

    # Test the read_records tool
    tool_response = await client.session.call_tool(
        "read_records", {"base_id": base_id, "table_id": table_id, "max_records": 5}
    )

    assert (
        tool_response and len(tool_response.content[0].text) > 0
    ), "Tool response should not be empty"
    assert (
        "Retrieved" in tool_response.content[0].text
    ), "Response should confirm records were retrieved"

    print("Read records response:")
    print(f"\t{tool_response.content[0].text}")

    print("✅ Successfully tested read_records tool")


@pytest.mark.asyncio
async def test_create_and_update_records(client):
    """Test creating and updating records"""
    # First get a valid base/table ID from resources
    response = await client.list_resources()
    assert len(response.resources) > 0, "No resources found"

    uri = str(response.resources[0].uri)
    base_id, table_id = uri.replace("airtable:///", "").split("/")

    # Create a test record
    create_response = await client.session.call_tool(
        "create_records",
        {
            "base_id": base_id,
            "table_id": table_id,
            "records": [
                {
                    "fields": {
                        "Project Name": "Test Record",
                        "Project Manager": "Created by automated test",
                    }
                }
            ],
        },
    )

    assert (
        create_response and len(create_response.content) > 0
    ), "Create response should not be empty"
    assert (
        "Successfully created" in create_response.content[0].text
    ), "Response should confirm record creation"

    # Extract the created record ID
    record_id = create_response.content[0].text.split("Record IDs: ")[1].strip()

    # Update the created record
    update_response = await client.session.call_tool(
        "update_records",
        {
            "base_id": base_id,
            "table_id": table_id,
            "records": [
                {
                    "id": record_id,
                    "fields": {"Project Manager": "Updated by automated test"},
                }
            ],
        },
    )

    assert (
        update_response and len(update_response.content) > 0
    ), "Update response should not be empty"
    assert (
        "Successfully updated" in update_response.content[0].text
    ), "Response should confirm record update"

    print("✅ Successfully tested create and update operations")


@pytest.mark.asyncio
async def test_search_with_filter(client):
    """Test searching records using filterByFormula"""
    # First get a valid base/table ID from resources
    response = await client.list_resources()
    assert len(response.resources) > 0, "No resources found"

    uri = str(response.resources[0].uri)
    base_id, table_id = uri.replace("airtable:///", "").split("/")

    # Use read_records tool with a filter
    try:
        response = await client.session.call_tool(
            "read_records",
            {
                "base_id": base_id,
                "table_id": table_id,
                "filter_by_formula": "NOT(BLANK({Project Name}))",
            },
        )

        if response and len(response.content) > 0:
            records_data = response.content[0].text
            response = f"Found records: {records_data}"
        else:
            response = "No records found or empty response"
    except Exception as e:
        response = f"Error searching records: {str(e)}"

    assert (
        "found records" in response.lower()
    ), f"Search results not found in response: {response}"

    print("Search results:")
    print(f"\t{response}")

    print("✅ Search functionality working")
