import pytest


@pytest.mark.asyncio
async def test_list_all_users(client):
    """Test the list-all-users tool"""
    response = await client.process_query("Use the list-all-users tool")
    assert response, "No response from list-all-users tool"
    print("✅ list-all-users passed")


@pytest.mark.asyncio
async def test_search_pages(client):
    """Test the search-pages tool"""
    query = "test"
    response = await client.process_query(f"Use the search-pages tool to search for '{query}'")
    assert response, "No response from search-pages tool"
    print("✅ search-pages passed")


@pytest.mark.asyncio
async def test_list_databases(client):
    """Test the list-databases tool"""
    response = await client.process_query("Use the list-databases tool")
    assert response, "No response from list-databases tool"
    print("✅ list-databases passed")


@pytest.mark.asyncio
async def test_query_database(client):
    """Test the query-database tool"""
    database_id = "your-database-id"
    response = await client.process_query(f"Use the query-database tool with database_id: {database_id}")
    assert response, "No response from query-database tool"
    print("✅ query-database passed")


@pytest.mark.asyncio
async def test_get_page(client):
    """Test the get-page tool"""
    page_id = "your-page-id"
    response = await client.process_query(f"Use the get-page tool with page_id: {page_id}")
    assert response, "No response from get-page tool"
    print("✅ get-page passed")


@pytest.mark.asyncio
async def test_create_page(client):
    """Test the create-page tool"""
    database_id = "your-database-id"
    properties = {"Name": {"title": [{"text": {"content": "Test Page"}}]}}
    response = await client.process_query(
        f"Use the create-page tool with database_id: {database_id} and properties: {properties}"
    )
    assert response, "No response from create-page tool"
    print("✅ create-page passed")


@pytest.mark.asyncio
async def test_append_blocks(client):
    """Test the append-blocks tool"""
    block_id = "your-block-id"
    children = [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "New block content"}}]}}]
    response = await client.process_query(
        f"Use the append-blocks tool with block_id: {block_id} and children: {children}"
    )
    assert response, "No response from append-blocks tool"
    print("✅ append-blocks passed")


@pytest.mark.asyncio
async def test_get_block_children(client):
    """Test the get-block-children tool"""
    block_id = "your-block-id"
    response = await client.process_query(f"Use the get-block-children tool with block_id: {block_id}")
    assert response, "No response from get-block-children tool"
    print("✅ get-block-children passed")
