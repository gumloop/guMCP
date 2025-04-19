import pytest
import re
import random

TOOL_TESTS = [
    {
        "name": "get_user",
        "args": "id=me",
        "expected_keywords": ["user_email", "user_id"],
        "regex_extractors": {
            "user_id": r"user_id:\s*([^\n]+)",
            "user_email": r"user_email:\s*([^\n]+)",
        },
        "description": "get details about a user in PagerDuty and extract the email address and ID",
    },
    {
        "name": "create_schedule",
        "args_template": "with email_from='{user_email}', name='Test Schedule {random_number}', time_zone='UTC', schedule_layers='name': 'Layer 1', 'start': '2023-01-01T00:00:00Z', 'rotation_virtual_start': '2023-01-01T00:00:00Z', 'rotation_turn_length_seconds': 86400, 'users': 'user': 'id': '{user_id}', 'type': 'user_reference'",
        "expected_keywords": ["schedule_id"],
        "regex_extractors": {"schedule_id": r"schedule_id:\s*([^\n]+)"},
        "description": "create a new on-call schedule in PagerDuty",
        "depends_on": ["user_id", "user_email"],
    },
    {
        "name": "list_schedules",
        "args_template": "with email_from='{user_email}', limit=5, include=['schedule_layers']",
        "expected_keywords": ["schedules"],
        "description": "list on-call schedules from PagerDuty",
        "depends_on": ["user_email"],
    },
    {
        "name": "get_schedule",
        "args_template": "id='{schedule_id}', email_from='{user_email}'",
        "expected_keywords": ["schedule"],
        "description": "get details about a specific schedule in PagerDuty",
        "depends_on": ["schedule_id", "user_email"],
    },
    {
        "name": "list_oncalls",
        "args_template": "email_from='{user_email}', limit=5",
        "expected_keywords": ["oncalls"],
        "description": "list on-call entries in PagerDuty",
        "depends_on": ["user_email"],
    },
    {
        "name": "list_notifications",
        "args_template": "email_from='{user_email}', since='2023-01-01T00:00:00Z', until='2023-12-31T23:59:59Z'",
        "expected_keywords": ["notifications"],
        "description": "list notifications in PagerDuty",
        "depends_on": ["user_email"],
    },
    {
        "name": "delete_schedule",
        "args_template": "id='{schedule_id}', email_from='{user_email}'",
        "expected_keywords": ["success"],
        "description": "delete a schedule in PagerDuty",
        "depends_on": ["schedule_id", "user_email"],
    },
]


@pytest.mark.asyncio
async def test_pagerduty_workflow(client):
    context = {}
    for test_config in TOOL_TESTS:
        await run_tool_test(client, test_config, context)


async def run_tool_test(client, test_config, context):
    tool_name = test_config["name"]
    expected_keywords = test_config["expected_keywords"]
    description = test_config["description"]

    depends_on = test_config.get("depends_on", [])
    for dependency in depends_on:
        if dependency not in context:
            pytest.skip(
                f"Test {tool_name} skipped. Required context '{dependency}' not available"
            )

    if "args" in test_config:
        args = test_config["args"]
    elif "args_template" in test_config:
        try:
            if (
                "random_number" not in context
                and "{random_number}" in test_config["args_template"]
            ):
                context["random_number"] = random.randint(1, 1000000)
            args = test_config["args_template"].format(**context)
        except KeyError as e:
            pytest.skip(
                f"Test {tool_name} skipped. Missing required context value: {e}"
            )
    else:
        args = ""

    keywords_str = ", ".join(expected_keywords)
    prompt = (
        "Not interested in your recommendations or what you think is best practice, just use what's given. "
        "Only pass required arguments to the tool and in case I haven't provided a required argument, you can try to pass your own that makes sense. "
        f"Use the {tool_name} tool to {description} {args}. "
        f"Only return the {keywords_str} with keywords if successful or error with keyword 'error_message'."
        "Sample response: keyword: output_data keyword2: output_data2"
    )

    response = await client.process_query(prompt)

    if "error_message" in response:
        pytest.fail(f"{tool_name} : Failed to {description}: {response}")

    for keyword in expected_keywords:
        assert (
            keyword in response
        ), f"{tool_name} : Expected '{keyword}' in response: {response}"

    if "regex_extractors" in test_config:
        for key, pattern in test_config["regex_extractors"].items():
            match = re.search(pattern, response, re.DOTALL)
            if match and match.group(1):
                context[key] = match.group(1).strip()
            else:
                fallback_pattern = r"{key}:\s*([^\n]+)".format(key=key)
                match = re.search(fallback_pattern, response, re.DOTALL)
                if match and match.group(1):
                    context[key] = match.group(1).strip()

    return context
