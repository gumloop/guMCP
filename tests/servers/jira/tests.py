import pytest
import uuid

# Global variables to store created project and issue IDs
SITE_NAME = "gumloop"
project_key = "TEST" + str(uuid.uuid4())[:4].upper()

created_issue_key = None
created_comment_id = None


@pytest.mark.asyncio
async def test_create_project(client):
    """Create a new JIRA project.

    Verifies that the project is created successfully.
    Stores the created project key for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    project_name = "Test Project " + str(uuid.uuid4())
    project_type = "software"

    response = await client.process_query(
        f"Use the create_project tool to create a new project with key {project_key}, "
        f"name {project_name}, and type {project_type} for SITE_NAME {SITE_NAME}. If successful, start your response "
        "with 'Created project successfully' and then list the project details."
    )

    response_text = str(response)

    assert (
        "created project successfully" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response_text, "No response returned from create_project"

    print(f"Response: {response_text}")
    print("✅ create_project passed.")


@pytest.mark.asyncio
async def test_list_projects(client):
    """List all accessible JIRA projects.

    Verifies that the response includes project information.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the list_projects tool to fetch all accessible projects for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here are the projects' and then list them."
    )

    assert (
        "here are the projects" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_projects"

    print(f"Response: {response}")
    print("✅ list_projects passed.")


@pytest.mark.asyncio
async def test_get_project(client):
    """Get details of a specific JIRA project.

    Verifies that the project details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not project_key:
        pytest.skip("No project key available - run create_project test first")

    response = await client.process_query(
        f"Use the get_project tool to fetch details for project key {project_key} for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here are the project details' and then list them."
    )

    assert (
        "here are the project details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_project"

    print(f"Response: {response}")
    print("✅ get_project passed.")


@pytest.mark.asyncio
async def test_create_issue(client):
    """Create a new JIRA issue.

    Verifies that the issue is created successfully.
    Stores the created issue key for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_issue_key

    if not project_key:
        pytest.skip("No project key available - run create_project test first")

    summary = "Test Issue " + str(uuid.uuid4())
    description = "This is a test issue created by the test_create_issue tool in guMCP."
    issue_type = "Task"

    response = await client.process_query(
        f"Use the create_issue tool to create a new issue in project {project_key} "
        f"with summary '{summary}', description '{description}', and type '{issue_type}' for SITE_NAME {SITE_NAME}. "
        "If successful, your response should be 'Created issue with key: <key>' and nothing else."
    )

    response_text = str(response)

    assert (
        "created issue with key:" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response_text, "No response returned from create_issue"

    if "key:" in response_text.lower():
        created_issue_key = response_text.lower().split("key: ")[1].split()[0]
    else:
        pytest.fail("Could not extract issue key from response")

    print(f"Response: {response_text}")
    print("✅ create_issue passed.")


@pytest.mark.asyncio
async def test_get_issue(client):
    """Get details of a specific JIRA issue.

    Verifies that the issue details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_issue_key:
        pytest.skip("No issue key available - run create_issue test first")

    response = await client.process_query(
        f"Use the get_issue tool to fetch details for issue key {created_issue_key.upper()} for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here are the issue details' and then list them."
    )

    assert (
        "here are the issue details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_issue"

    print(f"Response: {response}")
    print("✅ get_issue passed.")


@pytest.mark.asyncio
async def test_comment_on_issue(client):
    """Add a comment to a JIRA issue.

    Verifies that the comment is added successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_issue_key:
        pytest.skip("No issue key available - run create_issue test first")

    comment = (
        "This is a test comment created by the test_comment_on_issue tool in guMCP."
    )

    response = await client.process_query(
        f"Use the comment_on_issue tool to add a comment to issue {created_issue_key.upper()} "
        f"with content '{comment}' for SITE_NAME {SITE_NAME}. If successful, start your response with 'Added comment successfully' "
        "and then list the comment details."
    )

    assert (
        "added comment successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from comment_on_issue"

    print(f"Response: {response}")
    print("✅ comment_on_issue passed.")


@pytest.mark.asyncio
async def test_transition_my_issue(client):
    """Transition a JIRA issue to a new status.

    Verifies that the issue is transitioned successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    print(f"created_issue_key: {created_issue_key}")
    if not created_issue_key:
        pytest.skip("No issue key available - run create_issue test first")

    transition_to = "In Progress"

    response = await client.process_query(
        f"Use the transition_my_issue tool to transition issue {created_issue_key.upper()} "
        f"to status '{transition_to}' for SITE_NAME {SITE_NAME}. If successful, start your response with 'Transitioned issue successfully' "
        "and then list the issue details."
    )

    response_text = str(response)

    assert (
        "transitioned issue successfully" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response_text, "No response returned from transition_my_issue"

    print(f"Response: {response_text}")
    print("✅ transition_my_issue passed.")


@pytest.mark.asyncio
async def test_get_myself(client):
    """Get information about the authenticated user.

    Verifies that the user information is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_myself tool to fetch information about the authenticated user for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here is your user information' and then list it."
    )

    assert (
        "here is your user information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_myself"

    print(f"Response: {response}")
    print("✅ get_myself passed.")


@pytest.mark.asyncio
async def test_get_my_issues(client):
    """Get issues assigned to the authenticated user.

    Verifies that the issues are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_my_issues tool to fetch issues assigned to you for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here are your issues' and then list them."
    )

    assert (
        "here are your issues" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_my_issues"

    print(f"Response: {response}")
    print("✅ get_my_issues passed.")


@pytest.mark.asyncio
async def test_get_my_permissions(client):
    """Get permissions for the authenticated user.

    Verifies that the permissions are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not project_key:
        pytest.skip("No project key available - run create_project test first")

    response = await client.process_query(
        f"Use the get_my_permissions tool to fetch your permissions for project {project_key} for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here are your permissions' and then list them."
    )

    assert (
        "here are your permissions" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_my_permissions"

    print(f"Response: {response}")
    print("✅ get_my_permissions passed.")


@pytest.mark.asyncio
async def test_update_project(client):
    """Update a JIRA project.

    Verifies that the project is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not project_key:
        pytest.skip("No project key available - run create_project test first")

    new_name = "Updated Test Project " + str(uuid.uuid4())
    new_description = "This is an updated test project description."

    response = await client.process_query(
        f"Use the update_project tool to update project {project_key} with name '{new_name}' "
        f"and description '{new_description}' for SITE_NAME {SITE_NAME}. If successful, start your response "
        "with 'Updated project successfully' and then list the project details."
    )

    response_text = str(response)

    assert (
        "updated project successfully" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response_text, "No response returned from update_project"

    print(f"Response: {response_text}")
    print("✅ update_project passed.")


@pytest.mark.asyncio
async def test_get_issue_types_for_project(client):
    """Get issue types for a JIRA project.

    Verifies that the issue types are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not project_key:
        pytest.skip("No project key available - run create_project test first")

    response = await client.process_query(
        f"Use the get_issue_types_for_project tool to fetch issue types for project {project_key.upper()} "
        f"for SITE_NAME {SITE_NAME}. If successful, start your response with 'Here are the issue types' and then list them."
    )

    response_text = str(response)

    assert (
        "here are the issue types" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response_text, "No response returned from get_issue_types_for_project"

    print(f"Response: {response_text}")
    print("✅ get_issue_types_for_project passed.")


@pytest.mark.asyncio
async def test_update_issue(client):
    """Update a JIRA issue.

    Verifies that the issue is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_issue_key:
        pytest.skip("No issue key available - run create_issue test first")

    new_summary = "Updated Test Issue " + str(uuid.uuid4())
    new_description = "This is an updated test issue description."

    response = await client.process_query(
        f"Use the update_issue tool to update issue {created_issue_key.upper()} with summary '{new_summary}' "
        f"and description '{new_description}' for SITE_NAME {SITE_NAME}. If successful, start your response "
        "with 'Updated issue successfully' and then list the issue details."
    )

    response_text = str(response)

    assert (
        "updated issue successfully" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response, "No response returned from update_issue"

    print(f"Response: {response_text}")
    print("✅ update_issue passed.")


@pytest.mark.asyncio
async def test_list_issues(client):
    """List JIRA issues using JQL query.

    Verifies that the issues are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not project_key:
        pytest.skip("No project key available - run create_project test first")

    jql = f"project = {project_key.upper()} ORDER BY created DESC"

    response = await client.process_query(
        f"Use the list_issues tool to fetch issues with JQL '{jql}' for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here are the issues' and then list them."
    )

    response_text = str(response)

    assert (
        "here are the issues" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response_text, "No response returned from list_issues"

    print(f"Response: {response_text}")
    print("✅ list_issues passed.")


@pytest.mark.asyncio
async def test_get_my_recent_activity(client):
    """Get recent activity for the authenticated user.

    Verifies that the recent activity is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_my_recent_activity tool to fetch your recent activity for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Here is your recent activity' and then list it."
    )

    response_text = str(response)

    assert (
        "here is your recent activity" in response_text.lower()
    ), f"Expected success phrase not found in response: {response_text}"
    assert response_text, "No response returned from get_my_recent_activity"

    print(f"Response: {response_text}")
    print("✅ get_my_recent_activity passed.")


@pytest.mark.asyncio
async def test_delete_issue(client):
    """Delete a JIRA issue.

    Verifies that the issue is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_issue_key:
        pytest.skip("No issue key available - run create_issue test first")

    response = await client.process_query(
        f"Use the delete_issue tool to delete issue {created_issue_key.upper()} for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Deleted issue successfully' and then list the issue key."
    )

    assert (
        "deleted issue successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_issue"

    print(f"Response: {response}")
    print("✅ delete_issue passed.")


@pytest.mark.asyncio
async def test_delete_project(client):
    """Delete a JIRA project.

    Verifies that the project is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not project_key:
        pytest.skip("No project key available - run create_project test first")

    response = await client.process_query(
        f"Use the delete_project tool to delete project {project_key} for SITE_NAME {SITE_NAME}. "
        "If successful, start your response with 'Deleted project successfully' and then list the project key."
    )

    assert (
        "deleted project successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_project"

    print(f"Response: {response}")
    print("✅ delete_project passed.")
