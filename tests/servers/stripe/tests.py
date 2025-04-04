import uuid
import pytest
import re


def extract_id(text: str, prefix: str) -> str | None:
    """Extract a Stripe ID from LLM response text.

    Args:
        text: The response text from the LLM
        prefix: The Stripe ID prefix to find (e.g. 'cus_', 'prod_', 'price_')

    Returns:
        The extracted ID or None if not found

    Examples:
        - extract_id(text, "cus_") -> finds customer IDs like "cus_123abc"
        - extract_id(text, "prod_") -> finds product IDs like "prod_456def"
    """
    match = re.search(rf"{prefix}[a-zA-Z0-9_]+", text)
    return match.group(0) if match else None


@pytest.mark.asyncio
async def test_list_customers(client):
    response = await client.process_query(
        "Use the list_customers tool to get all customers. If successful, start with 'CUSTOMERS_LISTED:'"
    )
    assert "CUSTOMERS_LISTED:" in response or "CUSTOMER" in response
    print(f"Response: {response}")
    print("✅ Customers listed")


@pytest.mark.asyncio
async def test_retrieve_balance(client):
    response = await client.process_query(
        "Use the retrieve_balance tool to check the account balance. If successful, start with 'BALANCE_RETRIEVED:'"
    )
    assert "BALANCE_RETRIEVED:" in response or "available" in response.lower()
    print(f"Response: {response}")
    print("✅ Balance retrieved")


@pytest.mark.asyncio
async def test_list_subscriptions(client):
    response = await client.process_query(
        "Use the list_subscriptions tool to get all subscriptions. If successful, start with 'SUBSCRIPTIONS_LISTED:'"
    )
    assert "SUBSCRIPTIONS_LISTED:" in response or "subscription" in response.lower()
    print(f"Response: {response}")
    print("✅ Subscriptions listed")


@pytest.mark.asyncio
async def test_create_payment_intent(client):
    """Test creating a payment intent in Stripe."""
    response = await client.process_query(
        "Use the create_payment_intent tool to create a payment intent with amount 5000 and currency 'usd'. "
        "If successful, start your response with 'PAYMENT_INTENT_CREATED:' followed by the payment intent ID."
    )
    match = re.search(r"PAYMENT_INTENT_CREATED:\s*(\w+)", response)
    assert match, f"Payment intent creation failed: {response}"
    print(f"Response: {response}")
    print("✅ Payment intent creation successful")


@pytest.mark.asyncio
async def test_update_subscription(client):
    """Test updating a Stripe subscription."""
    email = f"update_sub_{uuid.uuid4().hex[:6]}@example.com"
    prod_name = f"UpdateSub Product {uuid.uuid4().hex[:6]}"

    # Step 1: Create customer with test card token
    cust_res = await client.process_query(
        f"Use the create_customer tool to create a customer with email '{email}' "
        f"and source='tok_visa'. If successful, start with 'CUSTOMER_CREATED:'"
    )
    customer_id = extract_id(cust_res, "cus_")
    assert customer_id, f"Customer creation failed: {cust_res}"
    print(f"Response: {cust_res}")

    # Step 2: Create product
    prod_res = await client.process_query(
        f"Create a product named '{prod_name}'. If successful, start with 'PRODUCT_CREATED:'"
    )
    product_id = extract_id(prod_res, "prod_")
    assert product_id, f"Product creation failed: {prod_res}"
    print(f"Response: {prod_res}")

    # Step 3: Create recurring price
    price_res = await client.process_query(
        f"Create a recurring monthly price for product {product_id} with 4000 cents in 'usd'. If successful, start with 'PRICE_CREATED:'"
    )
    price_id = extract_id(price_res, "price_")
    assert price_id, f"Price creation failed: {price_res}"
    print(f"Response: {price_res}")

    # Step 4: Create subscription
    sub_res = await client.process_query(
        f"Create a subscription for customer {customer_id} and price {price_id}. If successful, start with 'SUBSCRIPTION_CREATED:'"
    )
    subscription_id = extract_id(sub_res, "sub_")
    assert subscription_id, f"Subscription creation failed: {sub_res}"
    print(f"Response: {sub_res}")

    # Step 5: Update subscription
    update_res = await client.process_query(
        f"Update the subscription with ID {subscription_id}. Add metadata: purpose = 'test-update'. "
        f"If successful, start with 'SUBSCRIPTION_UPDATED:'"
    )
    assert (
        extract_id(update_res, "sub_") == subscription_id
    ), f"Subscription update failed: {update_res}"
    print(f"Response: {update_res}")
    print(f"✅ Subscription {subscription_id} updated successfully")


