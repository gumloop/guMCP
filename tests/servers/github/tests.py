"""
This file contains the tests for the GitHub server.
"""

import uuid
import pytest

TEST_UUID = str(uuid.uuid4())[:8]


@pytest.mark.asyncio
async def test_create_repository(client):
    """Test creating repository in GitHub"""
    repo_name = "mcp_repo_" + TEST_UUID
    description = (
        "This is a test repository created by test script of MCP Server for GitHub"
    )
    private = False
    auto_init = True

    response = await client.process_query(
        f"Use the create_repository tool to create a repo named '{repo_name}' who's description is '{description}' and is private: '{private}' and auto_init: '{auto_init}'. If you create the repository successfully, start your response with 'Your Repository is created successfully."
    )

    assert (
        "your repository is created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"Failed to create '{repo_name}'"

    print("Repository Created Repository Named: ", repo_name)
    print(f"\t{response}")

    print("✅ Successfully Created GitHub repository")


@pytest.mark.asyncio
async def test_search_repositories(client):
    """Test searching repositories in GitHub"""
    query = "guMCP"

    response = await client.process_query(
        f"Use the search_repositories tool to search for '{query}'. If you find any repositories, start your response with 'Here are the search results' and then list them."
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
    username = "gumloop"

    response = await client.process_query(
        f"Use the list_public_user_repositories tool with username: {username}. If you find any repositories, start your response with 'Here are the user repositories' and then list them."
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
        f"Use the list_organization_repositories tool with org_name: {org_name}. If you find any repositories, start your response with 'Here are the organization repositories' and then list them."
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
    owner = "gumloop"
    repo_name = "guMCP"
    path = "tests/clients/"
    branch = "main"

    response = await client.process_query(
        f"Use the get_contents tool with owner: {owner}, repo_name: {repo_name}, path: {path}, and branch: {branch}. If you get the contents successfully, start your response with 'Here are the file contents' and then show them."
    )

    assert (
        "here are the file contents" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No contents found for {owner}/{repo_name}/{path}"

    print("File contents:")
    print(f"\t{response}")

    print("✅ Successfully retrieved file contents")


@pytest.mark.asyncio
async def test_list_repository_languages(client):
    """Test listing languages used in a repository"""
    repo_name = "gumloop/guMCP"

    response = await client.process_query(
        f"Use the list_repository_languages tool with repo_name: {repo_name}. If you find any languages, start your response with 'Here are the repository languages' and then list them."
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
    """Test listing commits for a repository"""
    owner = "gumloop"
    repo_name = "guMCP"
    branch = "main"

    response = await client.process_query(
        f"Use the list_commits tool with owner: {owner}, repo_name: {repo_name} and branch: {branch}. If you find any commits, start your response with 'Here are the commits' and then list them."
    )

    assert (
        "here are the commits" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No commits found for repository {repo_name}"

    print("Commits found:")
    print(f"\t{response}")

    print("✅ Successfully listed repository commits")


@pytest.mark.asyncio
async def test_get_commit(client):
    """Test getting a specific commit"""
    owner = "gumloop"
    repo_name = "guMCP"
    commit_sha = "cc60f2741c368a71d92b3c07c9ddea45f951afbc"

    response = await client.process_query(
        f"Use the get_commit tool with owner: {owner}, repo_name: {repo_name} and commit_sha: {commit_sha}. If you get the commit successfully, start your response with 'Here is the commit' and then show it."
    )

    assert (
        "here is the commit" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No commit found for SHA {commit_sha}"

    print("Commit details:")
    print(f"\t{response}")

    print("✅ Successfully retrieved commit")


@pytest.mark.asyncio
async def test_star_repository(client):
    """Star the given repo in users account."""
    repo_name = "gumloop/guMCP"

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
    owner = "gumloop"
    repo_name = "guMCP"

    response = await client.process_query(
        f"Use the list_stargazers tool with owner: {owner}, repo_name: {repo_name}. If you find any stargazers, start your response with 'Here are the stargazers' and then list them."
    )

    assert (
        "here are the stargazers" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No stargazers found for repository {repo_name}"

    print("Stargazers found:")
    print(f"\t{response}")

    print("✅ Successfully listed stargazers")


@pytest.mark.asyncio
async def test_get_stargazers_count(client):
    """Test getting the number of stargazers for a repository"""
    repo_name = "gumloop/guMCP"

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
        "Use the list_starred_repos_by_user tool to list all the starred repositories for the user. If you find any starred repositories, start your response with 'Here are the starred repositories' and then list them."
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
    owner = "gumloop"
    repo_name = "guMCP"

    response = await client.process_query(
        f"Use the list_issues tool with owner: {owner}, repo_name: {repo_name}. If you find any issues, start your response with 'Here are the issues' and then list them."
    )

    assert (
        "here are the issues" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No issues found for repository {repo_name}"

    print("Issues found:")
    print(f"\t{response}")

    print("✅ Successfully listed repository issues")


@pytest.mark.asyncio
async def test_get_issue(client):
    """Test getting a specific issue for a repository"""
    owner = "gumloop"
    repo_name = "guMCP"
    issue_number = 1

    response = await client.process_query(
        f"Use the get_issue tool with owner: {owner}, repo_name: {repo_name} and issue_number: {issue_number}. If you get the issue successfully, start your response with 'Here is the issue' and then show it."
    )

    assert (
        "here is the issue" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response and len(response) > 0, f"No issue found for repository {repo_name}"

    print("Issue details:")
    print(f"\t{response}")

    print("✅ Successfully got the issue")


@pytest.mark.asyncio
async def test_create_issue(client):
    """Test creating an issue for a repository"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID
    title = "Test Issue " + TEST_UUID
    body = "This is a test issue created by test script of MCP Server for GitHub"

    response = await client.process_query(
        f"Use the create_issue tool with owner: {owner}, repo_name: {repo_name}, title: {title}, and body: {body}. If you create the issue successfully, start your response with 'Issue created successfully' and then show it."
    )

    assert (
        "issue created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to create issue for repository {repo_name}"

    print("Issue created successfully:")
    print(f"\t{response}")

    print("✅ Successfully created an issue")


@pytest.mark.asyncio
async def test_update_issue(client):
    """Test updating an issue for a repository"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID
    issue_number = 1
    title = "Updated Issue " + TEST_UUID
    body = (
        "This is an updated issue "
        + TEST_UUID
        + " by test script of MCP Server for GitHub"
    )

    response = await client.process_query(
        f"Use the update_issue tool with owner: {owner}, repo_name: {repo_name}, issue_number: {issue_number}, title: {title}, and body: {body}. If you update the issue successfully, start your response with 'Issue updated successfully' and then show it."
    )

    assert (
        "issue updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to update issue for repository {repo_name}"

    print("Issue updated successfully:")
    print(f"\t{response}")

    print("✅ Successfully updated an issue")


@pytest.mark.asyncio
async def test_add_comment_to_issue(client):
    """Test adding a comment to an issue"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID
    issue_number = 1
    comment = (
        "This is a comment " + TEST_UUID + " by test script of MCP Server for GitHub"
    )

    response = await client.process_query(
        f"Use the add_comment_to_issue tool with owner: {owner}, repo_name: {repo_name}, issue_number: {issue_number}, and comment: {comment}. If you add the comment successfully, start your response with 'Comment added successfully' and then show it."
    )

    assert (
        "comment added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to add comment to issue for repository {repo_name}"

    print("Comment added successfully:")
    print(f"\t{response}")

    print("✅ Successfully added a comment to an issue")


@pytest.mark.asyncio
async def test_create_branch(client):
    """Test creating a branch for a repository"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID
    branch_name = "test-branch-" + TEST_UUID
    base = "main"

    response = await client.process_query(
        f"Use the create_branch tool with owner: {owner}, repo_name: {repo_name}, branch_name: {branch_name}, and base: {base}. If you create the branch successfully, start your response with 'Branch created successfully' and then show it."
    )

    assert (
        "branch created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to create branch for repository {repo_name}"

    print("Branch created successfully:")
    print(f"\t{response}")

    print("✅ Successfully created a branch")


@pytest.mark.asyncio
async def test_list_branches(client):
    """Test listing branches for a repository"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID

    response = await client.process_query(
        f"Use the list_branches tool with owner: {owner}, repo_name: {repo_name}. If you find any branches, start your response with 'Here are the branches' and then list them."
    )

    assert (
        "here are the branches" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No branches found for repository {repo_name}"

    print("Branches found:")
    print(f"\t{response}")

    print("✅ Successfully listed repository branches")


@pytest.mark.asyncio
async def test_add_file_to_repository(client):
    """Test adding a file to a repository"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID
    path = "add_file_test_" + TEST_UUID + ".txt"
    content = (
        "This is a test file " + TEST_UUID + " by test script of MCP Server for GitHub"
    )
    branch = "test-branch-" + TEST_UUID
    commit_message = (
        "This is a test commit "
        + TEST_UUID
        + " by test script of MCP Server for GitHub"
    )

    response = await client.process_query(
        f"Use the add_file_to_repository tool with owner: {owner}, repo_name: {repo_name}, path: {path}, content: {content}, branch: {branch}, and commit_message: {commit_message}. If you add the file successfully, start your response with 'File added successfully' and then show it."
    )

    assert (
        "file added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to add file to repository {repo_name}"

    print("File added successfully:")
    print(f"\t{response}")

    print("✅ Successfully added a file to a repository")


@pytest.mark.asyncio
async def test_create_pull_request(client):
    """Test creating a pull request"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID
    base = "main"
    head = "test-branch-" + TEST_UUID
    title = "Test Pull Request " + TEST_UUID
    body = "This is a test pull request " + TEST_UUID

    response = await client.process_query(
        f"Use the create_pull_request tool with owner: {owner}, repo_name: {repo_name}, base: {base}, head: {head}, title: {title}, and body: {body}. If you create the pull request successfully, start your response with 'Pull request created successfully' and then show it."
    )

    assert (
        "pull request created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"Failed to create pull request for repository {repo_name}"

    print("Pull request created successfully:")
    print(f"\t{response}")

    print("✅ Successfully created a pull request")


@pytest.mark.asyncio
async def test_list_pull_requests(client):
    """Test listing pull requests for a repository"""
    owner = "rbehal"  # Change as per the OAuth user
    repo_name = "mcp_repo_" + TEST_UUID

    response = await client.process_query(
        f"Use the list_pull_requests tool with owner: {owner}, repo_name: {repo_name}. If you find any pull requests, start your response with 'Here are the pull requests' and then list them."
    )

    assert (
        "here are the pull requests" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response and len(response) > 0
    ), f"No pull requests found for repository {repo_name}"

    print("Pull requests found:")
    print(f"\t{response}")

    print("✅ Successfully listed repository pull requests")
