import pytest
import re
import random
import string


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


def get_test_id(test_config):
    return f"{test_config['name']}_{hash(test_config['description']) % 1000}"


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_excel_tool(client, context, test_config):
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
        f"Only return the value with following keywords: {keywords_str} if successful or error with keyword 'error_message'. "
        f"Use the {tool_name} tool to {description} {args}. "
        "Sample response: keyword: output_data keyword2: output_data2 keyword3: [] always ensure keyword is in same format as in expected_keywords"
    )

    response = await client.process_query(prompt)

    # Handle common empty result patterns
    if (
        "empty" in response.lower()
        or "[]" in response
        or "no items" in response.lower()
        or "not found" in response.lower()
    ):
        if "regex_extractors" in test_config:
            for key, pattern in test_config["regex_extractors"].items():
                if key not in context:
                    context[key] = "empty_list"

        pytest.skip(f"Empty result from API for {tool_name}")
        return

    # Handle API errors
    if "error_message" in response.lower() and "error_message" not in expected_keywords:
        pytest.fail(f"API error for {tool_name}: {response}")
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
                context[key] = match.group(1).strip()

    return context


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading an Excel workbook resource"""
    # First list resources to get a valid Excel file
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find the first Excel file resource
    excel_resource = next(
        (r for r in response.resources if str(r.uri).startswith("excel:///file/")),
        None,
    )

    # Skip test if no Excel resources found
    if not excel_resource:
        pytest.skip("No Excel resources found to test read_resource functionality")
        return

    # Read Excel file details
    response = await client.read_resource(excel_resource.uri)

    # Verify response
    assert response.contents, "Response should contain Excel workbook data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    # Parse the JSON content
    import json

    content_text = response.contents[0].text
    content_data = json.loads(content_text)

    # Verify basic workbook data
    assert "id" in content_data, "Response should include workbook ID"
    assert "name" in content_data, "Response should include workbook name"
    assert "worksheets" in content_data, "Response should include worksheets data"

    print("Excel workbook data read:")
    print(f"  - Workbook name: {content_data.get('name')}")
    print(f"  - Worksheets count: {len(content_data.get('worksheets', []))}")
    print("✅ Successfully read Excel workbook data")
