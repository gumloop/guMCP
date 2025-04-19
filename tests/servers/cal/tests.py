import pytest
import re
import json
from datetime import datetime, timedelta, timezone
import random

TOOL_TESTS = [
    {
        "name": "get_me",
        "args": "",
        "expected_keywords": ["username"],
        "regex_extractors": {
            "username": r'"username":\s*"([^"]+)"',
        },
        "description": "get your Cal.com user profile information and return username",
    },
    {
        "name": "get_event_types",
        "args_template": "with username={username}",
        "expected_keywords": ["event_type_details"],
        "regex_extractors": {
            "event_type_details": r'event_type_details:\s*(\d+)|"id":\s*(\d+)',
        },
        "description": "get available event types from Cal.com and return complete details of one of them as event_type_details. Include all fields like id, slug, title, length, etc.",
        "depends_on": ["username"],
    },
    {
        "name": "create_booking",
        "args_template": 'with start="{booking_time}", eventTypeId={event_type_details}, feel free to add any other fields you need based on the event type details',
        "expected_keywords": ["booking_uid"],
        "regex_extractors": {
            "booking_uid": r'booking_uid:\s*([^,\s"]+)|"uid":\s*"([^"]+)"',
        },
        "description": "create a booking using the Cal.com v2 API and return the booking uid",
        "depends_on": ["event_type_details"],
        "skip": True,
    },
    {
        "name": "get_bookings",
        "args": "with status=['upcoming']",
        "expected_keywords": ["booking_uid"],
        "regex_extractors": {
            "booking_uid_1": r'booking_uid_1:\s*([^,\s"]+)|"uid":\s*"([^"]+)"',
            "booking_uid_2": r'booking_uid_2:\s*([^,\s"]+)|"uid":\s*"([^"]+)"',
            "booking_uid_3": r'booking_uid_3:\s*([^,\s"]+)|"uid":\s*"([^"]+)"',
        },
        "description": "get all upcoming bookings from Cal.com and return unique booking_uid_1, booking_uid_2 etc",
    },
    {
        "name": "get_booking",
        "args_template": 'with bookingUid="{booking_uid_1}"',
        "expected_keywords": ["booking_uid", "event_type_id"],
        "regex_extractors": {
            "booking_uid": r'booking_uid:\s*([^,\s"]+)|"uid":\s*"([^"]+)"',
            "event_type_id": r'event_type_id:\s*([^,\s"]+)|"id":\s*(\d+)',
        },
        "description": "get a specific booking from Cal.com by its uid and return booking_uid and event_type_id",
        "depends_on": ["booking_uid_1"],
    },
    {
        "name": "reschedule_booking",
        "args_template": 'with bookingUid="{booking_uid_1}", start="{reschedule_time}", reschedulingReason="Testing API reschedule"',
        "expected_keywords": ["booking_uid"],
        "description": "reschedule a booking to a new time",
        "depends_on": ["booking_uid_1"],
        "skip": True,
    },
    {
        "name": "confirm_booking",
        "args_template": 'with bookingUid="{booking_uid_2}"',
        "expected_keywords": ["status"],
        "description": "confirm a pending booking and return status",
        "depends_on": ["booking_uid_2"],
        "skip": True,
    },
    {
        "name": "decline_booking",
        "args_template": 'with bookingUid="{booking_uid_2}", reason="Testing API decline"',
        "expected_keywords": ["status"],
        "description": "decline a pending booking and return status",
        "depends_on": ["booking_uid_2"],
        "skip": True,
    },
    {
        "name": "cancel_booking",
        "args_template": 'with bookingUid="{booking_uid_3}", cancellationReason="Testing API cancellation"',
        "expected_keywords": ["status"],
        "description": "cancel an existing booking and return status",
        "depends_on": ["booking_uid_3"],
    },
    {
        "name": "get_schedules",
        "args": "",
        "expected_keywords": ["schedule_id"],
        "regex_extractors": {
            "schedule_id": r'schedule_id:\s*(\d+)|"id":\s*(\d+)',
        },
        "description": "get all schedules from the authenticated user and return any one of them as schedule_id",
    },
]


@pytest.fixture
def context():
    """Fixture to create and maintain test context between tests"""
    data = {}
    current_time = datetime.now(timezone.utc)
    data["booking_time"] = (current_time + timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:00:00Z"
    )
    data["end_time"] = (current_time + timedelta(hours=3)).strftime(
        "%Y-%m-%dT%H:00:00Z"
    )
    data["reschedule_time"] = (current_time + timedelta(hours=10)).strftime(
        "%Y-%m-%dT%H:00:00Z"
    )
    data["random_number"] = random.randint(1000, 9999)
    return data


@pytest.mark.asyncio
async def test_cal_workflow(client, context):
    """Run all Cal.com API tests in sequence to maintain context"""
    for test_config in TOOL_TESTS:
        # Skip marked tests
        if test_config.get("skip", False):
            print(f"Skipping test {test_config['name']}: marked to skip")
            continue

        missing_deps = []
        for dep in test_config.get("depends_on", []):
            if dep not in context:
                missing_deps.append(dep)

        if missing_deps:
            print(
                f"Skipping test {test_config['name']}: missing dependencies {', '.join(missing_deps)}"
            )
            continue

        await run_cal_test(client, test_config, context)


async def run_cal_test(client, test_config, context):
    """Run a single Cal.com API test"""
    tool_name = test_config["name"]
    expected_keywords = test_config["expected_keywords"]
    description = test_config["description"]

    # Format args using context
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

    if "error_message" in response.lower():
        pytest.fail(f"{tool_name}: API error: {response}")

    for keyword in expected_keywords:
        assert (
            keyword.lower() in response.lower()
        ), f"{tool_name}: Expected keyword '{keyword}' not found in response: {response}"

    if "regex_extractors" in test_config:
        for key, pattern in test_config["regex_extractors"].items():
            match = re.search(pattern, response, re.DOTALL)
            if match:
                # Handle multiple capture groups
                for group_idx in range(1, len(match.groups()) + 1):
                    if match.group(group_idx):
                        context[key] = match.group(group_idx).strip()
                        break

    print(f"✅ {tool_name.replace('_', ' ').title()} test completed")
    return context
