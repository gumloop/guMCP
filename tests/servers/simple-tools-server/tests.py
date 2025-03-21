import pytest


@pytest.mark.asyncio
async def test_store_data(client):
    """Test the store-data tool"""
    key = "test_key"
    value = "test_value"

    response = await client.process_query(f"Store the key '{key}' with value '{value}'")

    # Simple verification: check if both key and value appear in the response
    assert key in response, f"Key '{key}' not found in response: {response}"
    assert value in response, f"Value '{value}' not found in response: {response}"
    print(f"✅ Data stored successfully: {key}={value}")


@pytest.mark.asyncio
async def test_retrieve_existing_data(client):
    """Test retrieving existing data"""
    key = "test_key"
    expected = "test_value"

    # First store the data
    await client.process_query(f"Store the key '{key}' with value '{expected}'")

    # Then retrieve it
    response = await client.process_query(f"Get the value for key '{key}'")

    assert (
        expected in response
    ), f"Expected value '{expected}' not found in response: {response}"
    print(f"✅ Retrieved existing data: {key}={expected}")


@pytest.mark.asyncio
async def test_retrieve_nonexistent_data(client):
    """Test retrieving non-existent data"""
    key = "non_existent_key"

    response = await client.process_query(
        f"Get the value for key '{key}'. Respond with 'not found' if it couldn't be found."
    )

    assert (
        "not found" in response.lower()
    ), f"Expected 'not found' message, got: {response}"
    print(f"✅ Correctly handled non-existent key: {key}")


@pytest.mark.asyncio
async def test_list_data_initial(client):
    """Test listing data (initial)"""
    response = await client.process_query(
        "List all stored data. Please include the phrase 'Here is the stored data' in your response, "
        "or 'No data stored' if empty. Make sure to clearly show all keys and values."
    )

    assert (
        "stored data" in response.lower() or "no data stored" in response.lower()
    ), f"Expected data listing confirmation, got: {response}"
    print("✅ Initial data list returned successfully")


@pytest.mark.asyncio
async def test_store_additional_data(client):
    """Test storing additional data"""
    key = "another_key"
    value = "another_value"

    response = await client.process_query(
        f"Store the key '{key}' with value '{value}'. When successful, please respond with "
        f"'Successfully stored the key {key} with value {value}' and confirm the storage was completed."
    )

    assert key in response, f"Key '{key}' not found in response: {response}"
    assert value in response, f"Value '{value}' not found in response: {response}"
    print(f"✅ Additional data stored successfully: {key}={value}")


@pytest.mark.asyncio
async def test_list_data_updated(client):
    """Test listing data after adding more entries"""
    response = await client.process_query(
        "List all stored data. Begin your response with 'Here is the stored data:' and make sure "
        "to include all keys and values in a clear format. Ensure both test_key and another_key are visible."
    )

    assert (
        "stored data" in response.lower()
    ), f"Expected 'stored data' confirmation, got: {response}"
    assert "test_key" in response, f"Expected test_key in data listing, got: {response}"
    assert (
        "another_key" in response
    ), f"Expected another_key in data listing, got: {response}"
    print("✅ Updated data list returned successfully with multiple entries")
