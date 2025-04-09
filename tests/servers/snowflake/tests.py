import pytest
import uuid

# Global variables to store created post and comment IDs
DB_NAME = "TEST_DB_" + str(uuid.uuid4())[:8]
TABLE_NAME = "TEST_TABLE_" + str(uuid.uuid4())[:8]
WAREHOUSE_NAME = "TEST_WAREHOUSE_" + str(uuid.uuid4())[:8]
SCHEMA_NAME = "TEST_SCHEMA_" + str(uuid.uuid4())[:8]


@pytest.mark.asyncio
async def test_create_database(client):
    """Create a new database in Snowflake.

    Verifies that the database is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the create_database tool to create a new database with name {DB_NAME}."
        "If successful, start your response with 'Database created successfully' and then list the database name in format 'Database: <database_name>'."
    )

    assert (
        "database created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ create_database passed.")


@pytest.mark.asyncio
async def test_create_schema(client):
    """Create a new schema in Snowflake.

    Verifies that the schema is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the create_schema tool to create a new schema with name {SCHEMA_NAME} in the database {DB_NAME}."
        "If successful, start your response with 'Schema created successfully' and then list the schema name in format 'Schema: <schema_name>'."
    )

    assert (
        "schema created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ create_schema passed.")


@pytest.mark.asyncio
async def test_list_schemas(client):
    """List all schemas in a database in Snowflake.

    Verifies that the schemas are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the list_schemas tool to list all schemas in the database {DB_NAME}."
        "If successful, start your response with 'Here are all the schemas in database <database_name>:"
    )

    assert (
        "here are all the schemas in database" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ list_schemas passed.")


@pytest.mark.asyncio
async def test_list_databases(client):
    """List all databases in Snowflake.

    Verifies that the database is listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the list_databases tool to list all databases in Snowflake."
        "If successful, start your response with 'Here are all the databases in Snowflake:'"
    )

    assert (
        "here are all the databases in snowflake" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ list_databases passed.")


@pytest.mark.asyncio
async def test_create_table(client):
    """Create a new table in Snowflake.

    Verifies that the table is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the create_table tool to create a new table with name {TABLE_NAME} in the database {DB_NAME}."
        "It should have 3 columns: id, name, and email."
        "If successful, start your response with 'Table created successfully' and then list the table name in format 'Table: <table_name>'."
    )

    assert (
        "table created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ create_table passed.")


@pytest.mark.asyncio
async def test_list_tables(client):
    """List all tables in a database in Snowflake.

    Verifies that the tables are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the list_tables tool to list all tables in the database {DB_NAME}."
        "If successful, start your response with 'Here are all the tables in the database <database_name>:"
    )

    assert (
        "here are all the tables in the database" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ list_tables passed.")


@pytest.mark.asyncio
async def test_describe_table(client):
    """Describe a table in a database in Snowflake.

    Verifies that the table is described successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the describe_table tool to describe the table {TABLE_NAME} in the database {DB_NAME}."
        "If successful, start your response with 'Here is the description of the table <table_name>:"
    )

    assert (
        "here is the description of the table" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ describe_table passed.")


@pytest.mark.asyncio
async def test_create_warehouse(client):
    """Create a new warehouse in Snowflake.

    Verifies that the warehouse is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the create_warehouse tool to create a new warehouse with name {WAREHOUSE_NAME}."
        "If successful, start your response with 'Warehouse created successfully' and then list the warehouse name in format 'Warehouse: <warehouse_name>'."
    )

    assert (
        "warehouse created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ create_warehouse passed.")


@pytest.mark.asyncio
async def test_list_warehouses(client):
    """List all warehouses in Snowflake.

    Verifies that the warehouses are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the list_warehouses tool to list all warehouses in Snowflake."
        "If successful, start your response with 'Here are all the warehouses in Snowflake:'"
    )

    assert (
        "here are all the warehouses in snowflake" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ list_warehouses passed.")


@pytest.mark.asyncio
async def test_execute_query(client):
    """Execute a SQL query on Snowflake.

    Verifies that the query is executed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the execute_query tool to execute the query 'INSERT INTO {TABLE_NAME} (id, name, email) VALUES (1, 'John Doe', 'john.doe@example.com')'. using the warehouse {WAREHOUSE_NAME} in the database {DB_NAME}."
        "If successful, start your response with 'data inserted successfully' and then list the table name in format 'Table: <table_name>'."
    )

    assert (
        "data inserted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ execute_query passed.")
