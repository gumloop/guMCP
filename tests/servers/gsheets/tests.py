import pytest
import uuid
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


# Shared context dictionary at module level
SHARED_CONTEXT = {}

TOOL_TESTS = [
    {
        "name": "create-sheet",
        "args_template": 'with title="MCP Test Sheet {random_id}"',
        "expected_keywords": ["created_sheet_id"],
        "regex_extractors": {"created_sheet_id": r"created_sheet_id:\s*([^\s]+)"},
        "description": "create a new Google Sheet and extract its ID",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "get-spreadsheet-info",
        "args_template": 'with spreadsheet_url="https://docs.google.com/spreadsheets/d/{created_sheet_id}/edit"',
        "expected_keywords": ["spreadsheet_id"],
        "regex_extractors": {"spreadsheet_id": r"spreadsheet_id:\s*([^\s]+)"},
        "description": "get metadata for spreadsheet and return spreadsheet_id i.e spreadsheet_id: <spreadsheet_id>",
        "depends_on": ["created_sheet_id"],
    },
    {
        "name": "get-sheet-names",
        "args_template": 'with spreadsheet_url="https://docs.google.com/spreadsheets/d/{created_sheet_id}/edit"',
        "expected_keywords": ["sheet_names"],
        "regex_extractors": {"sheet_names": r"sheet_names:\s*(\w+)"},
        "description": "list all sheet names in a spreadsheet and return the first one as string and not as list",
        "depends_on": ["created_sheet_id"],
    },
    {
        "name": "batch-update",
        "args_template": 'with spreadsheet_url="https://docs.google.com/spreadsheets/d/{created_sheet_id}/edit" data=["range": "Sheet1!A1", "values": [["Updated!"]], "range": "Sheet1!B1", "values": [["Test {random_id}"]]]',
        "expected_keywords": ["totalUpdatedCells"],
        "regex_extractors": {"totalUpdatedCells": r"totalUpdatedCells\s*[:=]\s*(\d+)"},
        "description": "update multiple ranges in a spreadsheet",
        "depends_on": ["created_sheet_id"],
    },
    {
        "name": "batch-get",
        "args_template": 'with spreadsheet_url="https://docs.google.com/spreadsheets/d/{created_sheet_id}/edit" ranges=["Sheet1!A1:C1"]',
        "expected_keywords": ["spreadsheet_id"],
        "regex_extractors": {"spreadsheet_id": r"spreadsheet_id:\s*([^\s]+)"},
        "description": "get values from multiple ranges in a spreadsheet and return spreadsheet_id i.e spreadsheet_id: <spreadsheet_id>",
        "depends_on": ["created_sheet_id"],
    },
    {
        "name": "append-values",
        "args_template": 'with spreadsheet_url="https://docs.google.com/spreadsheets/d/{created_sheet_id}/edit" range="Sheet1!A1" values=[["New Row", 123, "Test {random_id}"]]',
        "expected_keywords": ["spreadsheet_id"],
        "regex_extractors": {"spreadsheet_id": r"spreadsheet_id:\s*([^\s]+)"},
        "description": "append values to a range in a spreadsheet and return spreadsheet_id i.e spreadsheet_id: <spreadsheet_id>",
        "depends_on": ["created_sheet_id"],
    },
    {
        "name": "lookup-row",
        "args_template": 'with spreadsheet_url="https://docs.google.com/spreadsheets/d/{created_sheet_id}/edit" range="Sheet1!A1:C10" value="New Row"',
        "expected_keywords": ["found_row"],
        "regex_extractors": {"found_row": r"found_row\[0\]:\s*([^\n]+)"},
        "description": "find a row by searching for a value and return any one row as string found_row: <found_row>",
        "depends_on": ["created_sheet_id"],
    },
    {
        "name": "clear-values",
        "args_template": 'with spreadsheet_url="https://docs.google.com/spreadsheets/d/{created_sheet_id}/edit" range="Sheet1!A10:C10"',
        "expected_keywords": ["cleared_range"],
        "regex_extractors": {"cleared_range": r"cleared_range:\s*([^\s]+)"},
        "description": "clear values from a range in a spreadsheet and return cleared_range, format cleared_range: Sheet1!A10:C10",
        "depends_on": ["created_sheet_id"],
    },
    {
        "name": "copy-sheet",
        "args_template": 'with source_spreadsheet_id="{created_sheet_id}" source_sheet_id=0 destination_spreadsheet_id="{created_sheet_id}"',
        "expected_keywords": ["sheet_id"],
        "regex_extractors": {"sheet_id": r"sheet_id:\s*(\d+)"},
        "description": "copy a sheet from one spreadsheet to another",
        "depends_on": ["created_sheet_id"],
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.asyncio
async def test_resources(client, context):
    """Test listing and reading Google Sheets resources"""
    response = await run_resources_test(client)
    return response


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_tool(client, context, test_config):
    """Test Google Sheets tools"""
    return await run_tool_test(client, context, test_config)
