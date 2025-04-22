import pytest
import json
import uuid
from datetime import datetime

# Global variables to store created IDs
created_workbook_id = None
current_date = datetime.now().strftime("%Y-%m-%d")


@pytest.mark.asyncio
async def test_create_workbook(client):
    """Test creating a new Excel workbook.

    Verifies that a workbook is created successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_workbook_id
    workbook_name = f"Test Workbook {str(uuid.uuid4())}.xlsx"

    response = await client.process_query(
        f"Use the create_workbook tool to create a new Excel workbook named '{workbook_name}'. "
        "If successful, start your response with 'Workbook created successfully' and include the file ID. "
        "Your response for ID should be in format File ID: <id>"
    )

    assert (
        "workbook created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_workbook"

    # Extract workbook id from response
    try:
        created_workbook_id = response.lower().split("file id: ")[1].split()[0]
        print(f"Created workbook ID: {created_workbook_id}")
    except IndexError:
        pytest.fail("Could not extract workbook ID from response")

    print(f"Response: {response}")
    print("✅ create_workbook passed.")

    return created_workbook_id


@pytest.mark.asyncio
async def test_list_worksheets(client):
    """Test listing worksheets in an Excel workbook.

    Verifies that worksheets are listed successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_workbook_id

    if not created_workbook_id:
        created_workbook_id = await test_create_workbook(client)

    response = await client.process_query(
        f"Use the list_worksheets tool to list all worksheets in the Excel workbook with ID {created_workbook_id}. "
        "If successful, start your response with 'Found worksheets' and then list them."
    )

    assert (
        "found worksheets" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_worksheets"

    print(f"Response: {response}")
    print("✅ list_worksheets passed.")


@pytest.mark.asyncio
async def test_create_worksheet(client):
    """Test creating a new worksheet in an Excel workbook.

    Verifies that a worksheet is created successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_workbook_id

    if not created_workbook_id:
        created_workbook_id = await test_create_workbook(client)

    worksheet_name = f"Test Sheet {str(uuid.uuid4())[:8]}"

    response = await client.process_query(
        f"Use the create_worksheet tool to create a new worksheet named '{worksheet_name}' "
        f"in the Excel workbook with ID {created_workbook_id}. "
        "If successful, start your response with 'Worksheet created successfully'."
    )

    assert (
        "worksheet created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_worksheet"

    print(f"Response: {response}")
    print("✅ create_worksheet passed.")

    return worksheet_name


@pytest.mark.asyncio
async def test_update_cells(client):
    """Test updating cell values in a worksheet.

    Verifies that cell values are updated successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_workbook_id

    if not created_workbook_id:
        created_workbook_id = await test_create_workbook(client)

    worksheet_name = await test_create_worksheet(client)

    values = [
        ["Name", "Age", "City"],
        ["John Doe", 30, "New York"],
        ["Jane Smith", 25, "San Francisco"],
    ]

    response = await client.process_query(
        f"Use the update_cells tool to update the range A1:C3 in worksheet '{worksheet_name}' "
        f"of the Excel workbook with ID {created_workbook_id} with the following values: "
        f"{json.dumps(values)}. "
        "If successful, start your response with 'Cells updated successfully'."
    )

    assert (
        "cells updated successfully" in response.lower()
        or "successfully updated range" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_cells"

    print(f"Response: {response}")
    print("✅ update_cells passed.")


@pytest.mark.asyncio
async def test_read_worksheet(client):
    """Test reading data from a worksheet.

    Verifies that worksheet data is read successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_workbook_id

    if not created_workbook_id:
        created_workbook_id = await test_create_workbook(client)
        worksheet_name = await test_create_worksheet(client)
        await test_update_cells(client)
    else:
        # Try to use last created worksheet
        try:
            worksheet_name = await test_create_worksheet(client)
            await test_update_cells(client)
        except:
            pytest.skip(
                "Could not create worksheet or update cells, cannot proceed with read test"
            )

    response = await client.process_query(
        f"Use the read_worksheet tool to read data from worksheet '{worksheet_name}' "
        f"in the Excel workbook with ID {created_workbook_id}. "
        "If successful, start your response with 'Data from worksheet' and display the data."
    )

    assert (
        "data from worksheet" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from read_worksheet"

    print(f"Response: {response}")
    print("✅ read_worksheet passed.")


@pytest.mark.asyncio
async def test_add_formula(client):
    """Test adding a formula to a cell in a worksheet.

    Verifies that a formula is added successfully.

    Args:
        client: The test client fixture for the guMCP server.
    """
    global created_workbook_id

    if not created_workbook_id:
        created_workbook_id = await test_create_workbook(client)
        worksheet_name = await test_create_worksheet(client)
        await test_update_cells(client)
    else:
        # Try to use last created worksheet
        try:
            worksheet_name = await test_create_worksheet(client)
            await test_update_cells(client)
        except:
            pytest.skip(
                "Could not create worksheet or update cells, cannot proceed with formula test"
            )

    formula = "=SUM(B2:B3)"

    response = await client.process_query(
        f"Use the add_formula tool to add the formula '{formula}' to cell B4 "
        f"in worksheet '{worksheet_name}' of the Excel workbook with ID {created_workbook_id}. "
        "If successful, start your response with 'Formula added successfully'."
    )

    assert (
        "formula added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_formula"

    print(f"Response: {response}")
    print("✅ add_formula passed.")


@pytest.mark.asyncio
async def test_excel_workflow(client):
    """Test a complete Excel workflow.

    Creates a workbook, adds a worksheet, updates cells, and reads data.

    Args:
        client: The test client fixture for the guMCP server.
    """
    # Create a new workbook
    workbook_name = f"Workflow Test {str(uuid.uuid4())}.xlsx"

    create_response = await client.process_query(
        f"Use the create_workbook tool to create a new Excel workbook named '{workbook_name}'. "
        "If successful, include the file ID."
    )

    # Extract workbook id from response
    try:
        workbook_id = create_response.lower().split("file id: ")[1].split()[0]
    except IndexError:
        workbook_id = None

    if not workbook_id:
        pytest.fail("Could not create workbook for workflow test")

    # Create a worksheet
    worksheet_name = "Sales Data"

    await client.process_query(
        f"Use the create_worksheet tool to create a new worksheet named '{worksheet_name}' "
        f"in the Excel workbook with ID {workbook_id}."
    )

    # Add data to the worksheet
    values = [
        ["Product", "Quantity", "Price", "Total"],
        ["Widget A", 10, 25, ""],
        ["Widget B", 5, 30, ""],
        ["Widget C", 8, 15, ""],
    ]

    await client.process_query(
        f"Use the update_cells tool to update the range A1:D4 in worksheet '{worksheet_name}' "
        f"of the Excel workbook with ID {workbook_id} with the following values: "
        f"{json.dumps(values)}."
    )

    # Add formulas for totals
    await client.process_query(
        f"Use the add_formula tool to add the formula '=B2*C2' to cell D2 "
        f"in worksheet '{worksheet_name}' of the Excel workbook with ID {workbook_id}."
    )

    await client.process_query(
        f"Use the add_formula tool to add the formula '=B3*C3' to cell D3 "
        f"in worksheet '{worksheet_name}' of the Excel workbook with ID {workbook_id}."
    )

    await client.process_query(
        f"Use the add_formula tool to add the formula '=B4*C4' to cell D4 "
        f"in worksheet '{worksheet_name}' of the Excel workbook with ID {workbook_id}."
    )

    # Add a sum formula
    await client.process_query(
        f"Use the add_formula tool to add the formula '=SUM(D2:D4)' to cell D5 "
        f"in worksheet '{worksheet_name}' of the Excel workbook with ID {workbook_id}."
    )

    # Read the final data
    read_response = await client.process_query(
        f"Use the read_worksheet tool to read data from worksheet '{worksheet_name}' "
        f"in the Excel workbook with ID {workbook_id}."
    )

    assert (
        "total" in read_response.lower()
    ), "Expected data not found in final worksheet"

    print("✅ Excel workflow test passed.")
