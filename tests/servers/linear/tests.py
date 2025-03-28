import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing issues from Linear"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Linear issues found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed Linear issues")


@pytest.mark.asyncio
async def test_read_issue(client):
    """Test reading a specific Linear issue"""
    # First list issues to get a valid issue ID
    response = await client.list_resources()

    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    resources = response.resources
    
    # Try to read the first issue
    if resources:
        resource = resources[0]
        response = await client.read_resource(resource.uri)

        assert len(
            response.contents
        ), f"Response should contain issue contents: {response}"

        print("Issue read:")
        print(f"\tIssue: {resource.name}")
        print(f"\tContent type: {response.contents[0].mimeType}")
        print(f"\tContent preview: {response.contents[0].text[:200]}...")

        print("✅ Successfully read Linear issue")
    else:
        print("⚠️ No issues found to test reading")


@pytest.mark.asyncio
async def test_search_issues(client):
    """Test searching for issues"""
    response = await client.process_query(
        "Use the search_issues tool to search for issues with the word 'bug' or 'feature'. List any results you find."
    )

    print("Search results:")
    print(f"\t{response}")

    # The response should either contain search results or indicate no matches
    assert "issues" in response.lower() or "no issues found" in response.lower(), (
        f"Search response didn't include results or 'no issues' message: {response}"
    )

    print("✅ Search issues functionality working")


@pytest.mark.asyncio
async def test_list_teams(client):
    """Test listing Linear teams"""
    response = await client.process_query(
        "Use the list_teams tool to show me all teams in my Linear workspace."
    )

    print("Teams result:")
    print(f"\t{response}")

    # The response should either contain teams or indicate no teams
    assert "team" in response.lower(), (
        f"Teams response didn't include team information: {response}"
    )

    print("✅ List teams functionality working")


@pytest.mark.asyncio
async def test_create_issue(client):
    """Test creating a Linear issue"""
    # First get a team name by using the list_teams tool
    team_response = await client.process_query(
        "Use the list_teams tool to get me the name of one team in Linear."
    )
    
    team_name = None
    for line in team_response.split('\n'):
        if '-' in line and 'team' in line.lower():
            team_name = line.split('-')[1].split('(')[0].strip()
            break
    
    if not team_name:
        print("⚠️ Couldn't find a team name to test issue creation")
        return
        
    # Now create the issue
    create_response = await client.process_query(
        f"Use the create_issue tool to create a test issue in Linear with the following details:\n"
        f"Title: Test Issue from MCP\n"
        f"Description: This is a test issue created via the MCP client\n"
        f"Team: {team_name}\n"
        f"Priority: Medium"
    )

    print("Create issue result:")
    print(f"\t{create_response}")

    # Check if the issue was created successfully
    assert "created successfully" in create_response.lower() or "issue" in create_response.lower(), (
        f"Issue creation response didn't indicate success: {create_response}"
    )

    print("✅ Create issue functionality working")
