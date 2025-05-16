"""
This file contains the tests for the GitHub server.
"""

import uuid
import pytest

# Global test variables
TEST_UUID = str(uuid.uuid4())[:8]
TEST_REPO_NAME = f"mcp_repo_{TEST_UUID}"
TEST_BRANCH_NAME = f"test-branch-{TEST_UUID}"
TEST_OWNER = ""  # Change as per the OAuth user
TEST_DESCRIPTION = (
    "This is a test repository created by test script of MCP Server for GitHub"
)
TEST_AUTHOR = TEST_OWNER
MAX_LIMIT = 2  # Maximum number of items to return for any paginated result

# Repository to use for read-only operations - using the same repo created in tests
READ_REPO_OWNER = ""
READ_REPO_NAME = ""

# Store values for reuse across tests
STORED_COMMIT_SHA = None
STORED_ISSUE_NUMBER = None


@pytest.mark.asyncio
async def test_create_repository(client):
    """Test creating repository in GitHub"""
    private = False
    auto_init = True  # Ensure README.md is created

    response = await client.process_query(
        f"Use the create_repository tool to create a repo named '{TEST_REPO_NAME}' who's description is '{TEST_DESCRIPTION}' and is private: '{private}' and auto_init: '{auto_init}'. If you create the repository successfully, start your response with 'Your Repository is created successfully."
    )

    assert (
        "your repository is created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"Failed to create '{TEST_REPO_NAME}'"

    print("Repository Created Repository Named: ", TEST_REPO_NAME)
    print(f"\t{response}")

    print("✅ Successfully Created GitHub repository")


@pytest.mark.asyncio
async def test_search_repositories(client):
    """Test searching repositories in GitHub"""
    query = "guMCP"

    response = await client.process_query(
        f"Use the search_repositories tool with query: '{query}' and max_limit: {MAX_LIMIT}. If you find any repositories, start your response with 'Here are the search results' and then list them."
    )

    assert (
        "here are the search results" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No results for query '{query}'"

    print("Repositories found:")
    print(f"\t{response}")

    print("✅ Successfully searched GitHub repositories")


@pytest.mark.asyncio
async def test_list_public_user_repositories(client):
    """Test listing public repositories for a user"""
    username = READ_REPO_OWNER

    response = await client.process_query(
        f"Use the list_public_user_repositories tool with username: {username} and max_limit: {MAX_LIMIT}. If you find any repositories, start your response with 'Here are the user repositories' and then list them."
    )

    assert (
        "here are the user repositories" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No repositories found for user {username}"

    print("User repositories found:")
    print(f"\t{response}")

    print("✅ Successfully listed user repositories")


@pytest.mark.asyncio
async def test_list_organization_repositories(client):
    """Test listing repositories for an organization"""
    org_name = "ant-design"

    response = await client.process_query(
        f"Use the list_organization_repositories tool with org_name: {org_name} and max_limit: {MAX_LIMIT}. If you find any repositories, start your response with 'Here are the organization repositories' and then list them."
    )

    assert (
        "here are the organization repositories" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No repositories found for organization {org_name}"

    print("Organization repositories found:")
    print(f"\t{response}")

    print("✅ Successfully listed organization repositories")


@pytest.mark.asyncio
async def test_get_contents(client):
    """Test getting contents of a file in a repository"""
    path = "README.md"  # This file will exist when repo is created with auto_init=True
    branch = "main"

    response = await client.process_query(
        f"Use the get_contents tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, path: {path}, and branch: {branch}. If you get the contents successfully, start your response with 'Here are the file contents' and then show them."
    )

    assert (
        "here are the file contents" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No contents found for {READ_REPO_OWNER}/{READ_REPO_NAME}/{path}"

    print("File contents:")
    print(f"\t{response}")

    print("✅ Successfully retrieved file contents")


@pytest.mark.asyncio
async def test_list_repository_languages(client):
    """Test listing languages used in a repository"""
    repo_name = READ_REPO_NAME
    owner = READ_REPO_OWNER

    response = await client.process_query(
        f"Use the list_repository_languages tool with owner: {owner}, repo_name: {repo_name}. If you find any languages, start your response with 'Here are the repository languages' and then list them."
    )

    assert (
        "here are the repository languages" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No languages found for repository {repo_name}"

    print("Repository languages:")
    print(f"\t{response}")

    print("✅ Successfully listed repository languages")


@pytest.mark.asyncio
async def test_list_commits(client):
    """Test listing commits for a repository and store first commit SHA"""
    global STORED_COMMIT_SHA
    branch = "main"

    response = await client.process_query(
        f"Use the list_commits tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, branch: {branch}, and max_limit: {MAX_LIMIT}. If you find any commits, start your response with 'Here are the commits' and then pick any one of them and return as STORED_COMMIT_SHA: SHA_VALUE"
    )

    assert (
        "here are the commits" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No commits found for repository {READ_REPO_NAME}"

    # Extract the commit SHA from the response
    import re

    commit_sha_match = re.search(r"STORED_COMMIT_SHA: (\w+)", response)
    if commit_sha_match:
        STORED_COMMIT_SHA = commit_sha_match.group(1)

    assert (
        STORED_COMMIT_SHA and len(STORED_COMMIT_SHA) > 0
    ), "Failed to extract commit SHA"

    print("Commits found:")
    print(f"\t{response}")
    print(f"Stored commit SHA: {STORED_COMMIT_SHA}")

    print("✅ Successfully listed repository commits")


@pytest.mark.asyncio
async def test_get_commit(client):
    """Test getting a specific commit using stored SHA"""
    global STORED_COMMIT_SHA

    response = await client.process_query(
        f"Use the get_commit tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME} and commit_sha: {STORED_COMMIT_SHA}. If you get the commit successfully, start your response with 'Here is the commit' and then show it."
    )

    assert (
        "here is the commit" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No commit found for SHA {STORED_COMMIT_SHA}"

    print("Commit details:")
    print(f"\t{response}")

    print("✅ Successfully retrieved commit")


@pytest.mark.asyncio
async def test_star_repository(client):
    """Star the given repo in users account."""
    repo_name = f"{READ_REPO_OWNER}/{READ_REPO_NAME}"

    response = await client.process_query(
        f"Use the star_repository tool to star the given repo with repo_name: {repo_name}. If you successfully star the repo, start your response with 'Starred the given repository successfully."
    )

    assert (
        "starred the given repository successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No commits found for repository {repo_name}"

    print("Starred the given repository successfully:")
    print(f"\t{response}")

    print("✅ Successfully starred the given repository")


@pytest.mark.asyncio
async def test_list_stargazers(client):
    """Test listing stargazers for a repository"""

    response = await client.process_query(
        f"Use the list_stargazers tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, max_limit: {MAX_LIMIT}. If you find any stargazers, start your response with 'Here are the stargazers' and then list them."
    )

    assert (
        "here are the stargazers" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No stargazers found for repository {READ_REPO_NAME}"

    print("Stargazers found:")
    print(f"\t{response}")

    print("✅ Successfully listed stargazers")


@pytest.mark.asyncio
async def test_get_stargazers_count(client):
    """Test getting the number of stargazers for a repository"""
    repo_name = f"{READ_REPO_OWNER}/{READ_REPO_NAME}"

    response = await client.process_query(
        f"Use the get_stargazers_count tool with repo_name: {repo_name}. If you get the number of stargazers successfully, start your response with 'Here is the number of stargazers' and then show it."
    )

    assert (
        "here is the number of stargazers" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No stargazers found for repository {repo_name}"

    print("Number of stargazers:")
    print(f"\t{response}")

    print("✅ Successfully got the number of stargazers")


@pytest.mark.asyncio
async def test_list_starred_repos_by_user(client):
    """Test listing starred repositories for a user"""

    response = await client.process_query(
        f"Use the list_starred_repos_by_user tool with max_limit: {MAX_LIMIT}. If you find any starred repositories, start your response with 'Here are the starred repositories' and then list them."
    )

    assert (
        "here are the starred repositories" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, "No starred repositories found for user"

    print("Starred repositories found:")
    print(f"\t{response}")

    print("✅ Successfully listed starred repositories")


@pytest.mark.asyncio
async def test_list_issues(client):
    """Test listing issues for a repository"""
    global STORED_ISSUE_NUMBER

    response = await client.process_query(
        f"Use the list_issues tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, max_limit: {MAX_LIMIT}. If you find any issues, start your response with 'Here are the issues' and then list them."
    )

    assert (
        "here are the issues" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No issues found for repository {READ_REPO_NAME}"

    print("Issues found:")
    print(f"\t{response}")

    print("✅ Successfully listed repository issues")


@pytest.mark.asyncio
async def test_create_issue(client):
    """Test creating an issue for a repository and store issue number"""
    global STORED_ISSUE_NUMBER
    title = f"Test Issue {TEST_UUID}"
    body = "This is a test issue created by test script of MCP Server for GitHub"

    response = await client.process_query(
        f"Use the create_issue tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, title: {title}, and body: {body}. If you create the issue successfully, start your response with 'Issue created successfully' and then pick any one of the issue number and return as STORED_ISSUE_NUMBER: ISSUE_NUMBER"
    )

    assert (
        "issue created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to create issue for repository {READ_REPO_NAME}"

    # Extract the issue number from the response
    import re

    issue_number_match = re.search(r"STORED_ISSUE_NUMBER: (\d+)", response)
    if issue_number_match:
        STORED_ISSUE_NUMBER = issue_number_match.group(1)

    assert (
        STORED_ISSUE_NUMBER and len(STORED_ISSUE_NUMBER) > 0
    ), "Failed to extract issue number"

    print("Issue created successfully:")
    print(f"\t{response}")
    print(f"Stored issue number: {STORED_ISSUE_NUMBER}")

    print("✅ Successfully created an issue")


@pytest.mark.asyncio
async def test_get_issue(client):
    """Test getting a specific issue using stored issue number"""
    global STORED_ISSUE_NUMBER

    response = await client.process_query(
        f"Use the get_issue tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME} and issue_number: {STORED_ISSUE_NUMBER}. If you get the issue successfully, start your response with 'Here is the issue' and then show it."
    )

    assert (
        "here is the issue" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No issue found for repository {READ_REPO_NAME}"

    print("Issue details:")
    print(f"\t{response}")

    print("✅ Successfully got the issue")


@pytest.mark.asyncio
async def test_update_issue(client):
    """Test updating an issue using stored issue number"""
    global STORED_ISSUE_NUMBER

    title = f"Updated Issue {TEST_UUID}"
    body = (
        f"This is an updated issue {TEST_UUID} by test script of MCP Server for GitHub"
    )

    response = await client.process_query(
        f"Use the update_issue tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, issue_number: {STORED_ISSUE_NUMBER}, title: {title}, and body: {body}. If you update the issue successfully, start your response with 'Issue updated successfully' and then show it."
    )

    assert (
        "issue updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to update issue for repository {READ_REPO_NAME}"

    print("Issue updated successfully:")
    print(f"\t{response}")

    print("✅ Successfully updated an issue")


@pytest.mark.asyncio
async def test_add_comment_to_issue(client):
    """Test adding a comment to an issue using stored issue number"""
    global STORED_ISSUE_NUMBER

    comment = f"This is a comment {TEST_UUID} by test script of MCP Server for GitHub"

    response = await client.process_query(
        f"Use the add_comment_to_issue tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, issue_number: {STORED_ISSUE_NUMBER}, and comment: {comment}. If you add the comment successfully, start your response with 'Comment added successfully' and then show it."
    )

    assert (
        "comment added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to add comment to issue for repository {READ_REPO_NAME}"

    print("Comment added successfully:")
    print(f"\t{response}")

    print("✅ Successfully added a comment to an issue")


@pytest.mark.asyncio
async def test_create_branch(client):
    """Test creating a branch for a repository"""
    base = "main"

    response = await client.process_query(
        f"Use the create_branch tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, branch_name: {TEST_BRANCH_NAME}, and start_point: {base}. If you create the branch successfully, start your response with 'Branch created successfully' and then show it."
    )

    assert (
        "branch created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to create branch for repository {READ_REPO_NAME}"

    print("Branch created successfully:")
    print(f"\t{response}")

    print("✅ Successfully created a branch")


@pytest.mark.asyncio
async def test_list_branches(client):
    """Test listing branches for a repository"""

    response = await client.process_query(
        f"Use the list_branches tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, max_limit: {MAX_LIMIT}. If you find any branches, start your response with 'Here are the branches' and then list them."
    )

    assert (
        "here are the branches" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No branches found for repository {READ_REPO_NAME}"

    print("Branches found:")
    print(f"\t{response}")

    print("✅ Successfully listed repository branches")


@pytest.mark.asyncio
async def test_add_file_to_repository(client):
    """Test adding a file to a repository"""
    path = f"add_file_test_{TEST_UUID}.txt"
    content = f"This is a test file {TEST_UUID} by test script of MCP Server for GitHub"
    commit_message = (
        f"This is a test commit {TEST_UUID} by test script of MCP Server for GitHub"
    )

    response = await client.process_query(
        f"Use the add_file_to_repository tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, path: {path}, content: {content}, branch: {TEST_BRANCH_NAME}, and commit_message: {commit_message}. If you add the file successfully, start your response with 'File added successfully' and then show it."
    )

    assert (
        "file added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to add file to repository {READ_REPO_NAME}"

    print("File added successfully:")
    print(f"\t{response}")

    print("✅ Successfully added a file to a repository")


@pytest.mark.asyncio
async def test_create_pull_request(client):
    """Test creating a pull request"""
    base = "main"
    title = f"Test Pull Request {TEST_UUID}"
    body = f"This is a test pull request {TEST_UUID}"

    response = await client.process_query(
        f"Use the create_pull_request tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, base: {base}, head: {TEST_BRANCH_NAME}, title: {title}, and body: {body}. If you create the pull request successfully, start your response with 'Pull request created successfully' and then show it."
    )

    assert (
        "pull request created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to create pull request for repository {READ_REPO_NAME}"

    print("Pull request created successfully:")
    print(f"\t{response}")

    print("✅ Successfully created a pull request")


@pytest.mark.asyncio
async def test_list_pull_requests(client):
    """Test listing pull requests for a repository"""

    response = await client.process_query(
        f"Use the list_pull_requests tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, max_limit: {MAX_LIMIT}. If you find any pull requests, start your response with 'Here are the pull requests' and then list them."
    )

    assert (
        "here are the pull requests" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No pull requests found for repository {READ_REPO_NAME}"

    print("Pull requests found:")
    print(f"\t{response}")

    print("✅ Successfully listed repository pull requests")


@pytest.mark.asyncio
async def test_list_pull_requests_with_filters(client):
    """Test listing pull requests with filters and limits"""
    state = "all"  # Get both open and closed PRs

    response = await client.process_query(
        f"Use the list_pull_requests tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, state: {state}, and max_limit: {MAX_LIMIT}. If you find any pull requests, list them all and mention how many were returned and if the result was limited by max_limit."
    )

    assert response and len(response) > 0, f"No response received for filtered PRs"

    print("Pull requests with filters:")
    print(f"\t{response}")

    print("✅ Successfully listed repository pull requests with filters")


@pytest.mark.asyncio
async def test_list_issues_with_filters(client):
    """Test listing issues with filters"""
    state = "all"  # Get both open and closed issues
    creator = READ_REPO_OWNER  # Filter by creator

    response = await client.process_query(
        f"Use the list_issues tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, state: {state}, creator: {creator}, and max_limit: {MAX_LIMIT}. If you find any issues, list them and mention the filters that were applied."
    )

    assert response and len(response) > 0, f"No response received for filtered issues"

    print("Issues with filters:")
    print(f"\t{response}")

    print("✅ Successfully listed repository issues with filters")


@pytest.mark.asyncio
async def test_list_commits_with_filters(client):
    """Test listing commits with filters"""
    branch = "main"
    path = "README.md"  # Only commits that modified README.md

    response = await client.process_query(
        f"Use the list_commits tool with owner: {READ_REPO_OWNER}, repo_name: {READ_REPO_NAME}, branch: {branch}, max_limit: {MAX_LIMIT}, and path: {path}. If you find any commits, list them and explain that you are only showing commits that modified the README.md file, limited to {MAX_LIMIT} results."
    )

    assert response and len(response) > 0, f"No response received for filtered commits"

    print("Commits with filters:")
    print(f"\t{response}")

    print("✅ Successfully listed filtered repository commits")
