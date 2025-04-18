import pytest
import uuid

DB_NAME = "TEST_DB_" + str(uuid.uuid4())[:8]
TABLE_NAME = "TEST_TABLE_" + str(uuid.uuid4())[:8]
WAREHOUSE_NAME = "TEST_WAREHOUSE_" + str(uuid.uuid4())[:8]
SCHEMA_NAME = "PUBLIC"


@pytest.mark.asyncio
async def test_create_database(client):
    response = await client.process_query(
        f"Use the create_database tool to create a new database with name {DB_NAME}."
        " If successful, respond with 'Database created successfully' followed by 'Database: <database_name>'."
    )
    assert (
        "database created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_database"
    print(f"Response: {response}")
    print("✅ create_database passed.")


@pytest.mark.asyncio
async def test_create_table(client):
    response = await client.process_query(
        f"Use the create_table tool to create a new table with name {TABLE_NAME} in the database {DB_NAME} and schema {SCHEMA_NAME}."
        " The table should have columns: id INT, name STRING, email STRING."
        " If successful, respond with 'Table created successfully' followed by 'Table: <table_name>'."
    )
    assert (
        "table created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_table"
    print(f"Response: {response}")
    print("✅ create_table passed.")


@pytest.mark.asyncio
async def test_list_tables(client):
    response = await client.process_query(
        f"Use the list_tables tool to list all tables in the database {DB_NAME}."
        " If successful, respond with 'Here are all the tables in the database <database_name>:'"
    )
    assert (
        "here are all the tables in the database" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_tables"
    print(f"Response: {response}")
    print("✅ list_tables passed.")


@pytest.mark.asyncio
async def test_describe_table(client):
    response = await client.process_query(
        f"Use the describe_table tool to describe the table {TABLE_NAME} in the database {DB_NAME} and schema {SCHEMA_NAME}."
        " If successful, respond with 'Here is the description of the table <table_name>:'"
    )
    assert (
        "here is the description of the table" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from describe_table"
    print(f"Response: {response}")
    print("✅ describe_table passed.")


@pytest.mark.asyncio
async def test_create_warehouse(client):
    response = await client.process_query(
        f"Use the create_warehouse tool to create a new warehouse with name {WAREHOUSE_NAME}."
        " If successful, respond with 'Warehouse created successfully' followed by 'Warehouse: <warehouse_name>'."
    )
    assert (
        "warehouse created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_warehouse"
    print(f"Response: {response}")
    print("✅ create_warehouse passed.")


@pytest.mark.asyncio
async def test_list_warehouses(client):
    response = await client.process_query(
        "Use the list_warehouses tool to list all warehouses in Snowflake."
        " If successful, respond with 'Here are all the warehouses in Snowflake:'"
    )
    assert (
        "here are all the warehouses in snowflake" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_warehouses"
    print(f"Response: {response}")
    print("✅ list_warehouses passed.")


@pytest.mark.asyncio
async def test_execute_query(client):
    response = await client.process_query(
        f"Use the execute_query tool to run the query: INSERT INTO {TABLE_NAME} (id, name, email) VALUES (1, 'John Doe', 'john.doe@example.com')"
        f" in the database {DB_NAME}."
        " If successful, respond with 'Data inserted successfully' followed by 'Table: <table_name>'."
    )
    assert (
        "data inserted successfully" in response.lower()
        or "query executed successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from execute_query"
    print(f"Response: {response}")
    print("✅ execute_query passed.")


@pytest.mark.asyncio
async def test_list_databases(client):
    response = await client.process_query(
        "Use the list_databases tool to list all databases in Snowflake."
        " If successful, respond with 'Here are all the databases in Snowflake:'"
    )
    assert (
        "here are all the databases in snowflake" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_databases"
    print(f"Response: {response}")
    print("✅ list_databases passed.")
