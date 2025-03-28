import pytest
import json


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing Supabase projects and tables"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed resources")


# @pytest.mark.asyncio
# async def test_read_project(client):
#     """Test reading a Supabase project details"""
#     # First list resources to get a valid project
#     response = await client.list_resources()
#     assert (
#         response and hasattr(response, "resources") and len(response.resources)
#     ), f"Invalid list resources response: {response}"

#     # Find first project resource
#     project_resource = next(
#         (r for r in response.resources if r.uri.startswith("supabase://project/")), None
#     )
#     assert project_resource, "No project resources found"

#     # Read project details
#     response = await client.read_resource(project_resource.uri)
#     assert response and response.contents, "No content returned"

#     project_data = json.loads(response.contents[0].text)
#     assert "id" in project_data, "Project data missing ID field"

#     print("Project details read:")
#     print(f"\t{response.contents[0].text}")
#     print("✅ Successfully read project details")


# @pytest.mark.asyncio
# async def test_read_table(client):
#     """Test reading a table's data"""
#     # First list resources to get a valid table
#     response = await client.list_resources()
#     assert (
#         response and hasattr(response, "resources") and len(response.resources)
#     ), f"Invalid list resources response: {response}"

#     # Find first table resource
#     table_resource = next((r for r in response.resources if "/table/" in r.uri), None)
#     assert table_resource, "No table resources found"

#     # Read table data
#     response = await client.read_resource(table_resource.uri)
#     assert response and response.contents, "No content returned"

#     table_data = json.loads(response.contents[0].text)
#     assert isinstance(table_data, list), "Table data should be a list"

#     print("Table data read:")
#     print(f"\t{response.contents[0].text}")
#     print("✅ Successfully read table data")


# @pytest.mark.asyncio
# async def test_read_table_schema(client):
#     """Test reading a table's schema"""
#     # First list resources to get a valid schema
#     response = await client.list_resources()
#     assert (
#         response and hasattr(response, "resources") and len(response.resources)
#     ), f"Invalid list resources response: {response}"

#     # Find first schema resource
#     schema_resource = next((r for r in response.resources if "/schema/" in r.uri), None)
#     assert schema_resource, "No schema resources found"

#     # Read schema data
#     response = await client.read_resource(schema_resource.uri)
#     assert response and response.contents, "No content returned"

#     schema_data = json.loads(response.contents[0].text)
#     assert isinstance(schema_data, list), "Schema data should be a list"

#     print("Schema data read:")
#     print(f"\t{response.contents[0].text}")
#     print("✅ Successfully read schema data")


# @pytest.mark.asyncio
# async def test_read_table_tool(client):
#     """Test using the read_table tool"""
#     response = await client.process_query(
#         """Use the read_table tool to read the first 5 rows from any table.
#         If successful, start your response with 'Successfully read table data:'
#         followed by the results."""
#     )

#     assert (
#         "successfully read table data:" in response.lower()
#     ), f"Tool execution failed: {response}"

#     print("Read table tool results:")
#     print(f"\t{response}")
#     print("✅ Read table tool working")


# @pytest.mark.asyncio
# async def test_execute_sql_tool(client):
#     """Test using the execute_sql tool"""
#     response = await client.process_query(
#         """Use the execute_sql tool to run a simple SELECT query that counts the number of rows in any table.
#         If successful, start your response with 'SQL query executed successfully:'
#         followed by the results."""
#     )

#     assert (
#         "sql query executed successfully:" in response.lower()
#     ), f"Tool execution failed: {response}"

#     print("Execute SQL tool results:")
#     print(f"\t{response}")
#     print("✅ Execute SQL tool working")