@pytest.mark.asyncio
async def test_list_payment_intents(client):
    response = await client.process_query(
        "Use the list_payment_intents tool to list all payment intents. If successful, start with 'PAYMENT_INTENTS_LISTED:'"
    )
    assert "PAYMENT_INTENTS_LISTED:" in response or "payment_intent" in response.lower()
    print(f"Response: {response}")
    print("✅ Payment intents listed")


@pytest.mark.asyncio
async def test_list_charges(client):
    response = await client.process_query(
        "Use the list_charges tool to list all charges. If successful, start with 'CHARGES_LISTED:'"
    )
    assert "CHARGES_LISTED:" in response or "charge" in response.lower()
    print(f"Response: {response}")
    print("✅ Charges listed")


@pytest.mark.asyncio
async def test_create_customer(client):
    """Test creating a Stripe customer."""
    email = f"create_{uuid.uuid4().hex[:6]}@example.com"
    response = await client.process_query(
        f"Use the create_customer tool to create a customer with email {email}. "
        "If successful, start with 'CUSTOMER_CREATED:'"
    )

    # Safety fallback if response is None or empty
    assert response, "No response returned from process_query"
    assert "CUSTOMER_CREATED:" in response, f"Customer creation failed: {response}"
    print(f"Response: {response}")
    print("✅ Customer created")


@pytest.mark.asyncio
async def test_create_invoice(client):
    """Test creating a draft invoice for a Stripe customer."""
    email = f"invoice_{uuid.uuid4().hex[:6]}@example.com"

    # Step 1: Create customer
    cust_res = await client.process_query(
        f"Use the create_customer tool to create a customer with email '{email}'. "
        "If successful, start with 'CUSTOMER_CREATED:' followed by the customer ID only."
    )
    customer_id = extract_id(cust_res, "cus_")
    assert customer_id, f"Invalid customer ID: {cust_res}"
    print(f"Response: {cust_res}")

    # Step 2: Create invoice for that customer
    invoice_res = await client.process_query(
        f"Use the create_invoice tool to create a draft invoice for customer ID {customer_id}. "
        "If successful, start with 'INVOICE_CREATED:' followed by the invoice ID only."
    )
    invoice_id = extract_id(invoice_res, "in_")
    assert invoice_id, f"Invoice creation failed: {invoice_res}"
    print(f"Response: {invoice_res}")
    print(f"✅ Invoice created: {invoice_id}")


@pytest.mark.asyncio
async def test_list_invoices(client):
    """Test listing all Stripe invoices."""
    response = await client.process_query(
        "Use the list_invoices tool to get all invoices. If successful, start with 'INVOICES_LISTED:'"
    )

    # Validate response presence and content
    assert response, "No response returned from process_query"
    assert "INVOICES_LISTED:" in response, f"Invoices not listed properly: {response}"
    print(f"Response: {response}")
    print("✅ Invoices listed successfully")


@pytest.mark.asyncio
async def test_retrieve_customer(client):
    """Test retrieving the first listed customer."""

    # Step 1: List customers
    list_res = await client.process_query(
        "Use the list_customers tool to fetch existing customers. If successful, start with 'CUSTOMERS_LISTED:' and include their IDs."
    )
    customer_id = extract_id(list_res, "cus_")
    assert customer_id, f"No valid customer ID found in list: {list_res}"
    print(f"Response: {list_res}")

    # Step 2: Retrieve that customer
    retrieve_res = await client.process_query(
        f"Use the retrieve_customer tool to get info for customer ID {customer_id}. If successful, start with 'CUSTOMER_INFO:'"
    )
    assert extract_id(
        retrieve_res, "cus_"
    ), f"Failed to retrieve customer: {retrieve_res}"
    print(f"Response: {retrieve_res}")
    print(f"✅ Retrieved customer {customer_id}")


@pytest.mark.asyncio
async def test_create_product(client):
    """Test creating a new Stripe product."""
    name = f"Product {uuid.uuid4().hex[:6]}"
    response = await client.process_query(
        f"Use the create_product tool to create product '{name}'. If successful, start with 'PRODUCT_CREATED:'"
    )

    # Defensive check
    assert response, "No response returned from process_query"
    assert "PRODUCT_CREATED:" in response, f"Product creation failed: {response}"
    print(f"Response: {response}")
    print("✅ Product created successfully")


