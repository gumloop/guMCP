import pytest
import uuid

# Global variables to store created IDs
created_order_id = None
created_plan_id = None
created_product_id = None
created_subscription_id = None


@pytest.mark.asyncio
async def test_create_product(client):
    """Create a new PayPal product.

    Verifies that the product is created successfully.
    Stores the created product ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_product_id

    name = "Test Product " + str(uuid.uuid4())
    description = (
        "This is a test product created by the test_create_product tool in guMCP."
    )
    product_type = "PHYSICAL"

    response = await client.process_query(
        f"Use the create_product tool to create a new product with name {name}, "
        f"description {description}, and type {product_type}. If successful, start your response with "
        "'Created PayPal product successfully' and then list the product ID in format 'ID: <product_id>'."
    )

    assert (
        "created paypal product successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_product"

    # Extract product ID from response
    try:
        created_product_id = response.split("ID: ")[1].split()[0]
        print(f"Created product ID: {created_product_id}")
    except IndexError:
        pytest.fail("Could not extract product ID from response")

    print(f"Response: {response}")
    print("✅ create_product passed.")


@pytest.mark.asyncio
async def test_create_plan(client):
    """Create a new PayPal billing plan.

    Verifies that the plan is created successfully.
    Stores the created plan ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_plan_id

    if not created_product_id:
        pytest.skip("No product ID available - run create_product test first")

    name = "Test Plan " + str(uuid.uuid4())
    description = "This is a test plan created by the test_create_plan tool in guMCP."
    billing_cycles = [
        {
            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
            "tenure_type": "REGULAR",
            "sequence": 1,
            "total_cycles": 12,
            "pricing_scheme": {
                "fixed_price": {"value": "10.00", "currency_code": "USD"}
            },
        }
    ]
    payment_preferences = {
        "auto_bill_outstanding": True,
        "payment_failure_threshold": 3,
    }

    response = await client.process_query(
        f"Use the create_plan tool to create a new plan with product_id {created_product_id}, "
        f"name {name}, description {description}, billing_cycles {billing_cycles}, and "
        f"payment_preferences {payment_preferences}. If successful, start your response with "
        "'Created PayPal plan successfully' and then list the plan ID in format 'ID: <plan_id>'."
    )

    assert (
        "created paypal plan successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_plan"

    # Extract plan ID from response
    try:
        created_plan_id = response.split("ID: ")[1].split()[0]
        print(f"Created plan ID: {created_plan_id}")
    except IndexError:
        pytest.fail("Could not extract plan ID from response")

    print(f"Response: {response}")
    print("✅ create_plan passed.")


@pytest.mark.asyncio
async def test_create_order(client):
    """Create a new PayPal order.

    Verifies that the order is created successfully.
    Stores the created order ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_order_id

    intent = "CAPTURE"
    purchase_units = [
        {
            "amount": {"currency_code": "USD", "value": "10.00"},
            "description": "Test order created by guMCP",
        }
    ]

    response = await client.process_query(
        f"Use the create_order tool to create a new order with intent {intent} and "
        f"purchase_units {purchase_units}. If successful, start your response with "
        "'Created PayPal order successfully' and then list the order ID in format 'ID: <order_id>'."
    )

    assert (
        "created paypal order successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_order"

    # Extract order ID from response
    try:
        created_order_id = response.split("ID: ")[1].split()[0]
        print(f"Created order ID: {created_order_id}")
    except IndexError:
        pytest.fail("Could not extract order ID from response")

    print(f"Response: {response}")
    print("✅ create_order passed.")


@pytest.mark.asyncio
async def test_create_subscription(client):
    """Create a new PayPal subscription.

    Verifies that the subscription is created successfully.
    Stores the created subscription ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_subscription_id

    if not created_plan_id:
        pytest.skip("No plan ID available - run create_plan test first")

    subscriber = {
        "name": {"given_name": "Test", "surname": "User"},
        "email_address": "test@example.com",
    }

    response = await client.process_query(
        f"Use the create_subscription tool to create a new subscription with plan_id {created_plan_id} "
        f"and subscriber {subscriber}. If successful, start your response with "
        "'Created PayPal subscription successfully' and then list the subscription ID in format 'ID: <subscription_id>'."
    )

    assert (
        "created paypal subscription successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_subscription"

    # Extract subscription ID from response
    try:
        created_subscription_id = response.split("ID: ")[1].split()[0]
        print(f"Created subscription ID: {created_subscription_id}")
    except IndexError:
        pytest.fail("Could not extract subscription ID from response")

    print(f"Response: {response}")
    print("✅ create_subscription passed.")


@pytest.mark.asyncio
async def test_get_order(client):
    """Get details for a PayPal order.

    Verifies that the order details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_order_id:
        pytest.skip("No order ID available - run create_order test first")

    response = await client.process_query(
        f"Use the get_order tool to fetch details for order ID {created_order_id}. "
        "If successful, start your response with 'Here are the PayPal order details' and then list them."
    )

    assert (
        "here are the paypal order details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_order"

    print(f"Response: {response}")
    print("✅ get_order passed.")


@pytest.mark.asyncio
async def test_get_plan(client):
    """Get details for a PayPal plan.

    Verifies that the plan details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_plan_id:
        pytest.skip("No plan ID available - run create_plan test first")

    response = await client.process_query(
        f"Use the get_plan tool to fetch details for plan ID {created_plan_id}. "
        "If successful, start your response with 'Here are the PayPal plan details' and then list them."
    )

    assert (
        "here are the paypal plan details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_plan"

    print(f"Response: {response}")
    print("✅ get_plan passed.")


@pytest.mark.asyncio
async def test_get_product(client):
    """Get details for a PayPal product.

    Verifies that the product details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_product_id:
        pytest.skip("No product ID available - run create_product test first")

    response = await client.process_query(
        f"Use the get_product tool to fetch details for product ID {created_product_id}. "
        "If successful, start your response with 'Here are the PayPal product details' and then list them."
    )

    assert (
        "here are the paypal product details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_product"

    print(f"Response: {response}")
    print("✅ get_product passed.")


@pytest.mark.asyncio
async def test_get_subscription(client):
    """Get details for a PayPal subscription.

    Verifies that the subscription details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_subscription_id:
        pytest.skip("No subscription ID available - run create_subscription test first")

    response = await client.process_query(
        f"Use the get_subscription tool to fetch details for subscription ID {created_subscription_id}. "
        "If successful, start your response with 'Here are the PayPal subscription details' and then list them."
    )

    assert (
        "here are the paypal subscription details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_subscription"

    print(f"Response: {response}")
    print("✅ get_subscription passed.")


@pytest.mark.asyncio
async def test_update_product(client):
    """Update a PayPal product.

    Verifies that the product is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_product_id:
        pytest.skip("No product ID available - run create_product test first")

    new_description = "This is an updated description for the test product."

    response = await client.process_query(
        f"Use the update_product tool to update product ID {created_product_id} with "
        f"path 'description' and value '{new_description}'. If successful, start your response with "
        "'Updated PayPal product successfully'."
    )

    assert (
        "updated paypal product successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_product"

    print(f"Response: {response}")
    print("✅ update_product passed.")


@pytest.mark.asyncio
async def test_update_plan(client):
    """Update a PayPal plan.

    Verifies that the plan is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_plan_id:
        pytest.skip("No plan ID available - run create_plan test first")

    new_description = "This is an updated description for the test plan."

    response = await client.process_query(
        f"Use the update_plan tool to update plan ID {created_plan_id} with "
        f"path 'description' and value '{new_description}'. If successful, start your response with "
        "'Updated PayPal plan successfully'."
    )

    assert (
        "updated paypal plan successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_plan"

    print(f"Response: {response}")
    print("✅ update_plan passed.")


@pytest.mark.asyncio
async def test_deactivate_plan(client):
    """Deactivate a PayPal plan.

    Verifies that the plan is deactivated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_plan_id:
        pytest.skip("No plan ID available - run create_plan test first")

    response = await client.process_query(
        f"Use the deactivate_plan tool to deactivate plan ID {created_plan_id}. "
        "If successful, start your response with 'Deactivated PayPal plan successfully'."
    )

    assert (
        "deactivated paypal plan successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from deactivate_plan"

    print(f"Response: {response}")
    print("✅ deactivate_plan passed.")


@pytest.mark.asyncio
async def test_list_plans(client):
    """List PayPal billing plans.

    Verifies that plans can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_plans tool to fetch a list of plans. "
        "If successful, start your response with 'Here are the PayPal plans' and then list them."
    )

    assert (
        "here are the paypal plans" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_plans"

    print(f"Response: {response}")
    print("✅ list_plans passed.")


@pytest.mark.asyncio
async def test_activate_plan(client):
    """Activate a PayPal plan.

    Verifies that the plan is activated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_plan_id:
        pytest.skip("No plan ID available - run create_plan test first")

    response = await client.process_query(
        f"Use the activate_plan tool to activate plan ID {created_plan_id}. "
        "If successful, start your response with 'Activated PayPal plan successfully'."
    )

    assert (
        "activated paypal plan successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from activate_plan"

    print(f"Response: {response}")
    print("✅ activate_plan passed.")


@pytest.mark.asyncio
async def test_list_products(client):
    """List PayPal products.

    Verifies that products can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_products tool to fetch a list of products. "
        "If successful, start your response with 'Here are the PayPal products' and then list them."
    )

    assert (
        "here are the paypal products" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_products"

    print(f"Response: {response}")
    print("✅ list_products passed.")


@pytest.mark.asyncio
async def test_search_invoices(client):
    """Search PayPal invoices.

    Verifies that invoices can be searched successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the search_invoices tool to search for invoices. "
        "If successful , start your response with 'Successfully fetched <count> invoices'"
    )

    assert (
        "successfully fetched" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from search_invoices"

    print(f"Response: {response}")
    print("✅ search_invoices passed.")


@pytest.mark.asyncio
async def test_confirm_order(client):
    """Confirm a PayPal order.

    Verifies that the order is confirmed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_order_id:
        pytest.skip("No order ID available - run create_order test first")

    payment_source = {
        "paypal": {
            "name": "Test User",
            "email_address": "test@example.com",
            "experience_context": {
                "payment_method_id": "paypal",
                "payment_method_type": "paypal",
                "payment_method_details": {"paypal": {"account_id": "1234567890"}},
            },
        }
    }

    response = await client.process_query(
        f"Use the confirm_order tool to confirm order ID {created_order_id} with "
        f"payment_source {payment_source}. If successful, start your response with "
        "'Confirmed PayPal order successfully'."
    )

    assert (
        "confirmed paypal order successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from confirm_order"

    print(f"Response: {response}")
    print("✅ confirm_order passed.")
