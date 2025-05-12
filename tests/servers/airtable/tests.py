import pytest
import uuid
import json
import time
import random
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


# Shared context dictionary at module level
SHARED_CONTEXT = {
    "workspace_id": "wspPLjVuXykz3YL9S",  # add your airtable workspace id
}

TOOL_TESTS = [
    {
        "name": "create_base",
        "args_template": 'with name="Test Base {random_id}" description="guMCP Test Base" workspace_id="{workspace_id}" tables=[{{"name":"Test Table","description":"Test Table Description","fields":[{{"name":"Name","type":"singleLineText","description":"Primary field"}},{{"name":"Notes","type":"multilineText","description":"Notes field"}}]}}]',
        "expected_keywords": ["new_base_id"],
        "regex_extractors": {"new_base_id": r"new_base_id\s*:\s*(app\w+)"},
        "description": "create a new Airtable base and return new base id",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "list_bases",
        "args": "",
        "expected_keywords": ["base_id"],
        "regex_extractors": {"base_id": r"base_id\s*:\s*(app\w+)"},
        "description": "list all accessible Airtable bases and extract a base ID",
    },
    {
        "name": "create_table",
        "args_template": 'with base_id="{new_base_id}" table_name="Test Table {random_id}" description="Created by automated test" fields=[{{"name":"Primary Field","type":"singleLineText","description":"Primary field"}}]',
        "expected_keywords": ["new_table_id"],
        "regex_extractors": {"new_table_id": r"new_table_id\s*:\s*(tbl\w+)"},
        "description": "create a new table in a base",
        "depends_on": ["new_base_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "list_tables",
        "args_template": 'with base_id="{new_base_id}"',
        "expected_keywords": ["table_id"],
        "regex_extractors": {"table_id": r"table_id\s*:\s*(tbl\w+)"},
        "description": "list all tables in a given Airtable base and extract a table ID",
        "depends_on": ["new_base_id"],
    },
    {
        "name": "base_schema",
        "args_template": 'with base_id="{new_base_id}"',
        "expected_keywords": ["table_id"],
        "regex_extractors": {"table_id": r"table_id\s*:\s*(tbl\w+)"},
        "description": "get complete schema for all tables in a base and return any one table id",
        "depends_on": ["new_base_id"],
    },
    {
        "name": "create_field",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" field_name="Test Field {random_id}" field_type="singleLineText" description="Created by automated test"',
        "expected_keywords": ["field_id"],
        "regex_extractors": {"field_id": r"field_id\s*:\s*(fld\w+)"},
        "description": "add a new field to an existing table",
        "depends_on": ["new_base_id", "new_table_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_field",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" field_id="{field_id}" name="Updated Field {random_id}" description="Updated by automated test"',
        "expected_keywords": ["updated_field_id"],
        "regex_extractors": {"updated_field_id": r"updated_field_id\s*:\s*(fld\w+)"},
        "description": "update a field's metadata in a table and return field id",
        "depends_on": ["new_base_id", "new_table_id", "field_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_table",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" name="Updated Table {random_id}" description="Updated by automated test"',
        "expected_keywords": ["updated_table_id"],
        "regex_extractors": {"updated_table_id": r"updated_table_id\s*:\s*(tbl\w+)"},
        "description": "update an existing table's name and description and return table id",
        "depends_on": ["new_base_id", "new_table_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_records",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" records=[{{"fields": {{"Primary Field": "Batch Record {random_id}"}}}}]',
        "expected_keywords": ["batch_record_id"],
        "regex_extractors": {"batch_record_id": r"batch_record_id\s*:\s*(rec\w+)"},
        "description": "create multiple records in an Airtable table and extract first record ID",
        "depends_on": ["new_base_id", "new_table_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "read_records",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" max_records=5',
        "expected_keywords": ["record_id"],
        "regex_extractors": {"record_id": r"record_id\s*:\s*(rec\w+)"},
        "description": "read records from an Airtable table and extract a record ID",
        "depends_on": ["new_base_id", "new_table_id"],
    },
    {
        "name": "update_records",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" records=[{{"id":"{batch_record_id}","fields":{{"Primary Field":"Updated Record {random_id}"}}}}]',
        "expected_keywords": ["updated_record_id"],
        "regex_extractors": {"updated_record_id": r"updated_record_id\s*:\s*(rec\w+)"},
        "description": "update existing records in an Airtable table and return updated_record_id",
        "depends_on": ["new_base_id", "new_table_id", "batch_record_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "get_record",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" record_id="{batch_record_id}"',
        "expected_keywords": ["record_id"],
        "regex_extractors": {"record_id": r"record_id\s*:\s*(rec\w+)"},
        "description": "get a single record by its ID from a table and return record id",
        "depends_on": ["new_base_id", "new_table_id", "batch_record_id"],
    },
    {
        "name": "search_records",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" search_query="Batch Record"',
        "expected_keywords": ["found_records"],
        "regex_extractors": {"found_records": r"found_records\s*:\s*\[(.*?)\]"},
        "description": "search for records containing specific text in a table and return any record id",
        "depends_on": ["new_base_id", "new_table_id"],
    },
    {
        "name": "delete_records",
        "args_template": 'with base_id="{new_base_id}" table_id="{new_table_id}" record_ids=["{batch_record_id}"]',
        "expected_keywords": ["deleted_records_ids"],
        "regex_extractors": {
            "deleted_records_ids": r"deleted_records_ids\s*:\s*\[(.*?)\]"
        },
        "description": "delete one or more records from a table and return any one ids",
        "depends_on": ["new_base_id", "new_table_id", "batch_record_id"],
    },
    {
        "name": "delete_base",
        "args_template": 'with base_id="{new_base_id}"',
        "expected_keywords": ["deleted_base_id", "success"],
        "regex_extractors": {"deleted_base_id": r"deleted_base_id\s*:\s*(app\w+)"},
        "description": "delete a base",
        "depends_on": ["new_base_id"],
        "skip": True,
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.asyncio
async def test_resources(client):
    """Test listing bases and tables from Airtable"""
    return await run_resources_test(client)


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_airtable_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)
