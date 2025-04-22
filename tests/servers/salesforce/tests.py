import pytest
import uuid

# Global variables to store created record IDs
created_account_id = None
created_contact_id = None


@pytest.mark.asyncio
async def test_soql_query(client):
    """Execute a SOQL query to retrieve Salesforce records.

    Verifies that query results are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    query = "SELECT Id, Name FROM Account LIMIT 5"

    response = await client.process_query(
        f"Use the soql_query tool to execute this SOQL query: '{query}'. "
        "If successful, start your response with 'Here are the query results' and then show them."
    )

    assert (
        "here are the query results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from soql_query"

    print(f"Response: {response}")
    print("✅ soql_query passed.")


@pytest.mark.asyncio
async def test_sosl_search(client):
    """Perform a text-based search across multiple Salesforce objects using SOSL.

    Verifies that search results are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    search = "FIND {Test} IN ALL FIELDS RETURNING Account, Contact"

    response = await client.process_query(
        f"Use the sosl_search tool to execute this SOSL search: '{search}'. "
        "If successful, start your response with 'Here are the search results' and then show them."
    )

    assert (
        "here are the search results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from sosl_search"

    print(f"Response: {response}")
    print("✅ sosl_search passed.")


@pytest.mark.asyncio
async def test_describe_object(client):
    """Retrieve detailed metadata about a Salesforce object.

    Verifies that object metadata is returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    object_name = "Account"

    response = await client.process_query(
        f"Use the describe_object tool to get metadata for the '{object_name}' object. "
        "If successful, start your response with 'Here is the object metadata' and then show the details."
    )

    assert (
        "here is the object metadata" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from describe_object"

    print(f"Response: {response}")
    print("✅ describe_object passed.")


@pytest.mark.asyncio
async def test_create_account(client):
    """Create a new Account record in Salesforce.

    Verifies that the record is created successfully.
    Stores the created record ID for use in subsequent tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_account_id
    name = f"Test Account {str(uuid.uuid4())[:8]}"
    industry = "Technology"

    response = await client.process_query(
        f"""Use the create_record tool to create a new Account with these details:
        - Name: {name}
        - Industry: {industry}
        If successful, start your response with 'Created account successfully' and include the record ID.
        Return account id in format ID: <id>"""
    )

    assert (
        "created account successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_record"

    # Extract record ID from response
    try:
        created_account_id = response.split("ID: ")[1].split()[0]
    except Exception:
        pytest.fail("Could not extract account ID from response")

    print(f"Response: {response}")
    print("✅ create_account passed.")


@pytest.mark.asyncio
async def test_get_record(client):
    """Retrieve a specific Salesforce record by ID.

    Verifies that the record details are returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_account_id:
        pytest.skip("No account ID available - run create_account test first")

    response = await client.process_query(
        f"""Use the get_record tool to retrieve the Account with ID {created_account_id}.
        If successful, start your response with 'Here are the account details' and show the details."""
    )

    assert (
        "here are the account details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_record"

    print(f"Response: {response}")
    print("✅ get_record passed.")


@pytest.mark.asyncio
async def test_create_contact(client):
    """Create a new Contact record related to the test Account.

    Verifies that the record is created successfully.
    Stores the created record ID for use in subsequent tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_contact_id, created_account_id

    if not created_account_id:
        pytest.skip("No account ID available - run create_account test first")

    first_name = "Test"
    last_name = f"Contact {str(uuid.uuid4())[:8]}"
    email = f"test.{last_name.lower().replace(' ', '.')}@example.com"

    response = await client.process_query(
        f"""Use the create_record tool to create a new Contact with these details:
        - FirstName: {first_name}
        - LastName: {last_name}
        - Email: {email}
        - AccountId: {created_account_id}
        If successful, start your response with 'Created contact successfully' and include the record ID.
        Your response for contact id should be ID: <id>"""
    )

    assert (
        "created contact successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_record"

    try:
        created_contact_id = response.split("ID: ")[1].split()[0]
        print(f"Created contact ID: {created_contact_id}")
    except Exception:
        pytest.fail("Could not extract contact ID from response")

    print(f"Response: {response}")
    print("✅ create_contact passed.")


@pytest.mark.asyncio
async def test_update_record(client):
    """Update an existing Account record in Salesforce.

    Verifies that the record is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_account_id:
        pytest.skip("No account ID available - run create_account test first")

    description = f"Updated description as of {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the update_record tool to update the Account with ID {created_account_id}.
        Add a Description field with value: "{description}"
        If successful, start your response with 'Updated account successfully'."""
    )

    assert (
        "updated account successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_record"

    print(f"Response: {response}")
    print("✅ update_record passed.")


@pytest.mark.asyncio
async def test_get_org_limits(client):
    """Retrieve current organization limits and usage.

    Verifies that the limits data is returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        """Use the get_org_limits tool to retrieve the current Salesforce org limits.
        If successful, start your response with 'Here are the organization limits' and show the details."""
    )

    assert (
        "here are the organization limits" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_org_limits"

    print(f"Response: {response}")
    print("✅ get_org_limits passed.")


@pytest.mark.asyncio
async def test_get_specific_limit(client):
    """Retrieve a specific organization limit.

    Verifies that the specific limit data is returned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    limit_type = "DailyApiRequests"

    response = await client.process_query(
        f"""Use the get_org_limits tool to retrieve the '{limit_type}' limit specifically.
        If successful, start your response with 'Here is the specific limit' and show the details."""
    )

    assert (
        "here is the specific limit" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_org_limits"

    print(f"Response: {response}")
    print("✅ get_specific_limit passed.")


@pytest.mark.asyncio
async def test_delete_record(client):
    """Delete the test Contact record.

    Verifies that the record is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_id:
        pytest.skip("No contact ID available - run create_contact test first")

    response = await client.process_query(
        f"""Use the delete_record tool to delete the Contact with ID {created_contact_id}.
        If successful, start your response with 'Deleted contact successfully'."""
    )

    assert (
        "deleted contact successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_record"

    print(f"Response: {response}")
    print("✅ delete_contact passed.")


@pytest.mark.asyncio
async def test_delete_account(client):
    """Delete the test Account record.

    Verifies that the record is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_account_id:
        pytest.skip("No account ID available - run create_account test first")

    response = await client.process_query(
        f"""Use the delete_record tool to delete the Account with ID {created_account_id}.
        If successful, start your response with 'Deleted account successfully'."""
    )

    assert (
        "deleted account successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_record"

    print(f"Response: {response}")
    print("✅ delete_account passed.")
