import pytest
import uuid

from tests.utils.test_tools import run_resources_test


# Global variables to store created comment and reaction information
test_file_key = ""  # Replace with a valid test file key
test_comment_id = None
test_team_id = ""  # Replace with a valid test team ID
test_project_id = ""  # Replace with a valid test project ID


@pytest.mark.asyncio
async def test_resources(client):
    return await run_resources_test(client)


@pytest.mark.asyncio
async def test_get_me(client):
    """Test getting the authenticated user's information.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_me tool to fetch information about the authenticated user. "
        "If successful, start your response with 'Here is the user information' and then list the details."
    )

    assert (
        "here is the user information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_me"

    print(f"Response: {response}")
    print("✅ get_me passed.")


@pytest.mark.asyncio
async def test_get_file(client):
    """Test getting a Figma file by key.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_file tool to fetch details for file key {test_file_key}. "
        "If successful, start your response with 'Here is the file information' and then list the details."
    )

    assert (
        "here is the file information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_file"

    print(f"Response: {response}")
    print("✅ get_file passed.")


@pytest.mark.asyncio
async def test_get_file_comments(client):
    """Test getting comments for a Figma file.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_file_comments tool to fetch comments for file key {test_file_key}. "
        "If successful, start your response with 'Here are the file comments' and then list them."
    )

    assert (
        "here are the file comments" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_file_comments"

    print(f"Response: {response}")
    print("✅ get_file_comments passed.")


@pytest.mark.asyncio
async def test_post_comment(client):
    """Test posting a comment on a Figma file.

    Stores the created comment ID for use in delete test.

    Args:
        client: The test client fixture for the MCP server.
    """
    global test_comment_id
    message = f"Test comment {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the post_comment tool to create a new comment on file key {test_file_key} "
        f"with message '{message}'. If successful, start your response with "
        "'Comment posted successfully' and then list the comment ID in format 'ID: <comment_id>'."
    )

    assert (
        "comment posted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from post_comment"

    # Extract comment ID from response
    try:
        test_comment_id = response.lower().split("id: ")[1].split()[0]
        print(f"Created comment ID: {test_comment_id}")
    except IndexError:
        pytest.fail("Could not extract comment ID from response")

    print(f"Response: {response}")
    print("✅ post_comment passed.")


@pytest.mark.asyncio
async def test_post_comment_reaction(client):
    """Test posting a reaction to a comment.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_comment_id:
        pytest.skip("No comment ID available - run post_comment test first")

    emoji = ":heart:"

    response = await client.process_query(
        f"Use the post_comment_reaction tool to add a reaction with emoji '{emoji}' "
        f"to comment ID {test_comment_id} on file key {test_file_key}. "
        "If successful, start your response with 'Reaction added successfully'."
    )

    assert (
        "reaction added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from post_comment_reaction"

    print(f"Response: {response}")
    print("✅ post_comment_reaction passed.")


@pytest.mark.asyncio
async def test_get_comment_reactions(client):
    """Test getting reactions for a specific comment.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_comment_id:
        pytest.skip("No comment ID available - run post_comment test first")

    response = await client.process_query(
        f"Use the get_comment_reactions tool to fetch reactions for comment ID {test_comment_id} "
        f"on file key {test_file_key}. If successful, start your response with "
        "'Here are the comment reactions' and then list them."
    )

    assert (
        "here are the comment reactions" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_comment_reactions"

    print(f"Response: {response}")
    print("✅ get_comment_reactions passed.")


@pytest.mark.asyncio
async def test_delete_comment_reaction(client):
    """Test deleting a reaction from a comment.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_comment_id:
        pytest.skip("No comment ID available - run post_comment test first")

    emoji = "👍"

    response = await client.process_query(
        f"Use the delete_comment_reaction tool to remove the '{emoji}' reaction "
        f"from comment ID {test_comment_id} on file key {test_file_key}. "
        "If successful, start your response with 'Reaction deleted successfully'."
    )

    assert (
        "reaction deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_comment_reaction"

    print(f"Response: {response}")
    print("✅ delete_comment_reaction passed.")


@pytest.mark.asyncio
async def test_delete_comment(client):
    """Test deleting a comment from a Figma file.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not test_comment_id:
        pytest.skip("No comment ID available - run post_comment test first")

    response = await client.process_query(
        f"Use the delete_comment tool to delete comment ID {test_comment_id} "
        f"from file key {test_file_key}. If successful, start your response with "
        "'Comment deleted successfully'."
    )

    assert (
        "comment deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_comment"

    print(f"Response: {response}")
    print("✅ delete_comment passed.")


@pytest.mark.asyncio
async def test_get_team_projects(client):
    """Test getting all projects within a team.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_team_projects tool to fetch projects for team ID {test_team_id}. "
        "If successful, start your response with 'Here are the team projects' and then list them."
    )

    assert (
        "here are the team projects" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_team_projects"

    print(f"Response: {response}")
    print("✅ get_team_projects passed.")


@pytest.mark.asyncio
async def test_get_project_files(client):
    """Test listing the files in a given project.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_project_files tool to fetch files for project ID {test_project_id}. "
        "If successful, start your response with 'Here are the project files' and then list them."
    )

    assert (
        "here are the project files" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_project_files"

    print(f"Response: {response}")
    print("✅ get_project_files passed.")


@pytest.mark.asyncio
async def test_get_file_versions(client):
    """Test getting the version history of a file.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the get_file_versions tool to fetch version history for file key {test_file_key}. "
        "If successful, start your response with 'Here are the file versions' and then list them."
    )

    assert (
        "here are the file versions" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_file_versions"

    print(f"Response: {response}")
    print("✅ get_file_versions passed.")
