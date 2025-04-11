import pytest
import random


@pytest.mark.asyncio
async def test_get_authenticated_user(client):
    """Test getting authenticated user information"""
    response = await client.process_query(
        "Use the get_authenticated_user tool to get information about the currently authenticated user."
    )

    eval = await client.llm_as_a_judge(
        "It should pass if the response successfully retrieves information about the authenticated user.",
        response,
    )

    assert eval["passed"], eval["reasoning"]
    print(eval)
    print("✅ Get authenticated user tool working")


@pytest.mark.asyncio
async def test_get_workspaces(client):
    """Test getting all workspaces"""
    response = await client.process_query(
        "Use the get_workspaces tool to list all workspaces/teams the user has access to."
    )

    eval = await client.llm_as_a_judge(
        "It should pass if the response successfully retrieves a list of workspaces.",
        response,
    )

    assert eval["passed"], eval["reasoning"]
    print(eval)
    print("✅ Get workspaces tool working")


@pytest.mark.asyncio
async def test_workflow_with_spaces_and_lists(client):
    """Test the workflow of getting workspaces, spaces, and lists"""
    # First get workspaces
    workspaces_response = await client.process_query(
        "Use the get_workspaces tool to list all workspaces and extract a workspace ID."
    )

    workspace_id = await client.fetch_value_from_response(
        workspaces_response,
        {"extract_workspace_id": "extract any one workspace id from the response"},
    )

    assert workspace_id, "Failed to find a valid workspace ID"

    # Get spaces for the workspace
    spaces_response = await client.process_query(
        f"Use the get_spaces tool to list all spaces in workspace with ID {workspace_id}."
    )

    eval_spaces = await client.llm_as_a_judge(
        "It should pass if the response successfully retrieves a list of spaces for the workspace.",
        spaces_response,
    )

    assert eval_spaces["passed"], eval_spaces["reasoning"]

    # Try to extract a space ID for further testing
    space_id = await client.fetch_value_from_response(
        spaces_response,
        {"extract_space_id": "extract any one space id from the response if available"},
    )

    if space_id:
        # Get lists in the space
        lists_response = await client.process_query(
            f"Use the get_lists tool to list all lists in space with ID {space_id}."
        )

        eval_lists = await client.llm_as_a_judge(
            "It should pass if the response successfully retrieves a list of lists for the space.",
            lists_response,
        )

        assert eval_lists["passed"], eval_lists["reasoning"]

    print("✅ Workflow with spaces and lists working")


