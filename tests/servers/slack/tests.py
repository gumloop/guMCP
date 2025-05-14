import pytest
import random
import string
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


def random_id():
    """Generate a random ID string"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


# Shared context dictionary at module level
SHARED_CONTEXT = {
    "test_user_id": "U08L3MC1PPA",  # replace with the user ID of the user you want to test with
}

TOOL_TESTS = [
    {
        "name": "create_channel",
        "args_template": 'with name "testchannel{random_id}" is_private=False',
        "expected_keywords": ["channel_id"],
        "regex_extractors": {
            "channel_id": r"channel_id:\s*([A-Z0-9]+)",
        },
        "description": "Create a new Slack channel and return the channel id after you created it",
        "setup": lambda context: {"random_id": random_id()},
    },
    {
        "name": "add_user_to_channel",
        "args_template": "to channel with ID {channel_id} users {test_user_id}",
        "expected_keywords": ["ok"],
        "regex_extractors": {
            "ok": r"ok:\s*(true|yes)",
        },
        "description": "Invite user to the channel and return ok parameter from the response",
        "depends_on": ["channel_id", "test_user_id"],
    },
    {
        "name": "update_channel_topic",
        "args_template": 'for channel with ID {channel_id} with topic "Channel Topic {test_id}"',
        "expected_keywords": ["updated_topic"],
        "regex_extractors": {
            "updated_topic": r"updated_topic:\s*([^\s]+)",
        },
        "description": "Update the channel's topic and return the updated topic",
        "depends_on": ["channel_id"],
        "setup": lambda context: {"test_id": random_id()},
    },
    {
        "name": "update_channel_purpose",
        "args_template": 'for channel with ID {channel_id} with purpose "Channel Purpose {test_id}"',
        "expected_keywords": ["updated_purpose"],
        "regex_extractors": {
            "updated_purpose": r"updated_purpose:\s*([^\s]+)",
        },
        "description": "Update the channel's purpose and return the updated purpose",
        "depends_on": ["channel_id"],
        "setup": lambda context: {"test_id": random_id()},
    },
    {
        "name": "send_message",
        "args_template": 'to channel with ID {channel_id} with text "First message {test_id}"',
        "expected_keywords": ["message_ts"],
        "regex_extractors": {
            "message_ts": r"message_ts:\s*([0-9.]+)",
        },
        "description": "Send a message to the channel",
        "depends_on": ["channel_id"],
        "setup": lambda context: {"test_id": random_id()},
    },
    {
        "name": "read_messages",
        "args_template": "from channel with ID {channel_id}",
        "expected_keywords": ["messages_count"],
        "regex_extractors": {
            "messages_count": r"messages_count:\s*(\d+)",
        },
        "description": "Read messages from the channel",
        "depends_on": ["channel_id"],
    },
    {
        "name": "create_canvas",
        "args_template": 'in channel with ID {channel_id} with title "Canvas {test_id}" and blocks "This is a test canvas"',
        "expected_keywords": ["canvas_ts"],
        "regex_extractors": {
            "canvas_ts": r"canvas_ts:\s*([0-9.]+)",
        },
        "description": "Create a canvas in the channel",
        "depends_on": ["channel_id"],
        "setup": lambda context: {"test_id": random_id()},
    },
    {
        "name": "pin_message",
        "args_template": 'in channel with ID {channel_id} with timestamp "{message_ts}"',
        "expected_keywords": ["ok"],
        "regex_extractors": {
            "ok": r"ok:\s*(true|yes)",
        },
        "description": "Pin a message in the channel and return ok parameter from the response",
        "depends_on": ["channel_id", "message_ts"],
    },
    {
        "name": "list_pinned_items",
        "args_template": "for channel with ID {channel_id}",
        "expected_keywords": ["pinned_items_count"],
        "regex_extractors": {
            "pinned_items_count": r"(?:pinned_items_count|items):\s*(\d+)",
        },
        "description": "List pinned items in the channel and return the count of pinned items",
        "depends_on": ["channel_id"],
    },
    {
        "name": "react_to_message",
        "args_template": 'to message in channel with ID {channel_id} with timestamp "{message_ts}" with reaction "thumbsup"',
        "expected_keywords": ["reaction_added", "message_ts"],
        "regex_extractors": {
            "reaction_added": r"reaction_added:\s*(true|yes)",
            "message_ts": r"message_ts:\s*([0-9.]+)",
        },
        "description": "Add a reaction to a message",
        "depends_on": ["channel_id", "message_ts"],
    },
    {
        "name": "get_user_presence",
        "args_template": "for user {test_user_id}",
        "expected_keywords": ["presence", "user_id"],
        "regex_extractors": {
            "presence": r"presence:\s*(\w+)",
            "user_id": r"user_id:\s*([A-Z0-9]+)",
        },
        "description": "Check a user's online status",
        "depends_on": ["test_user_id"],
    },
    {
        "name": "unpin_message",
        "args_template": 'in channel with ID {channel_id} with timestamp "{message_ts}"',
        "expected_keywords": ["ok"],
        "regex_extractors": {
            "ok": r"ok:\s*(true|yes)",
        },
        "description": "Unpin a message from the channel and return ok parameter from the response",
        "depends_on": ["channel_id", "message_ts"],
    },
    {
        "name": "delete_message",
        "args_template": 'from channel with ID {channel_id} with timestamp "{message_ts}"',
        "expected_keywords": ["deleted_message_ts"],
        "regex_extractors": {
            "deleted_message_ts": r"deleted_message_ts:\s*([0-9.]+)",
        },
        "description": "Delete a message from the channel",
        "depends_on": ["channel_id", "message_ts"],
    },
    {
        "name": "remove_from_channel",
        "args_template": "with channel {channel_id} and user {test_user_id}",
        "expected_keywords": ["ok"],
        "regex_extractors": {
            "ok": r"ok:\s*(true|yes)",
        },
        "description": "Remove a user from the channel and return ok parameter from the response",
        "depends_on": ["channel_id", "test_user_id"],
    },
    # add user to channel
    {
        "name": "archive_channel",
        "args_template": "channel with ID {channel_id}",
        "expected_keywords": ["ok"],
        "regex_extractors": {
            "ok": r"ok:\s*(true|yes)",
        },
        "description": "Archive the created channel and return ok parameter from the response",
        "depends_on": ["channel_id"],
    },
    {
        "name": "list_users_in_channel",
        "args_template": "in channel with ID {channel_id}",
        "expected_keywords": ["user_count"],
        "regex_extractors": {
            "user_count": r"(?:user_count|users):\s*(\d+)",
        },
        "description": "List users in the channel and return the count of users",
        "depends_on": ["channel_id"],
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.asyncio
async def test_resources(client, context):
    """Test resources for Slack and extract channel and user information"""
    response = await run_resources_test(client)
    return response


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_slack_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)
