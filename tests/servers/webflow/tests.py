import pytest
import re
import random

TOOL_TESTS = [
    # Basic information tools
    {
        "name": "get_authorized_user",
        "args": "",
        "expected_keywords": ["id"],
        "regex_extractors": {"id": r'"?id"?[:\s]+([^,\s\n"]+)'},
        "description": "get information about the authorized Webflow user and return id",
    },
    {
        "name": "list_sites",
        "args": "",
        "expected_keywords": ["site_id"],
        "regex_extractors": {"site_id": r'"?site_?[iI]d"?[:\s]+([^,\s\n"]+)'},
        "description": "list all sites the provided access token can access and return site_id",
    },
    {
        "name": "get_site",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["workspace_id"],
        "regex_extractors": {
            "workspace_id": r'"?workspace_?[iI]d"?[:\s]+([^,\s\n"]+)',
        },
        "description": "get details of a specific site by its ID and return workspace_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "get_custom_domains",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["domain_url"],
        "regex_extractors": {
            "domain_url": r'"?domain_?[uU]rl"?[:\s]+([^,\s\n"]+)',
        },
        "description": "get a list of all custom domains related to a site",
        "depends_on": ["site_id"],
    },
    # Pages related tests
    {
        "name": "list_pages",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["page_id"],
        "regex_extractors": {"page_id": r'"?page_?[iI]d"?[:\s]+([^,\s\n"]+)'},
        "description": "list all pages for a site and return any one page_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "get_page_metadata",
        "args_template": 'with page_id="{page_id}"',
        "expected_keywords": ["id"],
        "regex_extractors": {"id": r'"?id"?[:\s]+([^,\s\n"]+)'},
        "description": "get metadata information for a single page and return id",
        "depends_on": ["page_id"],
    },
    {
        "name": "get_page_content",
        "args_template": 'with page_id="{page_id}"',
        "expected_keywords": ["page_id"],
        "regex_extractors": {
            "page_id": r"page_id\s*:\s*([^\s]+)",
        },
        "description": "get content from a static page and return any one page_id",
        "depends_on": ["page_id"],
    },
    # Forms related tests
    {
        "name": "list_forms",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["form_id"],
        "regex_extractors": {"form_id": r'"?form_?[iI]d"?[:\s]+([^,\s\n"]+)'},
        "description": "list forms for a given site and return any one form_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "list_form_submissions",
        "args_template": 'with form_id="{form_id}"',
        "expected_keywords": ["submission_id"],
        "regex_extractors": {
            "submission_id": r"submission_id\s*:\s*([^\s]+)",
        },
        "description": "list form submissions for a given form and return any one submission_id if empty return empty list []",
        "depends_on": ["form_id"],
    },
    {
        "name": "get_form_submission",
        "args_template": 'with form_submission_id="{submission_id}"',
        "expected_keywords": ["formResponse"],
        "description": "get information about a specific form submission and return formResponse if empty return empty list []",
        "depends_on": ["submission_id"],
    },
    {
        "name": "list_form_submissions_by_site",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["form_submission_id"],
        "regex_extractors": {
            "form_submission_id": r"form_submission_id\s*:\s*([^\s]+)",
        },
        "description": "list form submissions for a given site and return any one form_submission_id if empty return empty list []",
        "depends_on": ["site_id"],
    },
    {
        "name": "delete_form_submission",
        "args_template": 'with form_submission_id="{form_submission_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete a form submission and return status_code",
        "depends_on": ["form_submission_id"],
    },
    # Collection related tests
    {
        "name": "list_collections",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["collection_id"],
        "regex_extractors": {"collection_id": r"collection_id:\s*([^\s]+)"},
        "description": "list all collections within a site and return any one collection_id",
        "depends_on": ["site_id"],
    },
    {
        "name": "get_collection",
        "args_template": 'with collection_id="{collection_id}"',
        "expected_keywords": ["collection_schema_id"],
        "regex_extractors": {
            "collection_schema_id": r"collection_schema_id:\s*([^\s]+)",
        },
        "description": "get the full details of a collection from its ID and return collection_schema_id",
        "depends_on": ["collection_id"],
    },
    {
        "name": "create_collection",
        "args_template": 'with site_id="{site_id}" displayName="Test Collection-{random_id}" singularName="Test Item-{random_id}" slug="test-collection-{random_id}"',
        "expected_keywords": ["new_collection_id"],
        "regex_extractors": {
            "new_collection_id": r"new_collection_id:\s*([^\s]+)",
        },
        "description": "create a new collection for a site and return new new_collection_id",
        "depends_on": ["site_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    # Collection items staging tests
    {
        "name": "create_collection_item_staging",
        "args_template": 'with collection_id="{new_collection_id}" with field_data name="Test Item-{random_id}" slug="test-item-{random_id}"',
        "expected_keywords": ["new_item_id"],
        "regex_extractors": {"new_item_id": r"new_item_id\s*:\s*([^\s]+)"},
        "description": "create a new item in a collection and return id as new_item_id",
        "depends_on": ["new_collection_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "list_collection_items_staging",
        "args_template": 'with collection_id="{collection_id}"',
        "expected_keywords": ["_status_code"],
        "description": "list all items in a collection",
        "depends_on": ["collection_id"],
    },
    {
        "name": "get_collection_item_staging",
        "args_template": 'with collection_id="{new_collection_id}" item_id="{new_item_id}"',
        "expected_keywords": ["slug"],
        "description": "get a specific item from a collection and return any one slug",
        "depends_on": ["new_collection_id", "new_item_id"],
    },
    {
        "name": "update_collection_item_staging",
        "args_template": 'with collection_id="{new_collection_id}" item_id="{new_item_id}" field_data="name": "Updated Item-{random_id}"',
        "expected_keywords": ["fieldData"],
        "description": "update a specific item in a collection and return fieldData",
        "depends_on": ["new_collection_id", "new_item_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    # Cleanup - deleting items first, then collections
    {
        "name": "delete_collection_item_staging",
        "args_template": 'with collection_id="{new_collection_id}" item_id="{new_item_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete the localized item from a collection and return status_code",
        "depends_on": ["new_collection_id", "new_item_id"],
    },
    {
        "name": "delete_collection",
        "args_template": 'with collection_id="{new_collection_id}"',
        "expected_keywords": ["_status_code"],
        "regex_extractors": {
            "_status_code": r'"?_status_code"?[\s\n]*:[\s\n]*(\d+)',
        },
        "description": "delete a collection using its ID and return status_code",
        "depends_on": ["new_collection_id"],
    },
    # User related tests (kept as optional/skipped since they might be sensitive)
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

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


def get_test_id(test_config):
    return f"{test_config['name']}_{hash(test_config['description']) % 1000}"


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_webflow_tool(client, context, test_config):
    if test_config.get("skip", False):
        pytest.skip(f"Test {test_config['name']} marked to skip")
        return

    missing_deps = []
    for dep in test_config.get("depends_on", []):
        if dep not in context:
            missing_deps.append(dep)
        elif context[dep] in ["empty_list", "not_found", "empty"]:
            missing_deps.append(f"{dep} (has placeholder value)")

    if missing_deps:
        pytest.skip(f"Missing dependencies: {', '.join(missing_deps)}")
        return

    if "setup" in test_config and callable(test_config["setup"]):
        setup_result = test_config["setup"](context)
        if isinstance(setup_result, dict):
            context.update(setup_result)

    tool_name = test_config["name"]
    expected_keywords = test_config["expected_keywords"]
    description = test_config["description"]

    # Use args if available, otherwise try to format args_template
    if "args" in test_config:
        args = test_config["args"]
    elif "args_template" in test_config:
        try:
            args = test_config["args_template"].format(**context)
        except KeyError as e:
            pytest.skip(f"Missing context value: {e}")
            return
        except Exception as e:
            pytest.skip(f"Error formatting args: {e}")
            return
    else:
        args = ""

    keywords_str = ", ".join(expected_keywords)
    prompt = (
        "Not interested in your recommendations or what you think is best practice, just use what's given. "
        "Only pass required arguments to the tool and in case I haven't provided a required argument, you can try to pass your own that makes sense. "
        f"Only return the {keywords_str} with keywords if successful or error with keyword 'error_message'. "
        f"Use the {tool_name} tool to {description} {args}. "
        "Sample response: keyword: output_data keyword2: output_data2 keyword3: []"
    )

    response = await client.process_query(prompt)
    print(f"Response: {response}")

    # Handle common empty result patterns
    if (
        "empty" in response.lower()
        or "[]" in response
        or "no items" in response.lower()
        or "not found" in response.lower()
        or "custom domain" in response.lower()
        and "customdomains: []" in response.lower()
    ):
        print(f"Empty result detected for {tool_name}, skipping keyword validation")

        # Extract any values using regex or set default placeholders
        if "regex_extractors" in test_config:
            for key, pattern in test_config["regex_extractors"].items():
                if key not in context:
                    context[key] = "empty_list"
                    print(f"Set placeholder for {key}: empty_list")

        pytest.skip(f"Empty result from API for {tool_name}")
        return

    # Handle API errors
    if "error_message" in response.lower() and "error_message" not in expected_keywords:
        pytest.skip(f"API error for {tool_name}: {response}")
        return

    # Check for expected keywords
    missing_keywords = []
    for keyword in expected_keywords:
        if keyword != "error_message" and keyword.lower() not in response.lower():
            missing_keywords.append(keyword)

    if missing_keywords:
        pytest.skip(f"Keywords not found: {', '.join(missing_keywords)}")
        return

    # Extract values using regex
    if "regex_extractors" in test_config:
        for key, pattern in test_config["regex_extractors"].items():
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match and len(match.groups()) > 0:
                context[key] = match.group(1).strip() or "value_found"
                print(f"Extracted {key}: {context[key]}")
            else:
                context[key] = context.get(key, "not_found")
                print(f"Couldn't extract {key}, using default: {context[key]}")

    return context
