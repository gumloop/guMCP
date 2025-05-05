import pytest
import uuid
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test

# Global configuration - set these before running tests
PROJECT_REF = ""  # Replace with your actual project reference ID
SUPABASE_KEY = ""  # Replace with your service_role key

TOOL_TESTS = [
    {
        "name": "list_projects",
        "expected_keywords": ["projects"],
        "regex_extractors": {
            "project_ref": r'"?ref"?[:\s]+"?([^"]+)"?',
        },
        "description": "list Supabase projects and extract a project reference ID",
    },
    {
        "name": "get_project",
        "args_template": 'with ref="{0}"'.format(PROJECT_REF),
        "expected_keywords": ["project"],
        "regex_extractors": {
            "project_name": r'"?name"?[:\s]+"?([^"]+)"?',
        },
        "description": "get details of a specific Supabase project",
    },
    {
        "name": "create_storage_bucket",
        "args_template": (
            'with project_ref="{0}" name=test-bucket-{{random_id}} '
            'supabase_key="{1}"'
        ).format(PROJECT_REF, SUPABASE_KEY),
        "expected_keywords": ["bucket"],
        "regex_extractors": {
            "bucket_name": r'"?name"?[:\s]+"?([^\"]+)"?',
        },
        "description": (
            "create a new storage bucket in Supabase and extract the bucket ID "
            "with project_ref={0} name=test-bucket-{{random_id}} supabase_key={1}"
        ).format(PROJECT_REF, SUPABASE_KEY),
        "setup": lambda context: {"random_id": str(uuid.uuid4().hex[:8])},
    },
    {
        "name": "list_storage_buckets",
        "args_template": 'with project_ref="{0}" supabase_key="{1}"'.format(
            PROJECT_REF, SUPABASE_KEY
        ),
        "expected_keywords": ["buckets"],
        "regex_extractors": {
            "bucket_id": r'"?id"?[:\s]+"?([^"]+)"?',
        },
        "description": "list all storage buckets in a Supabase project",
    },
    {
        "name": "list_organizations",
        "args_template": "",
        "expected_keywords": ["id"],
        "regex_extractors": {
            "organization_id": r'"?id"?[:\s]+"?([^"]+)"?',
        },
        "description": "list Supabase organizations and extract an organization ID",
    },
    {
        "name": "get_storage_bucket",
        "args_template": 'bucket_id="{bucket_id}"',
        "expected_keywords": ["bucket"],
        "regex_extractors": {
            "bucket_info": r'"?public"?[:\s]+(true|false)',
        },
        "description": "get details about a specific storage bucket with project_ref={0} supabase_key={1}".format(
            PROJECT_REF, SUPABASE_KEY
        ),
        "depends_on": ["bucket_id"],
    },
    {
        "name": "delete_storage_bucket",
        "args_template": (
            'with project_ref="{0}" bucket_id="{{bucket_id}}" ' 'supabase_key="{1}"'
        ).format(PROJECT_REF, SUPABASE_KEY),
        "expected_keywords": ["deleted"],
        "description": "delete a storage bucket from Supabase",
        "depends_on": ["bucket_id"],
    },
    {
        "name": "create_project",
        "args_template": (
            'with org_id={organization_id} name="test-project-{{random_id}}" db_pass="{{random_db_pass}}" region="{{random_region}}"'
        ),
        "expected_keywords": ["project", "ref"],
        "regex_extractors": {
            "project_ref": r'"?ref"?[:\s]+"?([^"\s]+)"?',
        },
        "description": "create a new Supabase project with random values and extract the project reference ID",
        "setup": lambda context: {
            "random_id": str(uuid.uuid4().hex[:8]),
            "random_db_pass": uuid.uuid4().hex,
            "random_region": "us-east-1",  # or random.choice from a list of valid regions
        },
        "depends_on": ["organization_id"],
    },
    # DATA MANAGEMENT TOOLS TESTS
    # NOTE: You need to have a 'student' table created in your project before running these tests
    # with columns: id (bigint), created_at (timestamp with timezone), name (varchar), age (bigint), city (text)
    {
        "name": "read_table_data",
        "args_template": 'with project_ref="{0}" supabase_key="{1}" table_name="student" select="*"'.format(
            PROJECT_REF, SUPABASE_KEY
        ),
        "expected_keywords": ["rows", "student"],
        "description": "read data from the student table",
    },
    {
        "name": "create_table_data",
        "args_template": (
            'with project_ref="{0}" supabase_key="{1}" table_name="student" '
            'data="name": "Test Student {{random_id}}", "age": 21, "city": "Test City"'
        ).format(PROJECT_REF, SUPABASE_KEY),
        "expected_keywords": ["inserted", "student"],
        "regex_extractors": {
            "student_id": r'"?id"?[:\s]+(\d+)',
        },
        "description": "insert a new row into the student table",
        "setup": lambda context: {"random_id": str(uuid.uuid4().hex[:8])},
    },
    {
        "name": "update_table_data",
        "args_template": (
            'with project_ref="{0}" supabase_key="{1}" table_name="student" '
            'data="city": "Updated City" filters="id": {{student_id}}'
        ).format(PROJECT_REF, SUPABASE_KEY),
        "expected_keywords": ["updated", "student"],
        "description": "update a row in the student table",
        "depends_on": ["student_id"],
    },
    {
        "name": "delete_table_data",
        "args_template": (
            'with project_ref="{0}" supabase_key="{1}" table_name="student" '
            'filters="id": {{student_id}}'
        ).format(PROJECT_REF, SUPABASE_KEY),
        "expected_keywords": ["success"],
        "description": "delete a row from the student table",
        "depends_on": ["student_id"],
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_supabase_tool(client, context, test_config):
    print(f"Test config: {SHARED_CONTEXT}")
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response
