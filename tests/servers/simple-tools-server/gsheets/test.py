import pytest

EXAMPLE_URL = "https://docs.google.com/spreadsheets/d/<YOUR_SPREADSHEET_ID>/edit"


@pytest.mark.asyncio
async def test_create_sheet(client):
    """Test creating a new spreadsheet"""
    response = await client.call_tool("create-sheet", {"title": "MCP Test Sheet"})

    assert (
        response and "Created new spreadsheet" in response[0].text
    ), f"Create failed: {response}"
    print(
        f"✅ Created sheet successfully. Response message from API: '{response[0].text}'"
    )


@pytest.mark.asyncio
async def test_get_spreadsheet_info(client):
    """Test reading spreadsheet metadata"""
    response = await client.call_tool(
        "get-spreadsheet-info", {"spreadsheet_url": EXAMPLE_URL}
    )

    assert (
        "properties" in response[0].text.lower()
    ), f"Missing properties in response: {response}"
    print("✅ Spreadsheet info retrieved")


@pytest.mark.asyncio
async def test_get_sheet_names(client):
    """Test retrieving all sheet names"""
    response = await client.call_tool(
        "get-sheet-names", {"spreadsheet_url": EXAMPLE_URL}
    )

    assert response and len(response[0].text.strip()) > 0, "No sheet names returned"
    print(f"Sheets: {response[0].text}")
    print("✅ Sheet names fetched")


@pytest.mark.asyncio
async def test_batch_get(client):
    """Test batch-get tool"""
    response = await client.call_tool(
        "batch-get", {"spreadsheet_url": EXAMPLE_URL, "ranges": ["Sheet1!A1:C1"]}
    )

    assert response and "Sheet1" in response[0].text, f"Batch get failed: {response}"
    print("✅ Batch get worked")


@pytest.mark.asyncio
async def test_batch_update(client):
    """Test batch updating values"""
    response = await client.call_tool(
        "batch-update",
        {
            "spreadsheet_url": EXAMPLE_URL,
            "data": [{"range": "Sheet1!A1", "values": [["Updated!"]]}],
        },
    )

    assert "Batch update" in response[0].text or "successful" in response[0].text
    print("✅ Batch update success")


@pytest.mark.asyncio
async def test_append_values(client):
    """Test appending values"""
    response = await client.call_tool(
        "append-values",
        {
            "spreadsheet_url": EXAMPLE_URL,
            "range": "Sheet1!A1",
            "values": [["New Row", 123]],
        },
    )

    assert "appended" in response[0].text.lower()
    print("✅ Append successful")


@pytest.mark.asyncio
async def test_lookup_row(client):
    """Test looking up a row by value"""
    response = await client.call_tool(
        "lookup-row",
        {"spreadsheet_url": EXAMPLE_URL, "range": "Sheet1!A1:C10", "value": "New Row"},
    )

    assert "Found row" in response[0].text or "not found" in response[0].text
    print("✅ Lookup works")


@pytest.mark.asyncio
async def test_clear_values(client):
    """Test clearing a range"""
    response = await client.call_tool(
        "clear-values", {"spreadsheet_url": EXAMPLE_URL, "range": "Sheet1!A1:C1"}
    )

    assert "cleared" in response[0].text.lower()
    print("✅ Clear successful")


@pytest.mark.asyncio
async def test_copy_sheet(client):
    """Test copying a sheet"""
    response = await client.call_tool(
        "copy-sheet",
        {
            "source_spreadsheet_id": "<SOURCE_ID>",
            "source_sheet_id": 0,  # Replace with real sheetId
            "destination_spreadsheet_id": "<DEST_ID>",
        },
    )

    assert (
        "copied" in response[0].text.lower()
        or "spreadsheet id" in response[0].text.lower()
    )
    print("✅ Copy sheet worked")
