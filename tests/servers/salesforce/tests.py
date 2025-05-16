import pytest
import uuid

from tests.utils.test_tools import get_test_id, run_tool_test


# Shared context dictionary for test values
SHARED_CONTEXT = {
    "test_email": "",  # replace with an email from salesforce account
}


# Test configurations for Salesforce tools - one test per tool type
TOOL_TESTS = [
    {
        "name": "describe_object",
        "args_template": 'with object_name="Account"',
        "expected_keywords": ["object_name"],
        "regex_extractors": {"object_name": r"object_name:\s*([^\s]+)"},
        "description": "Retrieve detailed metadata about a Salesforce object",
    },
    {
        "name": "get_org_limits",
        "args_template": "",
        "expected_keywords": ["api_requests_remaining"],
        "regex_extractors": {
            "api_requests_remaining": r"api_requests_remaining:\s*(\d+)"
        },
        "description": "Retrieve current organization limits and return the api_requests_remaining value",
    },
    {
        "name": "create_record",
        "args_template": 'with object_name="Account" data={{"Name": "Test Account {random_id}", "Industry": "Technology"}}',
        "expected_keywords": ["account_id"],
        "regex_extractors": {"account_id": r"account_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Create a new Account record",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "get_record",
        "args_template": 'with object_name="Account" record_id="{account_id}"',
        "expected_keywords": ["account_id"],
        "regex_extractors": {"account_id": r"account_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Retrieve a specific Salesforce record by ID and return the account_id",
        "depends_on": ["account_id"],
    },
    {
        "name": "soql_query",
        "args_template": "with query=\"SELECT Id, Name FROM Account WHERE Id = '{account_id}'\"",
        "expected_keywords": ["record_id"],
        "regex_extractors": {"record_id": r"record_id:\s*([^\s]+)"},
        "description": "Execute a SOQL query to retrieve Salesforce records and return any one record_id",
        "depends_on": ["account_id"],
    },
    {
        "name": "create_record",
        "args_template": 'with object_name="Contact" data={{"FirstName": "Test", "LastName": "Contact {random_id}", "Email": "test.contact{random_id}@example.com", "AccountId": "{account_id}"}}',
        "expected_keywords": ["contact_id"],
        "regex_extractors": {"contact_id": r"contact_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Create a new Contact record related to the test Account",
        "depends_on": ["account_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_record",
        "args_template": 'with object_name="Account" record_id="{account_id}" data={{"Description": "Updated description as of {random_id}"}}',
        "expected_keywords": ["record_id"],
        "regex_extractors": {"record_id": r"record_id:\s*([^\s]+)"},
        "description": "Update an existing Account record and return the record_id",
        "depends_on": ["account_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "list_campaigns",
        "args_template": "with limit=5",
        "expected_keywords": ["campaign_id"],
        "regex_extractors": {"campaign_id": r"campaign_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "List campaigns in Salesforce and return any one campaign ID",
    },
    {
        "name": "add_contact_to_campaign",
        "args_template": 'with contact_id="{contact_id}" campaign_id="{campaign_id}" status="Sent"',
        "expected_keywords": ["status"],
        "regex_extractors": {"status": r"status:\s*([^\s,}]+)"},
        "description": "Add a contact to a campaign and return the status",
        "depends_on": ["contact_id", "campaign_id"],
    },
    {
        "name": "create_child_records",
        "args_template": 'with parent_id="{account_id}" child_object_name="Contact" parent_field_name="AccountId" records=[{{"FirstName": "Child", "LastName": "Record {random_id}", "Email": "child{random_id}@example.com"}}]',
        "expected_keywords": ["child_id"],
        "regex_extractors": {"child_id": r"child_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Create child records from line items and sets the parent-child relationship",
        "depends_on": ["account_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "find_child_records",
        "args_template": 'with parent_id="{account_id}" child_object_name="Contact" parent_field_name="AccountId"',
        "expected_keywords": ["child_id"],
        "regex_extractors": {"child_id": r"child_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Find child records for a given parent ID and return any one child_id",
        "depends_on": ["account_id"],
    },
    {
        "name": "create_enhanced_note",
        "args_template": 'with title="Test Note {random_id}" content="<h1>Test Note Content</h1><p>This is a test note created during testing.</p>"',
        "expected_keywords": ["note_id"],
        "regex_extractors": {"note_id": r"note_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Create an enhanced note (ContentNote)",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_file",
        "args_template": 'with title="Test File {random_id}" path_on_client="test_file.txt" version_data="VGhpcyBpcyBhIHRlc3QgZmlsZSBjb250ZW50IGNyZWF0ZWQgZHVyaW5nIHRlc3RpbmcuCg==" description="Test file description"',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r"file_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Create a file (ContentVersion)",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_record",
        "args_template": 'with object_name="Lead" data={{"FirstName": "Test", "LastName": "Lead {random_id}", "Company": "Test Company", "Email": "test.lead{random_id}@example.com", "Status": "Open - Not Contacted"}}',
        "expected_keywords": ["lead_id"],
        "regex_extractors": {"lead_id": r"lead_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Create a new Lead record",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "add_lead_to_campaign",
        "args_template": 'with lead_id="{lead_id}" campaign_id="{campaign_id}" status="Sent"',
        "expected_keywords": ["status"],
        "regex_extractors": {"status": r"status:\s*([^\s,}]+)"},
        "description": "Add a lead to a campaign and return the status",
        "depends_on": ["lead_id", "campaign_id"],
    },
    {
        "name": "convert_lead",
        "args_template": 'with lead_id="{lead_id}" converted_status="Closed - Converted" create_opportunity=true opportunity_name="Test Opportunity {random_id}"',
        "expected_keywords": ["success"],
        "regex_extractors": {"success": r"success:\s*(true|false)"},
        "description": "Convert a lead to account, contact, and opportunity",
        "depends_on": ["lead_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_note",
        "args_template": 'with parent_id="{account_id}" title="Test Note {random_id}" body="This is a test note created during testing."',
        "expected_keywords": ["note_id"],
        "regex_extractors": {"note_id": r"note_id:\s*([A-Za-z0-9]{15,18})"},
        "description": "Create a legacy note linked to a parent record",
        "depends_on": ["account_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "list_email_templates",
        "args_template": "with limit=5",
        "expected_keywords": ["template_id"],
        "regex_extractors": {
            "template_id": r'"?template_id"?\s*[:=]\s*"?([A-Za-z0-9]{15,18})"?'
        },
        "description": "List email templates and return any one template ID",
    },
    {
        "name": "delete_record",
        "args_template": 'with object_name="Contact" record_id="{contact_id}"',
        "expected_keywords": ["status"],
        "regex_extractors": {"status": r"status:\s*([^\s,}]+)"},
        "description": "Delete the test Contact record and return the status",
        "depends_on": ["contact_id"],
    },
    {
        "name": "delete_record",
        "args_template": 'with object_name="Account" record_id="{account_id}"',
        "expected_keywords": ["status"],
        "regex_extractors": {"status": r"status:\s*([^\s,}]+)"},
        "description": "Delete the test Account record and return the status",
        "depends_on": ["account_id"],
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_salesforce_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)