@pytest.mark.asyncio
async def test_confirm_payment_intent(client):
    """Test confirming a payment intent created just before confirmation."""

    # Step 1: Create a payment intent
    create_response = await client.process_query(
        "Use the create_payment_intent tool to create a payment intent for 5000 cents in USD. "
        "If successful, start with 'PAYMENT_INTENT_CREATED:' followed by the payment intent ID."
    )
    payment_intent_id = extract_id(create_response, "pi_")
    assert payment_intent_id, f"Payment intent creation failed: {create_response}"
    print(f"Response: {create_response}")

    # Step 2: Confirm the payment intent
    confirm_response = await client.process_query(
        f"Use the confirm_payment_intent tool to confirm payment intent ID {payment_intent_id}. "
        "If successful, start with 'PAYMENT_CONFIRMED:'"
    )
    assert extract_id(
        confirm_response, "pi_"
    ), f"Confirmation failed: {confirm_response}"
    print(f"Response: {confirm_response}")
    print(f"✅ Confirmed payment intent {payment_intent_id}")


@pytest.mark.asyncio
async def test_list_products(client):
    """Test listing all Stripe products."""
    response = await client.process_query(
        "Use the list_products tool to get all products. If successful, start with 'PRODUCTS_LISTED:'"
    )

    assert response, "No response returned from process_query"
    assert "PRODUCTS_LISTED:" in response, f"Product listing failed: {response}"
    print(f"Response: {response}")
    print("✅ Products listed successfully")


@pytest.mark.asyncio
async def test_cancel_subscription(client):
    """Test canceling a subscription after creating customer, product, and price."""
    email = f"cancel_{uuid.uuid4().hex[:6]}@example.com"
    product_name = f"Cancel Product {uuid.uuid4().hex[:6]}"

    # Step 1: Create customer with test card token
    cust_res = await client.process_query(
        f"Use the create_customer tool to create a customer with email '{email}' "
        f"and source='tok_visa'. If successful, start with 'CUSTOMER_CREATED:' followed by the ID only."
    )
    customer_id = extract_id(cust_res, "cus_")
    assert customer_id, f"Invalid customer ID: {cust_res}"
    print(f"Response: {cust_res}")

    # Step 2: Create product
    prod_res = await client.process_query(
        f"Use the create_product tool to create a product named '{product_name}'. "
        "If successful, start with 'PRODUCT_CREATED:' followed by the ID only."
    )
    product_id = extract_id(prod_res, "prod_")
    assert product_id, f"Invalid product ID: {prod_res}"
    print(f"Response: {prod_res}")

    # Step 3: Create recurring price
    price_res = await client.process_query(
        f"Use the create_price tool to create a recurring monthly price for product {product_id} "
        "with unit_amount 6000 and currency 'usd'. If successful, start with 'PRICE_CREATED:' followed by the ID only."
    )
    price_id = extract_id(price_res, "price_")
    assert price_id, f"Invalid price ID: {price_res}"
    print(f"Response: {price_res}")

    # Step 4: Create subscription
    sub_res = await client.process_query(
        f"Use the create_subscription tool to create a subscription for customer {customer_id} "
        f"with price ID {price_id}. If successful, start with 'SUBSCRIPTION_CREATED:' followed by the ID only."
    )
    subscription_id = extract_id(sub_res, "sub_")
    assert subscription_id, f"Subscription creation failed: {sub_res}"
    print(f"Response: {sub_res}")

    # Step 5: Cancel subscription
    cancel_res = await client.process_query(
        f"Use the cancel_subscription tool to cancel subscription ID {subscription_id}. "
        "If successful, start with 'SUBSCRIPTION_CANCELLED:' followed by the ID only."
    )
    assert (
        extract_id(cancel_res, "sub_") == subscription_id
    ), f"Cancel failed: {cancel_res}"
    print(f"Response: {cancel_res}")
    print("✅ Subscription cancelled successfully")


