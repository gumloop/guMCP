import re
import uuid
from typing import Any

import pytest

from tests.utils.test_tools import get_test_id, run_resources_test, run_tool_test


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

    # Add support for extracting amount values
    if key_phrase == "amount":
        amount_pattern = r"\b(\d+\.\d{2})\b"
        matches = list(re.finditer(amount_pattern, response))
        if matches:
            return matches[0].group(1)

    # Add support for extracting gateway values
    if key_phrase == "gateway":
        gateway_pattern = r"[\"'](\w+)[\"']"
        matches = list(re.finditer(gateway_pattern, response))
        if matches:
            return matches[0].group(1)

    if key_phrase == "parent_id":
        parent_id_pattern = r"[\"'](\d+)[\"']"
        matches = list(re.finditer(parent_id_pattern, response))
        if matches:
            return matches[0].group(1)

    return None


# Shared context dictionary
SHARED_CONTEXT: dict[str, Any] = {}

# Static test inputs - Please update these with valid values for your test environment
TEST_INPUTS = {
    "test_email": "test@example.com",
    "test_phone": "+1234567890",
    "test_order_number": "#1001",
    "test_customer_id": "1234567890",
    "test_order_id_to_cancel": "1234567890",
    "test_order_id_to_calculate_refund": "1234567890",
    "test_line_item_id_to_calculate_refund": "1234567890",
}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


# Define tool tests
TOOL_TESTS = [
    {
        "name": "get_shop_details",
        "args": "",
        "expected_keywords": ["shop_id"],
        "regex_extractors": {
            "shop_id": r'"?shop_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Get shop details and return shop ID",
    },
    {
        "name": "create_product",
        "args_template": 'with title="Test Product {random_id}"',
        "expected_keywords": ["product_id"],
        "regex_extractors": {
            "product_id": r'"?product_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Create a test product and return its ID",
        "setup": lambda context: {"random_id": uuid.uuid4().hex[:8]},
    },
    {
        "name": "get_products",
        "args": "",
        "expected_keywords": ["product_id"],
        "regex_extractors": {
            "listed_product_id": r'"?product_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "List products and return a product ID",
    },
    {
        "name": "get_product",
        "args_template": 'with product_id="{product_id}"',
        "expected_keywords": ["product_details", "variant_id"],
        "regex_extractors": {
            "variant_id": r'"?variant_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Get product details by ID",
        "depends_on": ["product_id"],
    },
    {
        "name": "get_variant_inventory_item",
        "args_template": 'with variant_id="{variant_id}"',
        "expected_keywords": ["inventory_item_id"],
        "regex_extractors": {
            "inventory_item_id": r'"?inventory_item_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Get inventory item ID for variant",
        "depends_on": ["variant_id"],
    },
    {
        "name": "update_inventory_tracking",
        "args_template": 'with inventory_item_id="{inventory_item_id}" tracked=true',
        "expected_keywords": ["tracking_enabled"],
        "description": "Enable inventory tracking",
        "depends_on": ["inventory_item_id"],
    },
    {
        "name": "delete_product",
        "args_template": 'with id="{product_id}"',
        "expected_keywords": ["product_id"],
        "description": "Delete the test product",
        "depends_on": ["product_id"],
    },
    {
        "name": "get_order_by_number",
        "args": 'with name="#1001"',  # This should be a valid order number in test environment
        "expected_keywords": ["order_id", "line_item_id"],
        "regex_extractors": {
            "order_id": r'"?order_id"?[:\s]+"?([^"]+)"?',
            "line_item_id": r"gid://shopify/LineItem/(\d+)",  # Updated to extract first line item ID
        },
        "description": "Get order details by number",
    },
    {
        "name": "calculate_refund",
        "args_template": f'with orderId="{TEST_INPUTS["test_order_id_to_calculate_refund"]}" lineItemId="{TEST_INPUTS["test_line_item_id_to_calculate_refund"]}" restockType="NO_RESTOCK"',
        "expected_keywords": ["amount", "gateway"],
        "regex_extractors": {
            "refund_amount": r'"?amount"?[:\s]+"?([^"]+)"?',
            "gateway": r'"?gateway"?[:\s]+"?([^"]+)"?',
        },
        "description": "Calculate refund for order line item",
    },
    {
        "name": "get_locations",
        "args": "",
        "expected_keywords": ["location_id"],
        "regex_extractors": {
            "location_id": r'"?location_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Get first location ID",
    },
    {
        "name": "create_refund",
        "args_template": 'with orderId="{order_id}" lineItemId="{line_item_id}" restockType="NO_RESTOCK" amount="{refund_amount}" gateway="{gateway}" note="Test refund" transactionKind="REFUND" transactionParentId="{parent_id}"',
        "expected_keywords": ["refund_id"],
        "regex_extractors": {
            "refund_id": r'"?refund_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Create refund for order line item",
        "depends_on": [
            "order_id",
            "line_item_id",
            "refund_amount",
            "gateway",
            "parent_id",
        ],
    },
    {
        "name": "get_contact_by_email",
        "args": f'with email="{TEST_INPUTS["test_email"]}"',
        "expected_keywords": ["id", "firstName", "lastName", "email"],
        "regex_extractors": {
            "customer_id": r'"?customer_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Get customer details by email",
    },
    {
        "name": "get_contact_by_phone",
        "args": f'with phone="{TEST_INPUTS["test_phone"]}"',
        "expected_keywords": ["id", "firstName", "lastName", "phone"],
        "regex_extractors": {
            "customer_id": r'"?customer_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Get customer details by phone",
    },
    {
        "name": "get_contact_by_id",
        "args_template": f'with id="{TEST_INPUTS["test_customer_id"]}"',
        "expected_keywords": [
            "id",
            "firstName",
            "lastName",
            "email",
            "phone",
            "defaultAddress",
        ],
        "description": "Get detailed customer information by ID",
    },
    {
        "name": "get_order_by_number",
        "args": f'with name="{TEST_INPUTS["test_order_number"]}"',
        "expected_keywords": [
            "id",
            "name",
            "confirmationNumber",
            "displayFulfillmentStatus",
            "totalPriceSet",
        ],
        "regex_extractors": {
            "order_id": r'"?order_id"?[:\s]+"?([^"]+)"?',
            "test_customer_id": r'"?customer_id"?[:\s]+"?([^"]+)"?',
        },
        "description": "Get order details by order number",
    },
    {
        "name": "get_recent_orders",
        "args_template": f'with limit=5 customer_id="{TEST_INPUTS["test_customer_id"]}"',
        "expected_keywords": [
            "edges",
            "node",
            "name",
            "confirmationNumber",
            "displayFulfillmentStatus",
        ],
        "description": "Get recent orders for a customer",
    },
    {
        "name": "cancel_order",
        "args_template": f'with id="{TEST_INPUTS["test_order_id_to_cancel"]}" refund=true restock=true staffNote="Test cancellation" reason="CUSTOMER"',
        "expected_keywords": ["userErrors"],
        "description": "Cancel an order",
    },
]


# Test resources
@pytest.mark.asyncio
async def test_resources(client, context):
    """Test listing and reading resources"""
    response = await run_resources_test(client)
    if response and response.resources:
        context["first_resource_uri"] = response.resources[0].uri
    return response


# Test tools
@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_tool(client, context, test_config):
    """Test individual tools using configuration"""
    return await run_tool_test(client, context, test_config)
