import uuid
import pytest
import time
import random
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


# Shared context dictionary at module level
SHARED_CONTEXT = {}

TOOL_TESTS = [
    {
        "name": "list_contacts",
        "args_template": 'with query="*@example.com" limit=3 properties=["email", "firstname", "lastname", "company"]',
        "expected_keywords": ["contact_id"],
        "regex_extractors": {"contact_id": r"contact_id:\s*(\d+)"},
        "description": "list HubSpot contacts with a search query and extract a contact ID",
    },
    {
        "name": "create_contact",
        "args_template": 'with email="test{random_id}@example.com" firstname="Test" lastname="User {random_id}" company="Test Company" jobtitle="QA Tester"',
        "expected_keywords": ["created_contact_id"],
        "regex_extractors": {"created_contact_id": r"created_contact_id:\s*(\d+)"},
        "description": "create a new HubSpot contact and return its created_contact_id",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_contact",
        "args_template": 'with contact_id="{created_contact_id}" company="Updated Company {random_id}" jobtitle="Senior QA Engineer"',
        "expected_keywords": ["updated_contact_id"],
        "regex_extractors": {"updated_contact_id": r"updated_contact_id:\s*(\d+)"},
        "description": "update an existing HubSpot contact",
        "depends_on": ["created_contact_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "search_contacts",
        "args_template": 'with filter_property="email" filter_operator="EQ" filter_value="testadfa5ffa@example.com"',
        "expected_keywords": ["found_contact_id"],
        "regex_extractors": {"found_contact_id": r"found_contact_id:\s*(\d+)"},
        "description": "search for HubSpot contacts with specific criteria",
    },
    {
        "name": "list_companies",
        "args_template": 'with limit=5 properties=["name", "domain", "industry"]',
        "expected_keywords": ["company_id"],
        "regex_extractors": {"company_id": r"company_id:\s*(\d+)"},
        "description": "list HubSpot companies and extract a company ID",
    },
    {
        "name": "create_company",
        "args_template": 'with name="Test Company {random_id}" domain="test-company-{random_id}.com" industry="COMPUTER_SOFTWARE" city="Test City" country="Test Country"',
        "expected_keywords": ["created_company_id"],
        "regex_extractors": {"created_company_id": r"created_company_id:\s*(\d+)"},
        "description": "create a new HubSpot company and return its ID",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_company",
        "args_template": 'with company_id="{created_company_id}" description="Updated description {random_id}" industry="COMPUTER_SOFTWARE"',
        "expected_keywords": ["updated_company_id"],
        "regex_extractors": {"updated_company_id": r"updated_company_id:\s*(\d+)"},
        "description": "update an existing HubSpot company",
        "depends_on": ["created_company_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "list_deals",
        "args_template": 'with limit=5 properties=["dealname", "amount", "dealstage"]',
        "expected_keywords": ["deal_id"],
        "regex_extractors": {"deal_id": r"deal_id:\s*(\d+)"},
        "description": "list HubSpot deals and extract a deal ID",
    },
    {
        "name": "create_deal",
        "args_template": 'with dealname="Test Deal {random_id}" amount=5000',
        "expected_keywords": ["created_deal_id"],
        "regex_extractors": {"created_deal_id": r"created_deal_id:\s*(\d+)"},
        "description": "create a new HubSpot deal and return its ID",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_deal",
        "args_template": 'with deal_id="{created_deal_id}" amount=7500 dealstage="qualifiedtobuy"',
        "expected_keywords": ["updated_deal_id"],
        "regex_extractors": {"updated_deal_id": r"updated_deal_id:\s*(\d+)"},
        "description": "update an existing HubSpot deal",
        "depends_on": ["created_deal_id"],
    },
    {
        "name": "get_engagements",
        "args_template": 'with contact_id="{created_contact_id}" limit=10',
        "expected_keywords": ["total", "results"],
        "description": "get engagement data for a HubSpot contact",
        "depends_on": ["created_contact_id"],
    },
    {
        "name": "send_email",
        "args_template": 'with contact_id="{created_contact_id}" subject="Test Email {random_id}" body="This is a test email from the HubSpot integration tests."',
        "expected_keywords": ["_status_code"],
        "description": "send an email to a HubSpot contact",
        "depends_on": ["created_contact_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_ticket",
        "args_template": 'with subject="Test Ticket {random_id}" content="This is a test ticket." hs_ticket_priority="MEDIUM" hs_pipeline_stage="1"',
        "expected_keywords": ["created_ticket_id"],
        "regex_extractors": {"created_ticket_id": r"created_ticket_id:\s*(\d+)"},
        "description": "create a new HubSpot ticket",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "list_tickets",
        "args_template": 'with limit=5 properties=["subject", "content", "hs_ticket_priority"]',
        "expected_keywords": ["ticket_id"],
        "regex_extractors": {"ticket_id": r"ticket_id:\s*(\d+)"},
        "description": "list HubSpot tickets and return any one of the ticket ids",
    },
    {
        "name": "get_ticket",
        "args_template": 'with ticket_id="{created_ticket_id}" properties=["subject", "content", "hs_ticket_priority"]',
        "expected_keywords": ["ticket_id"],
        "regex_extractors": {"ticket_id": r"ticket_id:\s*(\d+)"},
        "description": "get details for a specific HubSpot ticket and return the ticket id",
        "depends_on": ["created_ticket_id"],
    },
    {
        "name": "update_ticket",
        "args_template": 'with ticket_id="{created_ticket_id}" subject="Updated Ticket {random_id}" hs_ticket_priority="HIGH"',
        "expected_keywords": ["updated_ticket_id"],
        "regex_extractors": {"updated_ticket_id": r"updated_ticket_id:\s*(\d+)"},
        "description": "update an existing HubSpot ticket",
        "depends_on": ["created_ticket_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_ticket",
        "args_template": 'with subject="Duplicate Ticket {random_id}" content="This ticket will be merged." hs_pipeline_stage="1"',
        "expected_keywords": ["duplicate_ticket_id"],
        "regex_extractors": {"duplicate_ticket_id": r"duplicate_ticket_id:\s*(\d+)"},
        "description": "create a duplicate ticket with subject, content, and hs_pipeline_stage parameters for testing merge",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "merge_tickets",
        "args_template": 'with primary_ticket_id="{created_ticket_id}" secondary_ticket_id="{duplicate_ticket_id}"',
        "expected_keywords": ["id"],
        "description": "merge two HubSpot tickets",
        "depends_on": ["created_ticket_id", "duplicate_ticket_id"],
    },
    {
        "name": "delete_ticket",
        "args_template": 'with ticket_id="{created_ticket_id}"',
        "expected_keywords": ["status_code"],
        "description": "delete a HubSpot ticket",
        "depends_on": ["created_ticket_id"],
    },
    {
        "name": "list_products",
        "args_template": 'with limit=5 properties=["name", "description", "price"]',
        "expected_keywords": ["product_id"],
        "regex_extractors": {"product_id": r"product_id:\s*(\d+)"},
        "description": "list HubSpot products and extract a product ID",
    },
    {
        "name": "create_product",
        "args_template": 'with name="Test Product {random_id}" description="This is a test product" price=99.99 hs_sku="SKU-{random_id}"',
        "expected_keywords": ["created_product_id"],
        "regex_extractors": {"created_product_id": r"created_product_id:\s*(\d+)"},
        "description": "create a new HubSpot product and return its ID",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "get_product",
        "args_template": 'with product_id="{created_product_id}" properties=["name", "description", "price", "hs_sku"]',
        "expected_keywords": ["product_id"],
        "regex_extractors": {"product_id": r"product_id:\s*(\d+)"},
        "description": "get details for a specific HubSpot product and return the product id",
        "depends_on": ["created_product_id"],
    },
    {
        "name": "update_product",
        "args_template": 'with product_id="{created_product_id}" name="Updated Product {random_id}" price=129.99',
        "expected_keywords": ["updated_product_id"],
        "regex_extractors": {"updated_product_id": r"updated_product_id:\s*(\d+)"},
        "description": "update an existing HubSpot product",
        "depends_on": ["created_product_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "delete_product",
        "args_template": 'with product_id="{created_product_id}"',
        "expected_keywords": ["status_code"],
        "description": "delete a HubSpot product",
        "depends_on": ["created_product_id"],
    },
    {
        "name": "create_engagement",
        "args_template": 'with type="NOTE" metadata_body="Test engagement note {random_id}" timestamp={timestamp} contact_ids=["{created_contact_id}"]',
        "expected_keywords": ["created_engagement_id"],
        "regex_extractors": {
            "created_engagement_id": r"created_engagement_id:\s*(\d+)"
        },
        "description": "create a new HubSpot engagement",
        "setup": lambda context: {
            "random_id": str(uuid.uuid4())[:8],
            "timestamp": int(time.time() * 1000),
        },
        "depends_on": ["created_contact_id"],
    },
    {
        "name": "get_engagement",
        "args_template": 'with engagement_id="{created_engagement_id}"',
        "expected_keywords": ["engagement_id"],
        "regex_extractors": {"engagement_id": r"engagement_id:\s*(\d+)"},
        "description": "get a specific HubSpot engagement",
        "depends_on": ["created_engagement_id"],
    },
    {
        "name": "list_engagements",
        "args_template": "with limit=5",
        "expected_keywords": ["total"],
        "description": "list HubSpot engagements",
    },
    {
        "name": "get_call_dispositions",
        "args_template": "",
        "expected_keywords": ["id", "label"],
        "description": "get all possible dispositions for sales calls",
    },
    {
        "name": "update_engagement",
        "args_template": 'with engagement_id="{created_engagement_id}" metadata_body="Updated engagement note {random_id}"',
        "expected_keywords": ["updated_engagement_id"],
        "regex_extractors": {
            "updated_engagement_id": r"updated_engagement_id:\s*(\d+)"
        },
        "description": "update an existing HubSpot engagement",
        "depends_on": ["created_engagement_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "delete_engagement",
        "args_template": 'with engagement_id="{created_engagement_id}"',
        "expected_keywords": ["status_code"],
        "description": "delete a HubSpot engagement",
        "depends_on": ["created_engagement_id"],
    },
    {
        "name": "create_contact",
        "args_template": 'with email="test{random_id}@example.com" firstname="Test" lastname="User {random_id}" company="Test Company" jobtitle="QA Tester"',
        "expected_keywords": ["secondary_contact_id"],
        "regex_extractors": {"secondary_contact_id": r"secondary_contact_id:\s*(\d+)"},
        "description": "create a second hubspot contact and return its secondary_contact_id",
    },
    {
        "name": "merge_contacts",
        "args_template": 'with primary_contact_id="{created_contact_id}" secondary_contact_id="{secondary_contact_id}"',
        "expected_keywords": ["id", "status_code"],
        "description": "merge two HubSpot contacts",
        "depends_on": ["created_contact_id", "secondary_contact_id"],
    },
    {
        "name": "gdpr_delete_contact",
        "args_template": 'with contact_id="{created_contact_id}"',
        "expected_keywords": ["status_code"],
        "description": "permanently delete a HubSpot contact (GDPR-compliant)",
        "depends_on": ["created_contact_id"],
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_hubspot_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)

    if response and hasattr(response, "resources") and len(response.resources) > 0:
        context["first_resource_uri"] = response.resources[0].uri

    return response
