import pytest
import uuid
import re


def extract_result(response, key_phrase):
    """Extract result from response using regex to handle variations in AI output"""
    pattern = rf"{key_phrase}:\s*([^\n]+)"
    match = re.search(pattern, response, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    if key_phrase.endswith("_id"):
        gid_pattern = r"gid://shopify/\w+/(\d+)"
        gid_match = re.search(gid_pattern, response)
        if gid_match:
            resource_type = key_phrase.split("_")[0].capitalize()
            return f"gid://shopify/{resource_type}/{gid_match.group(1)}"

        numeric_pattern = r"[\"']?([\d]+)[\"']?"
        numeric_match = re.search(numeric_pattern, response)
        if numeric_match:
            resource_type = key_phrase.split("_")[0].capitalize()
            return f"gid://shopify/{resource_type}/{numeric_match.group(1)}"

    if (
        key_phrase.endswith("_count")
        or key_phrase == "count"
        or key_phrase == "available"
    ):
        count_pattern = r"\b(\d+)\b"
        matches = list(re.finditer(count_pattern, response))
        if matches:
            return matches[0].group(1)

    return None


@pytest.mark.asyncio
async def test_get_shop_details(client):
    """Test getting the Shopify shop details"""
    response = await client.process_query(
        "Use the get_shop_details tool to retrieve information about the shop."
        "Return the shop ID with keyword 'shop_id' if successful or error with keyword 'error_message'."
        "Sample response: shop_id: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to get shop details: {response}")

    shop_id = extract_result(response, "shop_id")
    assert shop_id, "Shop ID not found in response"

    return shop_id


@pytest.mark.asyncio
async def test_product_flow(client):
    """Test creating a product in Shopify"""

    unique_title = f"Test Product {uuid.uuid4().hex[:8]}"

    response = await client.process_query(
        f"Use the create_product tool to create a product in Shopify with the following details:\n"
        f"- title: '{unique_title}'\n"
        f"Return the product ID with keyword 'product_id' if successful or error with keyword 'error_message'."
    )

    if "error_message" in response:
        pytest.fail(f"Failed to create product: {response}")

    products_response = await client.process_query(
        f"Use the get_products tool to retrieve all products in Shopify."
        f"Return any one product ID from the list of products with keyword 'product_id' if successful or error with keyword 'error_message'."
    )

    if "error_message" in products_response:
        pytest.fail(f"Failed to get products: {products_response}")

    product_id = extract_result(products_response, "product_id")
    assert product_id, "Product ID not found in response"

    product_response = await client.process_query(
        f"Use the get_product tool to retrieve the product with ID: {product_id}."
        f"Return the product details with keyword 'product_details' if successful or error with keyword 'error_message'."
    )

    if "error_message" in product_response:
        pytest.fail(f"Failed to get product: {product_response}")

    product_details = extract_result(product_response, "product_details")
    assert product_details, "Product details not found in response"

    delete_product_response = await client.process_query(
        f"Use the delete_product tool to delete the product with ID: {product_id}."
        f"Return the product ID with keyword 'product_id' if successful or error with keyword 'error_message'."
    )

    if "error_message" in delete_product_response:
        pytest.fail(f"Failed to delete product: {delete_product_response}")

    delete_product_id = extract_result(delete_product_response, "product_id")
    assert delete_product_id, "Product ID not found in response"


@pytest.mark.asyncio
async def test_inventory_flow(client):
    """Test inventory flow"""

    # Create product
    create_product_response = await client.process_query(
        f"Use the create_product tool to create a product in Shopify with the following details:\n"
        f"- title: 'Inventory Test Product {uuid.uuid4().hex[:6]}'\n"
        f"Return the product ID with keyword 'product_id' if successful or error with keyword 'error_message'."
    )

    if "error_message" in create_product_response:
        pytest.fail(f"Failed to create product: {create_product_response}")

    product_id = extract_result(create_product_response, "product_id")
    assert product_id, "Product ID not found in create response"

    get_product_response = await client.process_query(
        f"Use the get_product tool to retrieve the product with ID: {product_id}.\n"
        f"Return the first variant ID with keyword 'variant_id' if successful or error with keyword 'error_message'."
    )

    if "error_message" in get_product_response:
        pytest.fail(f"Failed to get product: {get_product_response}")

    variant_id = extract_result(get_product_response, "variant_id")
    assert variant_id, "Variant ID not found in response"

    get_variant_response = await client.process_query(
        f"Use the get_variant_inventory_item tool to retrieve the inventory item ID for the variant with ID: {variant_id}.\n"
        f"Return the inventory item ID with keyword 'inventory_item_id' if successful or error with keyword 'error_message'."
    )

    if "error_message" in get_variant_response:
        pytest.fail(f"Failed to get variant inventory item: {get_variant_response}")

    inventory_item_id = extract_result(get_variant_response, "inventory_item_id")
    assert inventory_item_id, "Inventory item ID not found in response"

    enable_tracking_response = await client.process_query(
        f"Use the update_inventory_tracking tool to enable inventory tracking for the inventory item with ID: {inventory_item_id}.\n"
        f"Set tracked to true.\n"
        f"Return 'tracking_enabled: true' if successful or error with keyword 'error_message'."
    )

    print(f"Enable tracking response: {enable_tracking_response}")

    if "error_message" in enable_tracking_response:
        pytest.fail(f"Failed to enable inventory tracking: {enable_tracking_response}")

    print(f"✅ Inventory flow completed successfully")
