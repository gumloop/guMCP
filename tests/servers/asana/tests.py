import pytest
import random
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


TOOL_TESTS = [
    # Read operations that provide initial IDs
    {
        "name": "get_workspaces",
        "args_template": "",
        "expected_keywords": ["workspace_data_gid"],
        "regex_extractors": {
            "workspace_id": r'(?:"?workspace_data_gid"?[:\s]*)?(\d{6,})'
        },
        "description": "list workspaces and extract the first workspace ID",
    },
    {
        "name": "get_me",
        "args_template": "",
        "expected_keywords": ["user_data_gid"],
        "regex_extractors": {"user_id": r'(?:"?user_data_gid"?[:\s]*)?(\d{6,})'},
        "description": "get current user information and extract user ID and name",
    },
    # Create operations
    {
        "name": "create_project",
        "args_template": 'with workspace_id="{workspace_id}" name="Test Project-{random_id}"',
        "expected_keywords": ["project_data_gid"],
        "regex_extractors": {"project_id": r'(?:"?project_data_gid"?[:\s]*)?(\d{6,})'},
        "description": "create a new project in Asana and return its ID",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["workspace_id"],
    },
    {
        "name": "create_task",
        "args_template": 'with name="Test Task-{random_id}" project_id="{project_id}" notes="Test task notes" completed=false',
        "expected_keywords": ["task_data_gid"],
        "regex_extractors": {"task_id": r'(?:"?task_data_gid"?[:\s]*)?(\d{6,})'},
        "description": "create a new task in the project and return its ID",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["project_id"],
    },
    {
        "name": "create_section",
        "args_template": 'with project_id="{project_id}" name="Test Section-{random_id}"',
        "expected_keywords": ["section_data_gid"],
        "regex_extractors": {"section_id": r'(?:"?section_data_gid"?[:\s]*)?(\d{6,})'},
        "description": "create a new section in the project and return its ID",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["project_id"],
    },
    {
        "name": "create_tag",
        "args_template": 'with workspace_id="{workspace_id}" name="Test Tag-{random_id}"',
        "expected_keywords": ["tag_data_gid"],
        "regex_extractors": {"tag_id": r'(?:"?tag_data_gid"?[:\s]*)?(\d{6,})'},
        "description": "create a new tag in the workspace and return its ID",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["workspace_id"],
    },
    # Read operations that depend on created resources
    {
        "name": "get_project",
        "args_template": 'with project_id="{project_id}"',
        "expected_keywords": ["name", "gid"],
        "description": "get project details by ID",
        "depends_on": ["project_id"],
    },
    {
        "name": "get_task",
        "args_template": 'with task_id="{task_id}"',
        "expected_keywords": ["name", "gid"],
        "description": "get task details by ID",
        "depends_on": ["task_id"],
    },
    {
        "name": "get_sections",
        "args_template": 'with project_id="{project_id}"',
        "expected_keywords": ["gid"],
        "description": "list sections in the project",
        "depends_on": ["project_id"],
    },
    {
        "name": "get_tags",
        "args_template": 'with workspace_id="{workspace_id}"',
        "expected_keywords": ["gid"],
        "description": "list tags in the workspace",
        "depends_on": ["workspace_id"],
    },
    {
        "name": "get_users",
        "args_template": 'with workspace_id="{workspace_id}"',
        "expected_keywords": ["gid"],
        "description": "list users in the workspace",
        "depends_on": ["workspace_id"],
    },
    {
        "name": "get_user",
        "args_template": 'with user_id="{user_id}"',
        "expected_keywords": ["gid", "name"],
        "description": "get user details by ID",
        "depends_on": ["user_id"],
    },
    {
        "name": "get_projects",
        "args_template": 'with workspace_id="{workspace_id}"',
        "expected_keywords": ["gid", "name"],
        "description": "list projects in the workspace",
        "depends_on": ["workspace_id"],
    },
    {
        "name": "get_tasks",
        "args_template": 'with project_id="{project_id}"',
        "expected_keywords": ["gid", "name"],
        "description": "list tasks in the project",
        "depends_on": ["project_id"],
    },
    # Update operations
    {
        "name": "update_project",
        "args_template": 'with project_id="{project_id}" name="Updated Project-{random_id}"',
        "expected_keywords": ["success"],
        "description": "update project name",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["project_id"],
    },
    {
        "name": "update_task",
        "args_template": 'with task_id="{task_id}" name="Updated Task-{random_id}" notes="Updated task notes"',
        "expected_keywords": ["success"],
        "description": "update task name and notes",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["task_id"],
    },
    {
        "name": "mark_task_complete",
        "args_template": 'with task_id="{task_id}"',
        "expected_keywords": ["success"],
        "description": "mark task as complete",
        "depends_on": ["task_id"],
    },
    {
        "name": "mark_task_incomplete",
        "args_template": 'with task_id="{task_id}"',
        "expected_keywords": ["success"],
        "description": "mark task as incomplete",
        "depends_on": ["task_id"],
    },
    {
        "name": "add_tag_to_task",
        "args_template": 'with task_id="{task_id}" tag_id="{tag_id}"',
        "expected_keywords": ["success"],
        "description": "add tag to task",
        "depends_on": ["task_id", "tag_id"],
    },
    {
        "name": "add_task_to_section",
        "args_template": 'with section_id="{section_id}" task_id="{task_id}"',
        "expected_keywords": ["success"],
        "description": "add task to section",
        "depends_on": ["section_id", "task_id"],
    },
    {
        "name": "add_follower_to_task",
        "args_template": 'with task_id="{task_id}" user_id="{user_id}"',
        "expected_keywords": ["success"],
        "description": "add follower to task",
        "depends_on": ["task_id", "user_id"],
    },
    {
        "name": "assign_task",
        "args_template": 'with task_id="{task_id}" user_id="{user_id}"',
        "expected_keywords": ["success"],
        "description": "assign task to user",
        "depends_on": ["task_id", "user_id"],
    },
    {
        "name": "add_task_to_project",
        "args_template": 'with task_id="{task_id}" project_id="{project_id}"',
        "expected_keywords": ["success"],
        "description": "add task to project",
        "depends_on": ["task_id", "project_id"],
    },
    {
        "name": "duplicate_task",
        "args_template": 'with task_id="{task_id}" name="Duplicated Task-{random_id}"',
        "expected_keywords": ["success"],
        "description": "duplicate an existing task",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["task_id"],
    },
    {
        "name": "create_attachment",
        "args_template": 'with parent_id="{task_id}" url="https://example.com/test.txt" name="Test Attachment" connect_to_app=false',
        "expected_keywords": ["success"],
        "description": "create a new attachment for a task",
        "depends_on": ["task_id"],
    },
    {
        "name": "add_subtask",
        "args_template": 'with parent_task_id="{task_id}" name="Test Subtask-{random_id}" notes="Test subtask notes"',
        "expected_keywords": ["success"],
        "description": "create a new subtask for an existing task",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["task_id"],
    },
    # Delete operations
    {
        "name": "remove_tag_from_task",
        "args_template": 'with task_id="{task_id}" tag_id="{tag_id}"',
        "expected_keywords": ["success"],
        "description": "remove tag from task",
        "depends_on": ["task_id", "tag_id"],
    },
    {
        "name": "remove_follower_from_task",
        "args_template": 'with task_id="{task_id}" user_id="{user_id}"',
        "expected_keywords": ["success"],
        "description": "remove follower from task",
        "depends_on": ["task_id", "user_id"],
    },
    {
        "name": "unassign_task",
        "args_template": 'with task_id="{task_id}"',
        "expected_keywords": ["success"],
        "description": "unassign task",
        "depends_on": ["task_id"],
    },
    {
        "name": "remove_task_from_project",
        "args_template": 'with task_id="{task_id}" project_id="{project_id}"',
        "expected_keywords": ["success"],
        "description": "remove task from project",
        "depends_on": ["task_id", "project_id"],
    },
    {
        "name": "delete_task",
        "args_template": 'with task_id="{task_id}"',
        "expected_keywords": ["success"],
        "description": "delete task",
        "depends_on": ["task_id"],
    },
    {
        "name": "delete_section",
        "args_template": 'with section_id="{section_id}"',
        "expected_keywords": ["success"],
        "description": "delete section",
        "depends_on": ["section_id"],
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_asana_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response
