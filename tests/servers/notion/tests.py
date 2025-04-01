import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing all Notion users"""
    response = await client.process_query("Use the list-all-users tool")

    assert response and len(response) > 0, f"No users returned: {response}"

    print("Users found:")
    for user in response:
        print(f"  - {user.text[:80]}")

    print("✅ Successfully listed Notion users")


@pytest.mark.asyncio
async def test_search_pages_tool(client):
    """Test searching pages in Notion"""
    query = "test"

    response = await client.process_query(
        f"Use the search-pages tool to search for '{query}'"
    )

    assert response and len(response) > 0, f"No results for query '{query}'"

    print("Pages found:")
    for page in response:
        print(f"  - {page.text[:80]}")

    print("✅ Successfully searched Notion pages")


@pytest.mark.asyncio
async def test_list_databases_tool(client):
    """Test listing databases from Notion"""
    response = await client.process_query("Use the list-databases tool")

    assert response and len(response) > 0, f"No databases returned: {response}"

    print("Databases found:")
    for db in response:
        print(f"  - {db.text[:80]}")

    print("✅ Successfully listed Notion databases")


@pytest.mark.asyncio
async def test_query_database_tool(client):
    """Test querying a Notion database"""
    database_id = "test-database-id"

    response = await client.process_query(
        f"Use the query-database tool with database_id: {database_id}"
    )

    assert response and len(response) > 0, f"No results from database {database_id}"

    print("Database query result:")
    print(f"\t{response[0].text[:200]}")

    print("✅ Successfully queried Notion database")


@pytest.mark.asyncio
async def test_get_page_tool(client):
    """Test retrieving a Notion page"""
    page_id = "test-page-id"

    response = await client.process_query(
        f"Use the get-page tool with page_id: {page_id}"
    )

    assert response and len(response) > 0, f"No content for page {page_id}"

    print("Page content:")
    print(f"\t{response[0].text[:200]}")

    print("✅ Successfully retrieved Notion page")


@pytest.mark.asyncio
async def test_create_page_tool(client):
    """Test creating a Notion page"""
    database_id = "test-database-id"
    properties = {"Name": {"title": [{"text": {"content": "Test Page from MCP"}}]}}

    response = await client.process_query(
        f"Use the create-page tool with database_id: {database_id} and properties: {properties}"
    )

    assert response and "id" in response[0].text, f"Page creation failed: {response}"

    print("Page created:")
    print(f"\t{response[0].text[:200]}")

    print("✅ Successfully created Notion page")


@pytest.mark.asyncio
async def test_append_blocks_tool(client):
    """Test appending blocks to a Notion page"""
    block_id = "test-block-id"
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": "Appended block from MCP test"}}]
            },
        }
    ]

    response = await client.process_query(
        f"Use the append-blocks tool with block_id: {block_id} and children: {children}"
    )

    assert response and "block" in response[0].text.lower(), f"Append failed: {response}"

    print("Block appended:")
    print(f"\t{response[0].text[:200]}")

    print("✅ Successfully appended block to Notion")


@pytest.mark.asyncio
async def test_get_block_children_tool(client):
    """Test retrieving child blocks from Notion"""
    block_id = "test-block-id"

    response = await client.process_query(
        f"Use the get-block-children tool with block_id: {block_id}"
    )

    assert response and len(response) > 0, f"No children found for block {block_id}"

    print("Block children found:")
    for child in response:
        print(f"  - {child.text[:80]}")

    print("✅ Successfully retrieved block children")
