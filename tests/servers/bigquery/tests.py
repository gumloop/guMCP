import pytest
import uuid

# Test constants
DATASET_ID = "test_dataset_" + str(uuid.uuid4())[:8]
TABLE_ID = "test_table_" + str(uuid.uuid4())[:8]
PROJECT_ID = None  # Will use default project


@pytest.mark.asyncio
async def test_run_query(client):
    response = await client.process_query(
        "Use the run_query tool to execute a simple query: SELECT 1 as test_value"
    )
    assert (
        "test_value" in response.lower()
    ), f"Expected test_value in response: {response}"
    assert response, "No response returned from run_query"
    print(f"Response: {response}")
    print("✅ run_query passed.")


@pytest.mark.asyncio
async def test_list_datasets(client):
    response = await client.process_query(
        "Use the list_datasets tool to list all available datasets"
    )
    assert "datasets" in response.lower(), f"Expected datasets in response: {response}"
    assert response, "No response returned from list_datasets"
    print(f"Response: {response}")
    print("✅ list_datasets passed.")


@pytest.mark.asyncio
async def test_get_dataset_info(client):
    # First create a dataset to get info about
    create_response = await client.process_query(
        f"Use the run_query tool to create a dataset: CREATE SCHEMA IF NOT EXISTS {DATASET_ID}"
    )
    assert (
        "success" in create_response.lower()
    ), f"Failed to create dataset: {create_response}"

    response = await client.process_query(
        f"Use the get_dataset_info tool to get information about dataset {DATASET_ID}"
    )
    assert DATASET_ID in response, f"Expected dataset ID in response: {response}"
    assert response, "No response returned from get_dataset_info"
    print(f"Response: {response}")
    print("✅ get_dataset_info passed.")


@pytest.mark.asyncio
async def test_list_tables(client):
    # First create a table to list
    create_response = await client.process_query(
        f"Use the run_query tool to create a table: CREATE TABLE IF NOT EXISTS {DATASET_ID}.{TABLE_ID} (id INT64, name STRING)"
    )
    assert (
        "success" in create_response.lower()
    ), f"Failed to create table: {create_response}"

    response = await client.process_query(
        f"Use the list_tables tool to list tables in dataset {DATASET_ID}"
    )
    assert TABLE_ID in response, f"Expected table ID in response: {response}"
    assert response, "No response returned from list_tables"
    print(f"Response: {response}")
    print("✅ list_tables passed.")


@pytest.mark.asyncio
async def test_get_table_schema(client):
    response = await client.process_query(
        f"Use the get_table_schema tool to get schema for table {TABLE_ID} in dataset {DATASET_ID}"
    )
    assert "schema" in response.lower(), f"Expected schema in response: {response}"
    assert response, "No response returned from get_table_schema"
    print(f"Response: {response}")
    print("✅ get_table_schema passed.")


@pytest.mark.asyncio
async def test_preview_table_data(client):
    # First insert some data to preview
    insert_response = await client.process_query(
        f"Use the run_query tool to insert data: INSERT INTO {DATASET_ID}.{TABLE_ID} (id, name) VALUES (1, 'test')"
    )
    assert (
        "success" in insert_response.lower()
    ), f"Failed to insert data: {insert_response}"

    response = await client.process_query(
        f"Use the preview_table_data tool to preview data from table {TABLE_ID} in dataset {DATASET_ID}"
    )
    assert "preview" in response.lower(), f"Expected preview in response: {response}"
    assert response, "No response returned from preview_table_data"
    print(f"Response: {response}")
    print("✅ preview_table_data passed.")


@pytest.mark.asyncio
async def test_cleanup(client):
    # Clean up test resources
    cleanup_response = await client.process_query(
        f"Use the run_query tool to drop the test table: DROP TABLE IF EXISTS {DATASET_ID}.{TABLE_ID}"
    )
    assert (
        "success" in cleanup_response.lower()
    ), f"Failed to drop table: {cleanup_response}"

    cleanup_response = await client.process_query(
        f"Use the run_query tool to drop the test dataset: DROP SCHEMA IF EXISTS {DATASET_ID}"
    )
    assert (
        "success" in cleanup_response.lower()
    ), f"Failed to drop dataset: {cleanup_response}"
    print("✅ cleanup passed.")
