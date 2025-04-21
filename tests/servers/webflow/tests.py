import pytest
import re
import json
import random

TOOL_TESTS = [
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
    # {
    #     "name": "get_site",
    #     "args_template": 'with site_id="{site_id}"',
    #     "expected_keywords": ["workspace_id"],
    #     "regex_extractors": {
    #         "workspace_id": r'"?workspace_?[iI]d"?[:\s]+([^,\s\n"]+)',
    #     },
    #     "description": "get details of a specific site by its ID",
    #     "depends_on": ["site_id"],
    # },
    # {
    #     "name": "get_custom_domains",
    #     "args_template": 'with site_id="{site_id}"',
    #     "expected_keywords": ["domain_url"],
    #     "regex_extractors": {
    #         "domain_url": r'"?domain_?[uU]rl"?[:\s]+([^,\s\n"]+)',
    #     },
    #     "description": "get a list of all custom domains related to a site",
    #     "depends_on": ["site_id"],
    # },
    {
        "name": "list_pages",
        "args_template": 'with site_id="{site_id}"',
        "expected_keywords": ["page_id"],
        "regex_extractors": {"page_id": r'"?page_?[iI]d"?[:\s]+([^,\s\n"]+)'},
        "description": "list all pages for a site and return any one page_id",
        "depends_on": ["site_id"],
    },
    # {
    #     "name": "get_page_metadata",
    #     "args_template": 'with page_id="{page_id}"',
    #     "expected_keywords": ["id"],
    #     "regex_extractors": {"id": r'"?id"?[:\s]+([^,\s\n"]+)'},
    #     "description": "get metadata information for a single page and return id",
    #     "depends_on": ["page_id"],
    # },
    # {
    #     "name": "get_page_content",
    #     "args_template": 'with page_id="{page_id}"',
    #     "expected_keywords": ["component_id"],
    #     "regex_extractors": {
    #         "component_id": r'"?component[iI]d"?[:\s]+([^,\s\n"]+)',
    #     },
    #     "description": "get content from a static page and return any one component_id",
    #     "depends_on": ["page_id"],
    # },
    # {
    #     "name": "list_forms",
    #     "args_template": 'with site_id="{site_id}"',
    #     "expected_keywords": ["form_id"],
    #     "regex_extractors": {"form_id": r'"?form_?[iI]d"?[:\s]+([^,\s\n"]+)'},
    #     "description": "list forms for a given site and return any one form_id",
    #     "depends_on": ["site_id"],
    # },
    # {
    #     "name": "list_form_submissions",
    #     "args_template": 'with form_id="{form_id}"',
    #     "expected_keywords": ["formSubmissions"],
    #     "regex_extractors": {
    #         "submission_id": r'"?submission_?[iI]d"?[:\s]+([^,\s\n"]+)',
    #     },
    #     "description": "list form submissions for a given form and return any one submission_id",
    #     "depends_on": ["form_id"],
    # },
    # {
    #     "name": "get_form_submission",
    #     "args_template": 'with form_submission_id="{submission_id}"',
    #     "expected_keywords": ["formResponse"],
    #     "description": "get information about a specific form submission and return formResponse",
    #     "depends_on": ["submission_id"],
    # },
    # {
    #     "name": "list_form_submissions_by_site",
    #     "args_template": 'with site_id="{site_id}"',
    #     "expected_keywords": ["form_submission_id"],
    #     "regex_extractors": {
    #         "form_submission_id": r'"?form_submission_?[iI]d"?[:\s]+([^,\s\n"]+)',
    #     },
    #     "description": "list form submissions for a given site and return any one form_submission_id",
    #     "depends_on": ["site_id"],
    # },
    # {
    #     "name": "delete_form_submission",
    #     "args_template": 'with form_submission_id="{form_submission_id}"',
    #     "expected_keywords": ["_status_code"],
    #     "description": "delete a form submission",
    #     "depends_on": ["form_submission_id"],
    # },
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
        "expected_keywords": ["slug"],
        "regex_extractors": {
            "slug": r'"slug"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "get the full details of a collection from its ID and return slug",
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
        "name": "list_collection_items",
        "args_template": 'with collection_id="{collection_id}"',
        "expected_keywords": ["item_id"],
        "regex_extractors": {
            "item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "list all items in a collection and return any one item id and return item_id",
        "depends_on": ["collection_id"],
    },
    {
        "name": "create_collection_item",
        "args_template": 'with collection_id="{collection_id}" field_data={"name": "Test Item-{random_id}", "slug": "test-item-{random_id}"}',
        "expected_keywords": ["new_item_id "],
        "regex_extractors": {
            "new_item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "create a new item in a collection and return new_item_id",
        "depends_on": ["collection_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "get_collection_item",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_item_id}"',
        "expected_keywords": ["id", "fieldData"],
        "description": "get a specific item from a collection",
        "depends_on": ["collection_id", "new_item_id"],
    },
    {
        "name": "update_collection_item",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_item_id}" field_data={"name": "Updated Item-{random_id}"}',
        "expected_keywords": ["id", "fieldData"],
        "description": "update a specific item in a collection",
        "depends_on": ["collection_id", "new_item_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "publish_collection_items",
        "args_template": 'with collection_id="{collection_id}" item_ids=["{new_item_id}"]',
        "expected_keywords": ["publishedItemIds"],
        "description": "publish item(s) in a collection",
        "depends_on": ["collection_id", "new_item_id"],
    },
    {
        "name": "delete_collection_item",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_item_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete a specific item from a collection",
        "depends_on": ["collection_id", "new_item_id"],
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
    {
        "name": "list_collection_items_staging",
        "args_template": 'with collection_id="{collection_id}"',
        "expected_keywords": ["items", "pagination"],
        "regex_extractors": {
            "item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "list all items in a collection and return item_id",
        "depends_on": ["collection_id"],
    },
    {
        "name": "create_collection_item_staging",
        "args_template": 'with collection_id="{collection_id}" field_data={"name": "Test Item-{random_id}", "slug": "test-item-{random_id}"}',
        "expected_keywords": ["id", "fieldData"],
        "regex_extractors": {
            "new_item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "create a new item in a collection and return new_item_id",
        "depends_on": ["collection_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "get_collection_item_staging",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_item_id}"',
        "expected_keywords": ["id", "fieldData"],
        "description": "get a specific item from a collection",
        "depends_on": ["collection_id", "new_item_id"],
    },
    {
        "name": "update_collection_item_staging",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_item_id}" field_data={"name": "Updated Item-{random_id}"}',
        "expected_keywords": ["id", "fieldData"],
        "description": "update a specific item in a collection",
        "depends_on": ["collection_id", "new_item_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "create_collection_item_staging",
        "args_template": 'with collection_id="{collection_id}" field_data={"name": "Second Item-{random_id}", "slug": "second-item-{random_id}"}',
        "expected_keywords": ["id", "fieldData"],
        "regex_extractors": {
            "second_item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "create a second item in a collection for testing multiple operations",
        "depends_on": ["collection_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "update_collection_items_staging",
        "args_template": 'with collection_id="{collection_id}" items=[{"id": "{new_item_id}", "field_data": {"name": "Multi-Updated Item-{random_id}"}}, {"id": "{second_item_id}", "field_data": {"name": "Multi-Updated Second-{random_id}"}}]',
        "expected_keywords": ["id", "fieldData"],
        "description": "update multiple items in a collection",
        "depends_on": ["collection_id", "new_item_id", "second_item_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "create_localized_collection_items_staging",
        "args_template": 'with collection_id="{collection_id}" field_data={"name": "Localized Item-{random_id}", "slug": "localized-item-{random_id}"} cms_locale_ids=["653ad57de882f528b32e810e"]',
        "expected_keywords": ["id", "cmsLocaleIds"],
        "regex_extractors": {
            "localized_item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "create an item across multiple locales",
        "depends_on": ["collection_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "publish_collection_items_staging",
        "args_template": 'with collection_id="{collection_id}" item_ids=["{new_item_id}", "{second_item_id}"]',
        "expected_keywords": ["publishedItemIds"],
        "description": "publish item(s) in a collection",
        "depends_on": ["collection_id", "new_item_id", "second_item_id"],
    },
    {
        "name": "delete_collection_items_staging",
        "args_template": 'with collection_id="{collection_id}" items=[{"id": "{second_item_id}"}]',
        "expected_keywords": ["_status_code"],
        "description": "delete multiple items from a collection",
        "depends_on": ["collection_id", "second_item_id"],
    },
    {
        "name": "delete_collection_item_staging",
        "args_template": 'with collection_id="{collection_id}" item_id="{localized_item_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete the localized item from a collection",
        "depends_on": ["collection_id", "localized_item_id"],
    },
    {
        "name": "list_collection_items_live",
        "args_template": 'with collection_id="{collection_id}"',
        "expected_keywords": ["items", "pagination"],
        "regex_extractors": {
            "live_item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "list all published items in a collection and return live_item_id",
        "depends_on": ["collection_id"],
    },
    {
        "name": "create_collection_item_live",
        "args_template": 'with collection_id="{collection_id}" field_data={"name": "Live Item-{random_id}", "slug": "live-item-{random_id}"}',
        "expected_keywords": ["id", "fieldData"],
        "regex_extractors": {
            "new_live_item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "create a new live item in a collection and return new_live_item_id",
        "depends_on": ["collection_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "get_collection_item_live",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_live_item_id}"',
        "expected_keywords": ["id", "fieldData"],
        "description": "get a specific live item from a collection",
        "depends_on": ["collection_id", "new_live_item_id"],
    },
    {
        "name": "update_collection_item_live",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_live_item_id}" field_data={"name": "Updated Live Item-{random_id}"}',
        "expected_keywords": ["id", "fieldData"],
        "description": "update a specific live item in a collection",
        "depends_on": ["collection_id", "new_live_item_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "create_collection_item_live",
        "args_template": 'with collection_id="{collection_id}" field_data={"name": "Second Live Item-{random_id}", "slug": "second-live-item-{random_id}"}',
        "expected_keywords": ["id", "fieldData"],
        "regex_extractors": {
            "second_live_item_id": r'"id"[\s\n]*:[\s\n]*"([^"\n]+)"',
        },
        "description": "create a second live item in a collection for testing multiple operations",
        "depends_on": ["collection_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "update_collection_items_live",
        "args_template": 'with collection_id="{collection_id}" items=[{"id": "{new_live_item_id}", "field_data": {"name": "Multi-Updated Live Item-{random_id}"}}, {"id": "{second_live_item_id}", "field_data": {"name": "Multi-Updated Live Second-{random_id}"}}]',
        "expected_keywords": ["id", "fieldData", "items"],
        "description": "update multiple live items in a collection",
        "depends_on": ["collection_id", "new_live_item_id", "second_live_item_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "delete_collection_items_live",
        "args_template": 'with collection_id="{collection_id}" items=[{"id": "{second_live_item_id}"}]',
        "expected_keywords": ["_status_code"],
        "description": "delete multiple live items from a collection",
        "depends_on": ["collection_id", "second_live_item_id"],
    },
    {
        "name": "delete_collection_item_live",
        "args_template": 'with collection_id="{collection_id}" item_id="{new_live_item_id}"',
        "expected_keywords": ["_status_code"],
        "description": "delete a specific live item from a collection",
        "depends_on": ["collection_id", "new_live_item_id"],
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
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                if len(match.groups()) > 0:
                    context[key] = (
                        match.group(1).strip() if match.group(1) else "value_found"
                    )
                else:
                    # Match found but no capture groups - still success
                    context[key] = "value_found"
                print(f"  Extracted {key}: {context[key]}")
            else:
                print(f"⚠️ Warning: Couldn't extract {key} from response in {tool_name}")

    return context