@pytest.mark.asyncio
async def test_retrieve_subscription(client):
    """Test retrieving a subscription by listing first and then fetching it."""
    # Step 1: List subscriptions
    list_res = await client.process_query(
        "List all Stripe subscriptions. If successful, start your response with 'SUBSCRIPTIONS_LIST:' and include subscription IDs."
    )
    sub_id = extract_id(list_res, "sub_")
    assert "SUBSCRIPTIONS_LIST:" in list_res, f"Subscription list failed: {list_res}"
    print(f"Response: {list_res}")

    # Step 2: Retrieve subscription
    retrieve_res = await client.process_query(
        f"Use the retrieve_subscription tool to get details of subscription ID {sub_id}. "
        f"If successful, start your response with 'SUBSCRIPTION_RETRIEVED:'"
    )
    assert "SUBSCRIPTION_RETRIEVED:" in retrieve_res, f"Retrieve failed: {retrieve_res}"
    print(f"Response: {retrieve_res}")
    print("✅ Subscription retrieve via listing successful")


@pytest.mark.asyncio
async def test_create_price(client):
    """Test creating a price for a product in Stripe."""
    product_res = await client.process_query(
        "Create a product named 'Test Priceable'. If successful, start with 'PRODUCT_CREATED:'"
    )
    product_id = extract_id(product_res, "prod_")
    assert product_id, f"Product creation failed: {product_res}"
    print(f"Response: {product_res}")

    price_res = await client.process_query(
        f"Create a recurring monthly price for product {product_id} with unit_amount 2000 and currency 'usd'. "
        "If successful, start with 'PRICE_CREATED:'"
    )
    assert extract_id(price_res, "price_"), f"Price creation failed: {price_res}"
    print(f"Response: {price_res}")
    print("✅ Price creation successful")


@pytest.mark.asyncio
async def test_create_subscription(client):
    """Test creating a subscription with valid customer and recurring price."""
    email = f"sub_create_{uuid.uuid4().hex[:6]}@example.com"
    product_name = f"Product {uuid.uuid4().hex[:6]}"

    # Step 1: Create customer with test card token
    cust_res = await client.process_query(
        f"Use the create_customer tool to create a customer with email '{email}' "
        f"and source='tok_visa'. If successful, start the response with 'CUSTOMER_CREATED:' followed by the ID only."
    )
    customer_id = extract_id(cust_res, "cus_")
    assert customer_id, f"Invalid customer ID: {cust_res}"
    print(f"Response: {cust_res}")

    # Step 2: Create product
    prod_res = await client.process_query(
        f"Use the create_product tool to create a product named '{product_name}'. "
        "If successful, start the response with 'PRODUCT_CREATED:' followed by the ID only."
    )
    product_id = extract_id(prod_res, "prod_")
    assert product_id, f"Invalid product ID: {prod_res}"
    print(f"Response: {prod_res}")

    # Step 3: Create recurring price
    price_res = await client.process_query(
        f"Use the create_price tool to create a recurring monthly price for product {product_id} "
        "with unit_amount 800 and currency 'usd'. If successful, start with 'PRICE_CREATED:' followed by the ID only."
    )
    price_id = extract_id(price_res, "price_")
    assert price_id, f"Invalid price ID: {price_res}"
    print(f"Response: {price_res}")

    # Step 4: Create subscription
    sub_res = await client.process_query(
        f"Use the create_subscription tool to create a subscription for customer {customer_id} "
        f"with price ID {price_id}. If successful, start with 'SUBSCRIPTION_CREATED:' followed by the ID only."
    )
    subscription_id = extract_id(sub_res, "sub_")
    assert subscription_id, f"Subscription creation failed: {sub_res}"
    print(f"Response: {sub_res}")
    print("✅ Subscription created successfully")


@pytest.mark.asyncio
async def test_update_customer(client):
    """Test creating and updating a Stripe customer."""
    email = f"update_{uuid.uuid4().hex[:6]}@example.com"
    new_name = f"Updated User {uuid.uuid4().hex[:4]}"

    # Create customer first
    response = await client.process_query(
        f"Use the create_customer tool to create a customer with email {email}. "
        "If successful, only respond with 'CUSTOMER_CREATED:' followed by the customer ID."
    )
    customer_id = extract_id(response, "cus_")
    assert customer_id, f"Customer creation failed: {response}"

    # Update the customer with new name
    update_response = await client.process_query(
        f"Use the update_customer tool to update the customer with ID {customer_id}. "
        f"Set the name to '{new_name}'. If successful, only respond with 'CUSTOMER_UPDATED:'"
    )
    assert extract_id(
        update_response, "cus_"
    ), f"Customer update failed: {update_response}"
    print(f"Response: {update_response}")
    print(f"✅ Customer {customer_id} updated with name: {new_name}")
