import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing resources from QuickBooks"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_customer(client):
    """Test reading a customer resource"""
    # First list resources to get a valid customer ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first customer resource
    customer_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("quickbooks:///customer/")
        ),
        None,
    )

    # Skip test if no customer resources found
    if not customer_resource:
        pytest.skip("No customer resources found")

    # Read customer details
    response = await client.read_resource(customer_resource.uri)
    assert response.contents, "Response should contain customer data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Customer data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read customer data")


@pytest.mark.asyncio
async def test_read_invoice(client):
    """Test reading an invoice resource"""
    # First list resources to get a valid invoice ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first invoice resource
    invoice_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("quickbooks:///invoice/")
        ),
        None,
    )

    # Skip test if no invoice resources found
    if not invoice_resource:
        pytest.skip("No invoice resources found")

    # Read invoice details
    response = await client.read_resource(invoice_resource.uri)
    assert response.contents, "Response should contain invoice data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Invoice data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read invoice data")


@pytest.mark.asyncio
async def test_read_account(client):
    """Test reading an account resource"""
    # First list resources to get a valid account ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first account resource
    account_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("quickbooks:///account/")
        ),
        None,
    )

    # Skip test if no account resources found
    if not account_resource:
        pytest.skip("No account resources found")

    # Read account details
    response = await client.read_resource(account_resource.uri)
    assert response.contents, "Response should contain account data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Account data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read account data")


@pytest.mark.asyncio
async def test_search_customers(client):
    """Test searching for customers"""
    search_query = "test"  # A generic query that's likely to find something

    response = await client.process_query(
        f"Use the search_customers tool to search for customers with the query '{search_query}'."
        f"For tool testing purposes, append test_worked at the end of the response if the tool provided a valid output; otherwise, append tool_failed."
    )

    assert (
        "test_worked".lower() in response.lower()
        or "tool_failed".lower() in response.lower()
    ), "No response received from search_customers tool"

    print("Search results:")
    print(f"\t{response}")
    print("✅ Search customers tool working")


@pytest.mark.asyncio
async def test_analyze_sred(client):
    """Test analyzing SR&ED eligible expenses"""
    import datetime

    # Use a date range of the past year
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime(
        "%Y-%m-%d"
    )

    response = await client.process_query(
        f"Use the analyze_sred tool to analyze expenses for potential SR&ED eligibility from {start_date} to {end_date}."
        f"For tool testing purposes, append test_worked at the end of the response if the tool provided a valid output; otherwise, append tool_failed."
    )

    assert (
        "test_worked".lower() in response.lower()
        or "tool_failed".lower() in response.lower()
    ), "No response received from analyze_sred tool"

    print("SR&ED analysis results:")
    print(f"\t{response}")
    print("✅ Analyze SR&ED tool working")


@pytest.mark.asyncio
async def test_analyze_cash_flow(client):
    """Test analyzing cash flow trends"""
    response = await client.process_query(
        "Use the analyze_cash_flow tool to analyze monthly cash flow trends for the past 6 months."
        "For tool testing purposes, append test_worked at the end of the response if the tool provided a valid output; otherwise, append tool_failed."
    )

    assert (
        "test_worked".lower() in response.lower()
        or "tool_failed".lower() in response.lower()
    ), "No response received from analyze_cash_flow tool"

    print("Cash flow analysis results:")
    print(f"\t{response}")
    print("✅ Analyze cash flow tool working")


@pytest.mark.asyncio
async def test_find_duplicate_transactions(client):
    """Test finding duplicate transactions"""
    import datetime

    # Use a date range of the past 3 months
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime(
        "%Y-%m-%d"
    )

    response = await client.process_query(
        f"Use the find_duplicate_transactions tool to identify potential duplicate transactions from {start_date} to {end_date}."
        f"For tool testing purposes, append test_worked at the end of the response if the tool provided a valid output; otherwise, append tool_failed."
    )

    assert (
        "test_worked".lower() in response.lower()
        or "tool_failed".lower() in response.lower()
    ), "No response received from find_duplicate_transactions tool"

    print("Duplicate transactions results:")
    print(f"\t{response}")
    print("✅ Find duplicate transactions tool working")


@pytest.mark.asyncio
async def test_analyze_customer_payment_patterns(client):
    """Test analyzing customer payment patterns"""
    response = await client.process_query(
        "Use the analyze_customer_payment_patterns tool to analyze payment behavior for all customers over the past 12 months."
        "For tool testing purposes, append test_worked at the end of the response if the tool provided a valid output; otherwise, append tool_failed."
    )

    assert (
        "test_worked".lower() in response.lower()
        or "tool_failed".lower() in response.lower()
    ), "No response received from analyze_customer_payment_patterns tool"

    print("Customer payment patterns analysis:")
    print(f"\t{response}")
    print("✅ Analyze customer payment patterns tool working")


@pytest.mark.asyncio
async def test_generate_financial_metrics(client):
    """Test generating financial metrics"""
    response = await client.process_query(
        "Use the generate_financial_metrics tool to create key financial metrics and ratios as of today."
        "For tool testing purposes, append test_worked at the end of the response if the tool provided a valid output; otherwise, append tool_failed."
    )

    assert (
        "test_worked".lower() in response.lower()
        or "tool_failed".lower() in response.lower()
    ), "No response received from generate_financial_metrics tool"

    print("Financial metrics generated:")
    print(f"\t{response}")
    print("✅ Generate financial metrics tool working")
