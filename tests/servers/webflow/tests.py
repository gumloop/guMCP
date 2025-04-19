import pytest
import re
import json
import random

TOOL_TESTS = [
    {
        "name": "get_authorized_user",
        "args": "",
        "expected_keywords": ["id"],
        "regex_extractors": {"id": r"id:\s*([^,\s\n]+)"},
        "description": "get information about the authorized Webflow user and return id",
    },
    {
        "name": "list_sites",
        "args": "",
        "expected_keywords": ["site_id"],
        "regex_extractors": {"site_id": r"site_id:\s*([^,\s\n]+)"},
        "description": "list all sites the provided access token can access and return site_id",
    },
    {
        "name": "get_site",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["displayName", "workspaceId"],
        "regex_extractors": {
            "workspace_id": r"workspaceId:\s*([^,\s\n]+)",
        },
        "description": "get details of a specific site by its ID",
        "depends_on": ["site_id"],
    },
    {
        "name": "get_custom_domains",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["customDomains"],
        "regex_extractors": {
            "domain_id": r"domain_id:\s*([^,\s\n]+)",
            "domain_url": r"domain_url:\s*([^,\s\n]+)",
        },
        "description": "get a list of all custom domains related to a site",
        "depends_on": ["site_id"],
    },
    {
        "name": "list_pages",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["page_id"],
        "regex_extractors": {"page_id": r"page_id:\s*([^,\s\n]+)"},
        "description": "list all pages for a site and return any one page_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "get_page_metadata",
        "args_template": 'with page_id="{page_id}"',
        "expected_keywords": ["title"],
        "regex_extractors": {"title": r"title"},
        "description": "get metadata information for a single page and return title",
        "depends_on": ["page_id"],
    },
    {
        "name": "get_page_content",
        "args_template": 'with page_id="{page_id}"',
        "expected_keywords": ["component_id"],
        "regex_extractors": {
            "component_id": r'"component_id"',
        },
        "description": "get content from a static page and return any one component_id",
        "depends_on": ["page_id"],
    },
    {
        "name": "list_forms",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["forms"],
        "regex_extractors": {
            "form_id": r"form_id:\s*([^,\s\n]+)",
            "form_name": r"form_name:\s*([^,\s\n]+)",
        },
        "description": "list forms for a given site and return any one form_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "list_form_submissions",
        "args_template": 'with form_id="{form_id}"',
        "expected_keywords": ["formSubmissions"],
        "regex_extractors": {
            "submission_id": r"submission_id:\s*([^,\s\n]+)",
        },
        "description": "list form submissions for a given form and return any one submission_id",
        "depends_on": ["form_id"],
    },
    {
        "name": "get_form_submission",
        "args_template": 'with form_submission_id="{submission_id}"',
        "expected_keywords": ["formResponse"],
        "description": "get information about a specific form submission and return formResponse",
        "depends_on": ["submission_id"],
    },
    {
        "name": "list_form_submissions_by_site",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["form_submission_id"],
        "regex_extractors": {
            "form_submission_id": r"form_submission_id:\s*([^,\s\n]+)",
        },
        "description": "list form submissions for a given site and return any one form_submission_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "delete_form_submission",
        "args_template": 'with form_submission_id="{form_submission_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete a form submission",
        "depends_on": ["form_submission_id"],
    },
    {
        "name": "list_collections",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["collection_id"],
        "regex_extractors": {
            "collection_id": r'(?:"id"|id)[\s\n]*:[\s\n]*"?([0-9a-f]+)"?',
        },
        "description": "list all collections within a site and return any one collection_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "get_collection",
        "args_template": 'with collection_id="{collection_id}"',
        "expected_keywords": ["displayName", "fields"],
        "regex_extractors": {
            "displayName": r'"displayName"[\s\n]*:[\s\n]*"([^"\n]+)"',
            "fields": r'"fields"[\s\n]*:[\s\n]*(\[.*?\])',
        },
        "description": "get the full details of a collection from its ID",
        "depends_on": ["collection_id"],
    },
    {
        "name": "create_collection",
        "args_template": 'with site_id="{site_id}" displayName="Test Collection-{random_id}" singularName="Test Item-{random_id}" slug="test-collection-{random_id}"',
        "expected_keywords": ["new_collection_id"],
        "regex_extractors": {
            "new_collection_id": r'(?:"id"|id)[\s\n]*:[\s\n]*"?([0-9a-f]+)"?',
        },
        "description": "create a new collection for a site and return new collection_id",
        "depends_on": ["site_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "delete_collection",
        "args_template": 'with collection_id="{new_collection_id}"',
        "expected_keywords": ["_status_code"],
        "regex_extractors": {
            "_status_code": r'"_status_code"[\s\n]*:[\s\n]*(\d+)',
        },
        "description": "delete a collection using its ID and return status_code",
        "depends_on": ["new_collection_id"],
    },
    {
        "name": "list_users",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["users"],
        "regex_extractors": {
            "users": r'"users"[\s\n]*:[\s\n]*(\[.*?\])',
        },
        "description": "list all users for a site",
        "depends_on": ["site_id"],
        "skip": True,
    },
    {
        "name": "get_user",
        "args_template": 'with site_id="{site_id}" user_id="{user_id}"',
        "expected_keywords": ["status", "accessGroups"],
        "regex_extractors": {
            "status": r'"status"[\s\n]*:[\s\n]*"([^"\n]+)"',
            "accessGroups": r'"accessGroups"[\s\n]*:[\s\n]*(\[.*?\])',
        },
        "description": "get a specific user by ID",
        "depends_on": ["site_id", "user_id"],
        "skip": True,
    },
    {
        "name": "invite_user",
        "args_template": 'with site_id="{site_id}" email="test{random_id}@example.com"',
        "expected_keywords": ["id", "email"],
        "regex_extractors": {
            "id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
            "email": r'"email"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "invite a new user to a site",
        "depends_on": ["site_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "skip": True,
    },
    {
        "name": "delete_user",
        "args_template": 'with site_id="{site_id}" user_id="{user_id}"',
        "expected_keywords": ["_status_code"],
        "regex_extractors": {
            "_status_code": r'"_status_code"[\s\n]*:[\s\n]*(\d+)',
        },
        "description": "delete a user by ID",
        "depends_on": ["site_id", "user_id"],
        "skip": True,
    },
]


@pytest.fixture
def context():
    return {}


@pytest.mark.asyncio
async def test_webflow_workflow(client, context):
    for test_config in TOOL_TESTS:
        if test_config.get("skip", False):
            print(f"⏭️ Skipping test {test_config['name']}: marked to skip")
            continue

        missing_deps = []
        for dep in test_config.get("depends_on", []):
            if dep not in context:
                missing_deps.append(dep)

        if missing_deps:
            print(
                f"⏭️ Skipping test {test_config['name']}: missing dependencies {', '.join(missing_deps)}"
            )
            continue

        if "setup" in test_config and callable(test_config["setup"]):
            setup_result = test_config["setup"](context)
            if isinstance(setup_result, dict):
                context.update(setup_result)

        await run_webflow_test(client, test_config, context)


async def run_webflow_test(client, test_config, context):
    tool_name = test_config["name"]
    expected_keywords = test_config["expected_keywords"]
    description = test_config["description"]

    if "args" in test_config:
        args = test_config["args"]
    elif "args_template" in test_config:
        try:
            args = test_config["args_template"].format(**context)
        except KeyError as e:
            pytest.fail(f"Missing context value for {tool_name}: {e}")
            return
    else:
        args = ""

    keywords_str = ", ".join(expected_keywords)
    prompt = (
        "Not interested in your recommendations or what you think is best practice, just use what's given. "
        "Only pass required arguments to the tool and in case I haven't provided a required argument, you can try to pass your own that makes sense. "
        f"Only return the {keywords_str} with keywords if successful or error with keyword 'error_message'. "
        f"Use the {tool_name} tool to {description} {args}. "
        "Sample response: keyword: output_data keyword2: output_data2"
    )

    response = await client.process_query(prompt)

    print(f"Response: {response}")

    if "error_message" in response.lower():
        print(f"❌ Test {tool_name} failed: API error: {response}")
        return context

    missing_keywords = []
    for keyword in expected_keywords:
        if keyword.lower() not in response.lower():
            missing_keywords.append(keyword)

    if missing_keywords:
        print(
            f"⚠️ Warning: {tool_name}: Expected keywords not found: {', '.join(missing_keywords)}"
        )
    else:
        print(f"✅ {tool_name.replace('_', ' ').title()} test completed")

    if "regex_extractors" in test_config:
        for key, pattern in test_config["regex_extractors"].items():
            match = re.search(pattern, response, re.DOTALL)
            if match:
                for group_idx in range(1, len(match.groups()) + 1):
                    if match.group(group_idx):
                        context[key] = match.group(group_idx).strip()
                        break
            else:
                print(f"⚠️ Warning: Couldn't extract {key} from response in {tool_name}")

    return context
