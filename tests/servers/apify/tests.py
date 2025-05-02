import pytest
import uuid

# Global variables to store created resources
created_actor_id = None
created_task_id = None

# Add a dataset ID for testing delete_dataset
# You can create a dataset and find the dataset ID in the apify UI
dataset_id = ""


@pytest.mark.asyncio
async def test_list_actors(client):
    """Test listing all actors.

    Verifies that the list_actors tool returns a valid response.
    """
    response = await client.process_query(
        "Use the list_actors tool to fetch all actors. "
        "If successful, start your response with 'Here are the actors' and then list them."
    )

    assert (
        "here are the actors" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_actors"

    print(f"Response: {response}")
    print("✅ list_actors passed.")


@pytest.mark.asyncio
async def test_create_actor(client):
    """Test creating a new actor.

    Verifies that the create_actor tool successfully creates an actor.
    Stores the created actor ID for use in other tests.
    """
    global created_actor_id

    name = f"Test-Actor-{str(uuid.uuid4())[:4]}"
    body = {"description": "Test actor created by guMCP tests", "isPublic": False}

    response = await client.process_query(
        f"Create a new actor with name {name} and body {body}. "
        "If successful, start your response with 'Created actor successfully' and then list the actor ID."
        "Return the actor ID in format ID: <actor_id>"
    )

    assert (
        "created actor successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_actor"

    # Extract actor ID from response
    try:
        created_actor_id = response.split("ID: ")[1].split()[0]
        print(f"Created actor ID: {created_actor_id}")
    except IndexError:
        pytest.fail("Could not extract actor ID from response")

    print(f"Response: {response}")
    print("✅ create_actor passed.")


@pytest.mark.asyncio
async def test_get_actor(client):
    """Test getting actor details.

    Verifies that the get_actor tool returns details for a specific actor.
    """
    if not created_actor_id:
        pytest.skip("No actor ID available - run create_actor test first")

    response = await client.process_query(
        f"Use the get_actor tool to fetch details for actor ID {created_actor_id}. "
        "If successful, start your response with 'Here are the actor details' and then list them."
    )

    assert (
        "here are the actor details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_actor"

    print(f"Response: {response}")
    print("✅ get_actor passed.")


@pytest.mark.asyncio
async def test_build_actor(client):
    """Test building an actor.

    Verifies that the build_actor tool successfully builds an actor.
    """
    if not created_actor_id:
        pytest.skip("No actor ID available - run create_actor test first")

    response = await client.process_query(
        f"Use the build_actor tool to build actor {created_actor_id} "
        "If successful, start your response with 'Actor build started successfully'."
    )

    assert (
        "actor build started successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from build_actor"

    print(f"Response: {response}")
    print("✅ build_actor passed.")


@pytest.mark.asyncio
async def test_list_tasks(client):
    """Test listing all tasks.

    Verifies that the list_tasks tool returns a valid response.
    """
    response = await client.process_query(
        "Use the list_tasks tool to fetch all tasks. "
        "If successful, start your response with 'Here are the tasks' and then list them."
    )

    assert (
        "here are the tasks" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_tasks"

    print(f"Response: {response}")
    print("✅ list_tasks passed.")


@pytest.mark.asyncio
async def test_create_task(client):
    """Test creating a new task.

    Verifies that the create_task tool successfully creates a task.
    Stores the created task ID for use in other tests.
    """
    global created_task_id

    if not created_actor_id:
        pytest.skip("No actor ID available - run create_actor test first")

    response = await client.process_query(
        f"Create a new task for actor {created_actor_id} using create_task tool"
        "If successful, start your response with 'Created task successfully' and then list the task ID."
        "Give the task ID in format ID: <task_id>"
    )

    assert (
        "created task successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_task"

    # Extract task ID from response
    try:
        created_task_id = response.split("ID: ")[1].split()[0]
        print(f"Created task ID: {created_task_id}")
    except IndexError:
        pytest.fail("Could not extract task ID from response")

    print(f"Response: {response}")
    print("✅ create_task passed.")


@pytest.mark.asyncio
async def test_get_task(client):
    """Test getting task details.

    Verifies that the get_task tool returns details for a specific task.
    """
    if not created_task_id:
        pytest.skip("No task ID available - run create_task test first")

    response = await client.process_query(
        f"Use the get_task tool to fetch details for task ID {created_task_id}. "
        "If successful, start your response with 'Here are the task details' and then list them."
    )

    assert (
        "here are the task details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_task"

    print(f"Response: {response}")
    print("✅ get_task passed.")


@pytest.mark.asyncio
async def test_list_datasets(client):
    """Test listing all datasets.

    Verifies that the list_datasets tool returns a valid response.
    """
    response = await client.process_query(
        "Use the list_datasets tool to fetch all datasets. "
        "If successful, start your response with 'Here are the datasets' and then list them."
    )

    assert (
        "here are the datasets" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_datasets"

    print(f"Response: {response}")
    print("✅ list_datasets passed.")


@pytest.mark.asyncio
async def test_list_actor_runs(client):
    """Test listing actor runs.

    Verifies that the list_actor_runs tool returns a valid response.
    """
    if not created_actor_id:
        pytest.skip("No actor ID available - run create_actor test first")

    response = await client.process_query(
        f"Use the list_actor_runs tool to fetch runs for actor ID {created_actor_id}. "
        "If successful, start your response with 'Here are the actor runs' and then list them."
    )

    assert (
        "here are the actor runs" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_actor_runs"

    print(f"Response: {response}")
    print("✅ list_actor_runs passed.")


@pytest.mark.asyncio
async def test_list_task_runs(client):
    """Test listing task runs.

    Verifies that the list_task_runs tool returns a valid response.
    """
    if not created_task_id:
        pytest.skip("No task ID available - run create_task test first")

    response = await client.process_query(
        f"Use the list_task_runs tool to fetch runs for task ID {created_task_id}. "
        "If successful, start your response with 'Here are the task runs' and then list them."
    )

    assert (
        "here are the task runs" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_task_runs"

    print(f"Response: {response}")
    print("✅ list_task_runs passed.")


@pytest.mark.asyncio
async def test_run_actor(client):
    """Test running an actor.

    Verifies that the run_actor tool successfully starts an actor run.
    """
    if not created_actor_id:
        pytest.skip("No actor ID available - run create_actor test first")

    body = {"test": "data"}
    response = await client.process_query(
        f"Use the run_actor tool to run actor ID {created_actor_id} with body {body}. "
        "If successful, start your response with 'Actor run started successfully'."
    )

    assert (
        "actor run started successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from run_actor"

    print(f"Response: {response}")
    print("✅ run_actor passed.")


@pytest.mark.asyncio
async def test_update_task(client):
    """Test updating a task.

    Verifies that the update_task tool successfully updates a task.
    """
    if not created_task_id:
        pytest.skip("No task ID available - run create_task test first")

    body = {
        "name": f"Updated-Task-{str(uuid.uuid4())[:4]}",
        "description": "Updated task description",
    }

    response = await client.process_query(
        f"Use the update_task tool to update task ID {created_task_id} with body {body}. "
        "If successful, start your response with 'Task updated successfully'."
    )

    assert (
        "task updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_task"

    print(f"Response: {response}")
    print("✅ update_task passed.")


@pytest.mark.asyncio
async def test_update_task_input(client):
    """Test updating task input.

    Verifies that the update_task_input tool successfully updates task input.
    """
    if not created_task_id:
        pytest.skip("No task ID available - run create_task test first")

    body = {"test": "updated data"}
    response = await client.process_query(
        f"Use the update_task_input tool to update input for task ID {created_task_id} with body {body}. "
        "If successful, start your response with 'Task input updated successfully'."
    )

    assert (
        "task input updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_task_input"

    print(f"Response: {response}")
    print("✅ update_task_input passed.")


@pytest.mark.asyncio
async def test_run_task(client):
    """Test running a task.

    Verifies that the run_task tool successfully starts a task run.
    """
    if not created_task_id:
        pytest.skip("No task ID available - run create_task test first")

    body = {"test": "data"}
    response = await client.process_query(
        f"Use the run_task tool to run task ID {created_task_id} with body {body}. "
        "If successful, start your response with 'Task run started successfully'."
    )

    assert (
        "task run started successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from run_task"

    print(f"Response: {response}")
    print("✅ run_task passed.")


@pytest.mark.asyncio
async def test_delete_dataset(client):
    """Test deleting a dataset.

    Verifies that the delete_dataset tool successfully deletes a dataset,
    or correctly reports that the dataset doesn't exist.
    """
    response = await client.process_query(
        f"Use the delete_dataset tool to delete dataset ID {dataset_id}. "
        "If successful, start your response with 'Dataset deleted successfully'."
    )

    valid_outcomes = [
        "dataset deleted successfully",
        "not found",
        "already been deleted",
    ]
    assert any(
        outcome in response.lower() for outcome in valid_outcomes
    ), f"Expected success phrase or 'not found' message not found in response: {response}"
    assert response, "No response returned from delete_dataset"

    print(f"Response: {response}")
    print("✅ delete_dataset passed.")


@pytest.mark.asyncio
async def test_delete_task(client):
    """Test deleting a task.

    Verifies that the delete_task tool successfully deletes a task.
    """
    if not created_task_id:
        pytest.skip("No task ID available - run create_task test first")

    response = await client.process_query(
        f"Use the delete_task tool to delete task ID {created_task_id}. "
        "If successful, start your response with 'Task deleted successfully'."
    )

    assert (
        "task deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_task"

    print(f"Response: {response}")
    print("✅ delete_task passed.")


@pytest.mark.asyncio
async def test_delete_actor(client):
    """Test deleting an actor.

    Verifies that the delete_actor tool successfully deletes an actor.
    """
    if not created_actor_id:
        pytest.skip("No actor ID available - run create_actor test first")

    response = await client.process_query(
        f"Use the delete_actor tool to delete actor ID {created_actor_id}. "
        "If successful, start your response with 'Actor deleted successfully'."
    )

    assert (
        "actor deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_actor"

    print(f"Response: {response}")
    print("✅ delete_actor passed.")