@pytest.mark.asyncio
async def test_task_creation_and_update(client):
    """Test creating and updating a task"""
    # First get workspaces and a space
    workspaces_response = await client.process_query(
        "Use the get_workspaces tool to list all workspaces."
    )

    workspace_id = await client.fetch_value_from_response(
        workspaces_response,
        {"extract_workspace_id": "extract any one workspace id from the response"},
    )

    assert workspace_id, "Failed to find a valid workspace ID"

    # Get spaces for the workspace
    spaces_response = await client.process_query(
        f"Use the get_spaces tool to list all spaces in workspace with ID {workspace_id}."
    )

    space_id = await client.fetch_value_from_response(
        spaces_response,
        {"extract_space_id": "extract any one space id from the response if available"},
    )

    if not space_id:
        pytest.skip("No spaces found, skipping task creation test")

    # Get folders in the space
    folders_response = await client.process_query(
        f"Use the get_folders tool to list all folders in space with ID {space_id}."
    )

    folder_id = await client.fetch_value_from_response(
        folders_response,
        {
            "extract_folder_id": "extract any one folder id from the response if available"
        },
    )

    # Get lists in the folder or space
    if folder_id and folder_id.get("extract_folder_id"):
        # Get lists in the folder
        lists_response = await client.process_query(
            f"Use the get_lists tool to list all lists in folder with ID {folder_id.get('extract_folder_id')}."
        )
    else:
        # Try getting lists directly in the space as a fallback
        lists_response = await client.process_query(
            f"Use the get_lists tool to list all lists in space with ID {space_id}."
        )

    list_id = await client.fetch_value_from_response(
        lists_response,
        {"extract_list_id": "extract any one list id from the response if available"},
    )

    if not list_id or not list_id.get("extract_list_id"):
        pytest.skip("No lists found, skipping task creation test")

    list_id = list_id.get("extract_list_id")

    # Create a test task
    task_title = f"Test Task {random.randint(1000, 9999)}"
    create_task_response = await client.process_query(
        f"Use the create_task tool to create a new task in list with ID {list_id}, "
        f"with name '{task_title}' and description 'This is a test task created by the API'."
    )

    task_id = await client.fetch_value_from_response(
        create_task_response,
        {"extract_task_id": "extract the task id from the response"},
    )

    assert task_id and task_id.get(
        "extract_task_id"
    ), "Failed to extract task ID from create response"
    task_id = task_id.get("extract_task_id")

    # Update the task
    update_task_response = await client.process_query(
        f"Use the update_task tool to update the task with ID {task_id}, "
        f"setting name to 'Updated {task_title}' and priority to 2."
    )

    eval_update = await client.llm_as_a_judge(
        "It should pass if the response successfully updates the task.",
        update_task_response,
    )
    assert eval_update["passed"], eval_update["reasoning"]

    # Add a comment to the task
    comment_response = await client.process_query(
        f"Use the add_comment tool to add a comment to task with ID {task_id}, "
        f"with comment text 'This is a test comment added by the API'."
    )

    eval_comment = await client.llm_as_a_judge(
        "It should pass if the response successfully adds a comment to the task.",
        comment_response,
    )
    assert eval_comment["passed"], eval_comment["reasoning"]

    print("✅ Task creation, update, and commenting workflow working")


@pytest.mark.asyncio
async def test_create_folder_and_list(client):
    """Test creating a folder and list"""
    # First get workspaces and a space
    workspaces_response = await client.process_query(
        "Use the get_workspaces tool to list all workspaces."
    )

    workspace_id = await client.fetch_value_from_response(
        workspaces_response,
        {"extract_workspace_id": "extract any one workspace id from the response"},
    )

    assert workspace_id, "Failed to find a valid workspace ID"

    # Get spaces for the workspace
    spaces_response = await client.process_query(
        f"Use the get_spaces tool to list all spaces in workspace with ID {workspace_id}."
    )

    space_id = await client.fetch_value_from_response(
        spaces_response,
        {"extract_space_id": "extract any one space id from the response if available"},
    )

    if not space_id:
        print("No spaces found, skipping folder and list creation test")
        return

    # Create a folder
    folder_name = f"Test Folder {random.randint(1000, 9999)}"
    create_folder_response = await client.process_query(
        f"Use the create_folder tool to create a new folder in space with ID {space_id}, "
        f"with name '{folder_name}'."
    )

    folder_id = await client.fetch_value_from_response(
        create_folder_response,
        {"extract_folder_id": "extract the folder id from the response"},
    )

    if folder_id:
        # Create a list in the folder
        list_name = f"Test List {random.randint(1000, 9999)}"
        create_list_response = await client.process_query(
            f"Use the create_list tool to create a new list in folder with ID {folder_id}, "
            f"with name '{list_name}'."
        )

        eval_list = await client.llm_as_a_judge(
            "It should pass if the response successfully creates a new list.",
            create_list_response,
        )

        assert eval_list["passed"], eval_list["reasoning"]
    else:
        list_name = f"Test List {random.randint(1000, 9999)}"
        create_list_response = await client.process_query(
            f"Use the create_list tool to create a new list in space with ID {space_id}, "
            f"with name '{list_name}'."
        )

        eval_list = await client.llm_as_a_judge(
            "It should pass if the response successfully creates a new list.",
            create_list_response,
        )

        assert eval_list["passed"], eval_list["reasoning"]

    print("✅ Folder and list creation workflow working")
