import re
import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing teams and issues from Linear"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_team(client):
    """Test reading a team resource"""
    # First list resources to get a valid team ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first team resource
    team_resource = next(
        (r for r in response.resources if str(r.uri).startswith("linear://team/")),
        None,
    )
    assert team_resource, "No team resources found"

    # Read team details
    response = await client.read_resource(team_resource.uri)

    print("RESPONSE", response)

    assert response.contents, "Response should contain team data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Team data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read team data")


@pytest.mark.asyncio
async def test_search_issues(client):
    """Test searching for issues"""
    response = await client.process_query(
        "Use the search_issues tool to search for all issues. If you find any issues, start your response with 'Found issues:' and then list them."
    )

    # Verify search results
    assert (
        "found issues:" in response.lower()
    ), f"Search results should start with 'Found issues:': {response}"

    print("Search results:")
    print(f"\t{response}")
    print("✅ Search functionality working")


@pytest.mark.asyncio
async def test_create_issue(client):
    """Test creating an issue"""
    # First get a valid team ID
    response = await client.list_resources()
    team_resource = next(
        (r for r in response.resources if str(r.uri).startswith("linear://team/")),
        None,
    )
    assert team_resource, "No team resources found"
    team_id = str(team_resource.uri).replace("linear://team/", "")

    # Create test issue with a marker for easy ID extraction
    create_response = await client.process_query(
        f"Use the create_issue tool to create an issue with team_id '{team_id}', "
        "title 'Test Issue', description 'This is a test issue.', and priority 4. "
        "After creating the issue, output the ID in this exact format: 'ISSUE_ID:your-issue-id-here'"
    )

    print("Create issue response:")
    print(f"\t{create_response}")
    print("✅ Issue creation working")

    # Extract issue ID from the response using the marker
    issue_id_match = re.search(r"ISSUE_ID:([a-zA-Z0-9-]+)", create_response)
    assert issue_id_match, f"Could not find issue ID in the response: {create_response}"
    issue_id = issue_id_match.group(1)

    return issue_id


@pytest.mark.asyncio
async def test_update_issue(client):
    """Test updating an issue"""
    # First create an issue and get its ID
    issue_id = await test_create_issue(client)
    assert issue_id, "Failed to get issue ID from creation"

    # Update test issue
    update_response = await client.process_query(
        f"Use the update_issue tool to update the issue with issue_id '{issue_id}', "
        "setting title to 'Updated Test Issue' and priority to 3."
    )

    print("Update issue response:")
    print(f"\t{update_response}")
    print("✅ Issue update working")
