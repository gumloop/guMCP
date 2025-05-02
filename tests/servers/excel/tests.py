import pytest
import re
import random
import string
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


TOOL_TESTS = [
    {
        "name": "create_workbook",
        "args_template": 'with name="Test Workbook-{random_id}"',
        "expected_keywords": ["created_file_id"],
        "regex_extractors": {
            "created_file_id": r'"?created_file_id"?[:\s]+([^,\s\n"]+)'
        },
        "description": "create a new Excel workbook and return its ID",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    # Basic file and workbook operations
    {
        "name": "list_worksheets",
        "args_template": 'with file_id="{created_file_id}"',
        "expected_keywords": ["worksheet_name"],
        "regex_extractors": {"worksheet_name": r"worksheet_name:\s*([\w\s\d-]+)"},
        "description": "list all worksheets in an Excel workbook and return the name of any one worksheet",
        "depends_on": ["created_file_id"],
    },
    {
        "name": "add_worksheet",
        "args_template": 'with file_id="{created_file_id}" name="Test Worksheet-{random_id}"',
        "expected_keywords": ["name"],
        "regex_extractors": {"new_worksheet_name": r'"name":\s*"([^"]+)"'},
        "description": "create a new worksheet in the Excel workbook and return the name of the worksheet",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
        "depends_on": ["created_file_id"],
    },
    # Basic data operations - commented out as per user preference
    {
        "name": "update_cells",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" range="A1:B3" values=[["Header 1", "Header 2"], ["Value 1", "Value 2"], ["Value 3", "Value 4"]]',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r'"?file_id"?[:\s]+([^,\s\n"]+)'},
        "description": "update cell values in the worksheet and return the file_id",
        "depends_on": ["new_worksheet_name", "created_file_id"],
    },
    {
        "name": "read_worksheet",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}"',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r'"?file_id"?[:\s]+([^,\s\n"]+)'},
        "description": "read data from the worksheet and return file_id",
        "depends_on": ["new_worksheet_name", "created_file_id"],
    },
    {
        "name": "add_row",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" values=["New Value 1", "New Value 2"]',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r'"?file_id"?[:\s]+([^,\s\n"]+)'},
        "description": "add a row to the end of the worksheet and return the file_id",
        "depends_on": ["new_worksheet_name", "created_file_id"],
    },
    {
        "name": "update_row",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" row_index=2 values={{"Header 1": "Updated Value 1", "Header 2": "Updated Value 2"}}',
        "expected_keywords": ["updated"],
        "description": "update a specific row in the worksheet and return the updated row",
        "depends_on": ["new_worksheet_name", "created_file_id"],
    },
    {
        "name": "add_formula",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" cell="C2" formula="=SUM(A2:B2)"',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r'"?file_id"?[:\s]+([^,\s\n"]+)'},
        "description": "add a formula to a cell in the worksheet and return the file_id",
        "depends_on": ["new_worksheet_name", "created_file_id"],
    },
    # Table operations
    {
        "name": "add_table",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" range="D1:E3" name="TestTable-{random_id}"',
        "expected_keywords": ["table_name"],
        "regex_extractors": {"table_name": r'"name":\s*"([^"]+)"'},
        "description": "create a new table in the worksheet and return table_name",
        "depends_on": ["new_worksheet_name", "created_file_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "list_tables",
        "args_template": 'with file_id="{created_file_id}"',
        "expected_keywords": ["table_name"],
        "regex_extractors": {"table_name": r'"name":\s*"([^"]+)"'},
        "description": "list all tables in the Excel workbook and return table_name",
        "depends_on": ["created_file_id"],
    },
    {
        "name": "get_table",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" table_name="{table_name}"',
        "expected_keywords": ["address"],
        "description": "get table metadata and return address",
        "depends_on": ["new_worksheet_name", "table_name", "created_file_id"],
    },
    {
        "name": "list_table_rows",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" table_name="{table_name}"',
        "expected_keywords": ["value"],
        "description": "list rows in the table and return values",
        "depends_on": ["new_worksheet_name", "table_name", "created_file_id"],
    },
    {
        "name": "add_table_column",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" table_name="{table_name}" column_name="NewColumn-{random_id}"',
        "expected_keywords": ["Successfully"],
        "description": "add a column to the table and return Successfully",
        "depends_on": ["new_worksheet_name", "table_name", "created_file_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    # Search and modify operations
    {
        "name": "find_row",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" column="Header 1" value="Updated Value 1"',
        "expected_keywords": ["row_index"],
        "regex_extractors": {"row_index": r'"?row_index"?[:\s]+([^,\s\n"]+)'},
        "description": "find a row by column value",
        "depends_on": ["new_worksheet_name", "created_file_id"],
    },
    {
        "name": "find_or_create_row",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" search_column="Header 1" search_value="Unique Value-{random_id}" values={{"Header 1": "Unique Value-{random_id}", "Header 2": "Associated Value"}}',
        "expected_keywords": ["created"],
        "description": "find a row by column value or create it if not found",
        "depends_on": ["new_worksheet_name", "created_file_id"],
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "delete_worksheet_row",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" row_index=4',
        "expected_keywords": ["Successfully"],
        "description": "delete a row from the worksheet and return Successfully",
        "depends_on": ["new_worksheet_name", "created_file_id"],
    },
    # Cleanup operations
    {
        "name": "delete_table",
        "args_template": 'with file_id="{created_file_id}" worksheet_name="{new_worksheet_name}" table_name="{table_name}"',
        "expected_keywords": ["Successfully"],
        "description": "delete the table from the worksheet and return Successfully",
        "depends_on": ["new_worksheet_name", "table_name", "created_file_id"],
    },
    {
        "name": "download_workbook",
        "args_template": 'with file_id="{created_file_id}"',
        "expected_keywords": ["url"],
        "regex_extractors": {"url": r'"url":\s*"([^"]+)"'},
        "description": "get a download URL for the workbook and return downloadUrl and nothing else",
        "depends_on": ["created_file_id"],
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.asyncio
async def test_resources(client):
    return await run_resources_test(client)


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_excel_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)
