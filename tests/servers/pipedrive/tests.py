import pytest
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test

# Test get user
# You can only test get user if you have a user id
user_id = ""  # TODO: Add user id

TOOL_TESTS = [
    # Create Operations
    {
        "name": "create_organization",
        "args_template": 'with name="Test Organization"',
        "expected_keywords": ["id", "name"],
        "regex_extractors": {"org_id": r'"?id"?[:\s]+(\d+)'},
        "description": "create a new organization in Pipedrive",
    },
    {
        "name": "create_person",
        "args_template": 'with name="Test Person"',
        "expected_keywords": ["id", "name"],
        "regex_extractors": {"person_id": r'"?id"?[:\s]+(\d+)'},
        "description": "create a new person in Pipedrive",
    },
    {
        "name": "create_deal",
        "args_template": 'with title="Test Deal" value=1000 currency="USD"',
        "expected_keywords": ["deal_id", "title"],
        "regex_extractors": {"deal_id": r'"?deal_id"?[:\s]+(\d+)'},
        "description": "create a new deal in Pipedrive",
    },
    {
        "name": "create_lead",
        "args_template": 'with title="Test Lead"',
        "expected_keywords": ["lead_id", "title"],
        "regex_extractors": {"lead_id": r'"?lead_id"?[:\s]+"?([^",}]+)"?'},
        "description": "create a new lead in Pipedrive",
    },
    {
        "name": "create_product",
        "args_template": 'with name="Test Product" code="TEST-001" unit="kg" prices=["price": 100, "currency": "USD"]',
        "expected_keywords": ["product_id", "name"],
        "regex_extractors": {"product_id": r'"?product_id"?[:\s]+(\d+)'},
        "description": "create a new product in Pipedrive",
    },
    {
        "name": "create_activity",
        "args_template": 'with subject="Test Activity" type="task" due_date="2024-12-31"',
        "expected_keywords": ["activity_id", "subject"],
        "regex_extractors": {"activity_id": r'"?activity_id"?[:\s]+(\d+)'},
        "description": "create a new activity in Pipedrive",
    },
    {
        "name": "create_note",
        "args_template": 'with content="Test Note" and organization_id={org_id}',
        "expected_keywords": ["id", "content"],
        "regex_extractors": {"note_id": r'"?id"?[:\s]+(\d+)'},
        "description": "create a new note in Pipedrive",
    },
    # Read Operations
    {
        "name": "get_all_users",
        "args_template": "",
        "expected_keywords": ["id", "name"],
        "description": "get all users from Pipedrive",
    },
    {
        "name": "get_organization",
        "args_template": 'with organization_id="{org_id}"',
        "expected_keywords": ["id", "name"],
        "description": "get a specific organization from Pipedrive",
        "depends_on": ["org_id"],
    },
    {
        "name": "get_person",
        "args_template": 'with person_id="{person_id}"',
        "expected_keywords": ["id", "name"],
        "description": "get a specific person from Pipedrive",
        "depends_on": ["person_id"],
    },
    {
        "name": "get_deal",
        "args_template": 'with deal_id="{deal_id}"',
        "expected_keywords": ["id", "title"],
        "description": "get a specific deal from Pipedrive",
        "depends_on": ["deal_id"],
    },
    {
        "name": "get_lead",
        "args_template": 'with lead_id="{lead_id}"',
        "expected_keywords": ["id", "title"],
        "description": "get a specific lead from Pipedrive",
        "depends_on": ["lead_id"],
    },
    {
        "name": "get_product",
        "args_template": 'with product_id="{product_id}"',
        "expected_keywords": ["id", "name"],
        "description": "get a specific product from Pipedrive",
        "depends_on": ["product_id"],
    },
    {
        "name": "get_activity",
        "args_template": 'with activity_id="{activity_id}"',
        "expected_keywords": ["id", "subject"],
        "description": "get a specific activity from Pipedrive",
        "depends_on": ["activity_id"],
    },
    {
        "name": "get_note",
        "args_template": 'with note_id="{note_id}"',
        "expected_keywords": ["id", "content"],
        "description": "get a specific note from Pipedrive",
        "depends_on": ["note_id"],
    },
    # Update Operations
    {
        "name": "update_organization",
        "args_template": 'with organization_id="{org_id}" name="Updated Organization"',
        "expected_keywords": ["id", "name"],
        "description": "update an organization in Pipedrive",
        "depends_on": ["org_id"],
    },
    {
        "name": "update_person",
        "args_template": 'with person_id="{person_id}" name="Updated Person"',
        "expected_keywords": ["id", "name"],
        "description": "update a person in Pipedrive",
        "depends_on": ["person_id"],
    },
    {
        "name": "update_deal",
        "args_template": 'with deal_id="{deal_id}" title="Updated Deal"',
        "expected_keywords": ["id", "title"],
        "description": "update a deal in Pipedrive",
        "depends_on": ["deal_id"],
    },
    {
        "name": "update_product",
        "args_template": 'with product_id="{product_id}" name="Updated Product"',
        "expected_keywords": ["id", "name"],
        "description": "update a product in Pipedrive",
        "depends_on": ["product_id"],
    },
    {
        "name": "update_activity",
        "args_template": 'with activity_id="{activity_id}" subject="Updated Activity"',
        "expected_keywords": ["id", "subject"],
        "description": "update an activity in Pipedrive",
        "depends_on": ["activity_id"],
    },
    {
        "name": "update_note",
        "args_template": 'with note_id="{note_id}" content="Updated Note"',
        "expected_keywords": ["id", "content"],
        "description": "update a note in Pipedrive",
        "depends_on": ["note_id"],
    },
    # Delete Operations
    {
        "name": "delete_organization",
        "args_template": 'with organization_id="{org_id}"',
        "expected_keywords": ["success"],
        "description": "delete an organization from Pipedrive",
        "depends_on": ["org_id"],
    },
    {
        "name": "delete_person",
        "args_template": 'with person_id="{person_id}"',
        "expected_keywords": ["success"],
        "description": "delete a person from Pipedrive",
        "depends_on": ["person_id"],
    },
    {
        "name": "delete_deal",
        "args_template": 'with deal_id="{deal_id}"',
        "expected_keywords": ["success"],
        "description": "delete a deal from Pipedrive",
        "depends_on": ["deal_id"],
    },
    {
        "name": "delete_lead",
        "args_template": 'with lead_id="{lead_id}"',
        "expected_keywords": ["success"],
        "description": "delete a lead from Pipedrive",
        "depends_on": ["lead_id"],
    },
    {
        "name": "delete_product",
        "args_template": 'with product_id="{product_id}"',
        "expected_keywords": ["success"],
        "description": "delete a product from Pipedrive",
        "depends_on": ["product_id"],
    },
    {
        "name": "delete_activity",
        "args_template": 'with activity_id="{activity_id}"',
        "expected_keywords": ["success"],
        "description": "delete an activity from Pipedrive",
        "depends_on": ["activity_id"],
    },
    {
        "name": "delete_note",
        "args_template": 'with note_id="{note_id}"',
        "expected_keywords": ["success"],
        "description": "delete a note from Pipedrive",
        "depends_on": ["note_id"],
    },
    # Get User Operation
    {
        "name": "get_user",
        "args_template": 'with user_id="{user_id}"',
        "expected_keywords": ["success"],
        "description": "get a specific user from Pipedrive",
        "depends_on": ["user_id"],
    },
    # Get All Operations
    {
        "name": "get_all_deals",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all deals from Pipedrive",
    },
    {
        "name": "get_all_activities",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all activities from Pipedrive",
    },
    {
        "name": "get_all_leads",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all leads from Pipedrive",
    },
    {
        "name": "get_all_notes",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all notes from Pipedrive",
    },
    {
        "name": "get_all_persons",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all persons from Pipedrive",
    },
    {
        "name": "get_all_organizations",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all organizations from Pipedrive",
    },
    {
        "name": "get_all_products",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all products from Pipedrive",
    },
    {
        "name": "get_all_users",
        "args_template": "",
        "expected_keywords": ["success"],
        "description": "get all users from Pipedrive",
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {"user_id": user_id}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_pipedrive_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response
