import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing all Notion users"""
    response = await client.process_query(
        "Use the list-all-users tool. If you find any users, start your response with 'Here are the Notion users' and then list them."
    )

    assert (
        "here are the notion users" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No users returned: {response}"

    print("Users found:")
    print(f"\t{response}")

    print("✅ Successfully listed Notion users")


@pytest.mark.asyncio
async def test_search_pages_tool(client):
    """Test searching pages in Notion"""
    query = "test"

    response = await client.process_query(
        f"Use the search-pages tool to search for '{query}'. If you find any pages, start your response with 'Here are the search results' and then list them."
    )

    assert (
        "here are the search results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No results for query '{query}'"

    print("Pages found:")
    print(f"\t{response}")

    print("✅ Successfully searched Notion pages")


@pytest.mark.asyncio
async def test_list_databases_tool(client):
    """Test listing databases from Notion"""
    response = await client.process_query(
        "Use the list-databases tool. If you find any databases, start your response with 'Here are the Notion databases' and then list them."
    )

    assert (
        "here are the notion databases" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No databases returned: {response}"

    print("Databases found:")
    print(f"\t{response}")

    print("✅ Successfully listed Notion databases")


@pytest.mark.asyncio
async def test_query_database_tool(client):
    """Test querying a Notion database"""
    database_id = "c0343e8e89fa4c0f82466b5c34f3c08a"

    response = await client.process_query(
        f"Use the query-database tool with database_id: {database_id}. If you get any results, start your response with 'Here are the database results' and then list them."
    )

    assert (
        "here are the database results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No results from database {database_id}"

    print("Database query result:")
    print(f"\t{response}")

    print("✅ Successfully queried Notion database")


@pytest.mark.asyncio
async def test_get_page_tool(client):
    """Test retrieving a Notion page"""
    page_id = "34eef81e112742eab82ba4a3530600c7"

    response = await client.process_query(
        f"Use the get-page tool with page_id: {page_id}. If you retrieve the page successfully, start your response with 'Here is the page content' and then show it."
    )

    assert (
        "here is the page content" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No content for page {page_id}"

    print("Page content:")
    print(f"\t{response}")

    print("✅ Successfully retrieved Notion page")


@pytest.mark.asyncio
async def test_create_page_tool(client):
    """Test creating a Notion page"""
    database_id = "c0343e8e89fa4c0f82466b5c34f3c08a"
    properties = {"Name": {"title": [{"text": {"content": "Test Page from MCP"}}]}}

    response = await client.process_query(
        f"Use the create-page tool with database_id: {database_id} and properties: {properties}. If the page is created successfully, start your response with 'Page created successfully' and include the page ID."
    )

    assert (
        "page created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and "id" in response, f"Page creation failed: {response}"

    print("Page created:")
    print(f"\t{response}")

    print("✅ Successfully created Notion page")


@pytest.mark.asyncio
async def test_append_blocks_tool(client):
    """Test appending blocks to a Notion page"""
    block_id = "34eef81e112742eab82ba4a3530600c7"
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
        f"Use the append-blocks tool with block_id: {block_id} and children: {children}. If blocks are appended successfully, start your response with 'Blocks appended successfully'."
    )

    assert (
        "blocks appended successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and "block" in response.lower(), f"Append failed: {response}"

    print("Block appended:")
    print(f"\t{response}")

    print("✅ Successfully appended block to Notion")


@pytest.mark.asyncio
async def test_get_block_children_tool(client):
    """Test retrieving child blocks from Notion"""
    block_id = "34eef81e112742eab82ba4a3530600c7"

    response = await client.process_query(
        f"Use the get-block-children tool with block_id: {block_id}. If you find any child blocks, start your response with 'Here are the block children' and then list them."
    )

    assert (
        "here are the block children" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No children found for block {block_id}"

    print("Block children found:")
    print(f"\t{response}")

    print("✅ Successfully retrieved block children")
