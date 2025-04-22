import pytest
import uuid

# Global variables to store created IDs
created_action_id = None
created_annotation_id = None
created_cohort_id = None
created_dashboard_id = 372731
created_experiment_id = None
created_insight_id = None
person_id = None


@pytest.mark.asyncio
async def test_list_actions(client):
    """List all actions in a PostHog project.

    Verifies that the response contains action data.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_actions tool to fetch all actions. "
        "If successful, start your response with 'Here are the actions' and then list them."
    )

    assert (
        "here are the actions" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_actions"

    print(f"Response: {response}")
    print("✅ list_actions passed.")


@pytest.mark.asyncio
async def test_create_action(client):
    """Create a new action in PostHog.

    Verifies that the action is created successfully.
    Stores the created action ID for use in update/delete tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_action_id

    name = f"Test Action {uuid.uuid4()}"
    description = (
        "This is a test action created by the test_create_action tool in guMCP."
    )
    steps = [
        {
            "event": "test_event",
            "properties": [{"key": "test_prop", "value": "test_value"}],
        }
    ]

    response = await client.process_query(
        f"Use the create_action tool to create a new action with name {name}, "
        f"description {description}, and steps {steps}. If successful, start your response with "
        "'Created action successfully' and then list the action ID in format 'ID: <action_id>'."
    )

    assert (
        "created action successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_action"

    # Extract action ID from response
    try:
        created_action_id = response.split("ID: ")[1].split()[0]
        print(f"Created action ID: {created_action_id}")
    except IndexError:
        pytest.fail("Could not extract action ID from response")

    print(f"Response: {response}")
    print("✅ create_action passed.")


@pytest.mark.asyncio
async def test_get_action(client):
    """Get details of a specific action.

    Verifies that the action details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_action_id:
        pytest.skip("No action ID available - run create_action test first")

    response = await client.process_query(
        f"Use the get_action tool to fetch details for action ID {created_action_id}. "
        "If successful, start your response with 'Here are the action details' and then list them."
    )

    assert (
        "here are the action details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_action"

    print(f"Response: {response}")
    print("✅ get_action passed.")


@pytest.mark.asyncio
async def test_update_action(client):
    """Update an existing action.

    Verifies that the action is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_action_id:
        pytest.skip("No action ID available - run create_action test first")

    new_name = f"Updated Test Action {uuid.uuid4()}"
    new_description = "This is an updated test action description."

    response = await client.process_query(
        f"Use the update_action tool to update action ID {created_action_id} with "
        f"name {new_name} and description {new_description}. If successful, start your response with "
        "'Updated action successfully' and then list the action details."
    )

    assert (
        "updated action successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_action"

    print(f"Response: {response}")
    print("✅ update_action passed.")


@pytest.mark.asyncio
async def test_create_annotation(client):
    """Create a new annotation in PostHog.

    Verifies that the annotation is created successfully.
    Stores the created annotation ID for use in update/delete tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_annotation_id

    content = f"Test Annotation {uuid.uuid4()}"
    date_marker = "2024-03-20T12:00:00Z"
    scope = "project"
    creation_type = "USR"

    response = await client.process_query(
        f"Use the create_annotation tool to create a new annotation with content {content}, "
        f"date_marker {date_marker}, scope {scope}, and creation_type {creation_type}. "
        "If successful, start your response with 'Created annotation successfully' and then list the annotation ID."
        "Give extracted annotation ID in format 'ID: <annotation_id>'."
    )

    assert (
        "created annotation successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_annotation"

    # Extract annotation ID from response
    try:
        created_annotation_id = response.split("ID: ")[1].split()[0]
        print(f"Created annotation ID: {created_annotation_id}")
    except IndexError:
        pytest.fail("Could not extract annotation ID from response")

    print(f"Response: {response}")
    print("✅ create_annotation passed.")


@pytest.mark.asyncio
async def test_create_cohort(client):
    """Create a new cohort in PostHog.

    Verifies that the cohort is created successfully.
    Stores the created cohort ID for use in update/delete tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_cohort_id

    name = f"Test Cohort {uuid.uuid4()}"
    description = (
        "This is a test cohort created by the test_create_cohort tool in guMCP."
    )
    groups = [
        {
            "properties": [
                {
                    "key": "test_prop",
                    "value": "test_value",
                    "operator": "exact",
                    "type": "person",
                }
            ]
        }
    ]

    response = await client.process_query(
        f"Use the create_cohort tool to create a new cohort with name {name}, "
        f"description {description}, and groups {groups}. If successful, start your response with "
        "'Created cohort successfully' and then list the cohort ID."
        "Give extracted cohort ID in format 'ID: <cohort_id>'."
    )

    assert (
        "created cohort successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_cohort"

    # Extract cohort ID from response
    try:
        created_cohort_id = response.split("ID: ")[1].split()[0]
        print(f"Created cohort ID: {created_cohort_id}")
    except IndexError:
        pytest.fail("Could not extract cohort ID from response")

    print(f"Response: {response}")
    print("✅ create_cohort passed.")


@pytest.mark.asyncio
async def test_create_dashboard(client):
    """Create a new dashboard in PostHog.

    Verifies that the dashboard is created successfully.
    Stores the created dashboard ID for use in update/delete tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_dashboard_id

    name = f"Test Dashboard {uuid.uuid4()}"
    description = (
        "This is a test dashboard created by the test_create_dashboard tool in guMCP."
    )

    response = await client.process_query(
        f"Use the create_dashboard tool to create a new dashboard with name {name} "
        f"and description {description}. If successful, start your response with "
        "'Created dashboard successfully' and then list the dashboard ID."
        "Give extracted dashboard ID in format 'ID: <dashboard_id>'."
    )

    assert (
        "created dashboard successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_dashboard"

    # Extract dashboard ID from response
    try:
        created_dashboard_id = response.split("ID: ")[1].split()[0]
        print(f"Created dashboard ID: {created_dashboard_id}")
    except IndexError:
        pytest.fail("Could not extract dashboard ID from response")

    print(f"Response: {response}")
    print("✅ create_dashboard passed.")


@pytest.mark.asyncio
async def test_create_experiment(client):
    """Create a new experiment in PostHog.

    Verifies that the experiment is created successfully.
    Stores the created experiment ID for use in update/delete tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_experiment_id

    name = f"Test Experiment {uuid.uuid4()}"
    description = (
        "This is a test experiment created by the test_create_experiment tool in guMCP."
    )
    feature_flag_key = f"test-flag-{uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_experiment tool to create a new experiment with name {name}, "
        f"description {description}, and feature_flag_key {feature_flag_key}. If successful, start your response with "
        "'Created experiment successfully' and then list the experiment ID."
        "Give extracted experiment ID in format 'ID: <experiment_id>'."
    )

    assert (
        "created experiment successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_experiment"

    # Extract experiment ID from response
    try:
        created_experiment_id = response.split("ID: ")[1].split()[0]
        print(f"Created experiment ID: {created_experiment_id}")
    except IndexError:
        pytest.fail("Could not extract experiment ID from response")

    print(f"Response: {response}")
    print("✅ create_experiment passed.")


@pytest.mark.asyncio
async def test_create_insight(client):
    """Create a new insight in PostHog.

    Verifies that the insight is created successfully.
    Stores the created insight ID for use in update/delete tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_insight_id

    name = f"Test Insight {uuid.uuid4()}"
    description = (
        "This is a test insight created by the test_create_insight tool in guMCP."
    )
    filters = {"events": [{"id": "test_event"}], "display": "ActionsLineGraph"}

    response = await client.process_query(
        f"Use the create_insight tool to create a new insight with name {name}, "
        f"description {description}, and filters {filters}. If successful, start your response with "
        "'Created insight successfully' and then list the insight ID."
        "Give extracted insight ID in format 'ID: <insight_id>'."
    )

    assert (
        "created insight successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_insight"

    # Extract insight ID from response
    try:
        created_insight_id = response.split("ID: ")[1].split()[0]
        print(f"Created insight ID: {created_insight_id}")
    except IndexError:
        pytest.fail("Could not extract insight ID from response")

    print(f"Response: {response}")
    print("✅ create_insight passed.")


@pytest.mark.asyncio
async def test_capture_event(client):
    """Capture a custom event in PostHog.

    Verifies that the event is captured successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    distinct_id = f"test-user-{uuid.uuid4()}"
    event = "test_event"
    properties = {"test_prop": "test_value", "test_number": 42}

    response = await client.process_query(
        f"Use the capture_event tool to capture an event with distinct_id {distinct_id}, "
        f"event {event}, and properties {properties}. If successful, start your response with "
        "'Captured event successfully' and then list the event details."
    )

    assert (
        "captured event successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from capture_event"

    print(f"Response: {response}")
    print("✅ capture_event passed.")


@pytest.mark.asyncio
async def test_identify_user(client):
    """Identify a user in PostHog.

    Verifies that the user is identified successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    distinct_id = f"test-user-{uuid.uuid4()}"
    properties = {"name": "Test User", "email": "test@example.com", "plan": "premium"}

    response = await client.process_query(
        f"Use the identify_user tool to identify a user with distinct_id {distinct_id} "
        f"and properties {properties}. If successful, start your response with "
        "'Identified user successfully' and then list the user details."
    )

    assert (
        "identified user successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from identify_user"

    print(f"Response: {response}")
    print("✅ identify_user passed.")


@pytest.mark.asyncio
async def test_check_feature_flag(client):
    """Check if a feature flag is enabled for a user.

    Verifies that the feature flag check returns a valid response.

    Args:
        client: The test client fixture for the MCP server.
    """
    distinct_id = f"test-user-{uuid.uuid4()}"
    flag_key = "test-flag"

    response = await client.process_query(
        f"Use the check_feature_flag tool to check if flag {flag_key} is enabled for user {distinct_id}. "
        "If successful, start your response with 'Feature flag check result' and then list the result."
    )

    assert (
        "feature flag check result" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from check_feature_flag"

    print(f"Response: {response}")
    print("✅ check_feature_flag passed.")


@pytest.mark.asyncio
async def test_get_feature_flag_payload(client):
    """Get the payload of a feature flag for a user.

    Verifies that the feature flag payload is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    distinct_id = f"test-user-{uuid.uuid4()}"
    flag_key = "test-flag"

    response = await client.process_query(
        f"Use the get_feature_flag_payload tool to get the payload for flag {flag_key} for user {distinct_id}. "
        "If successful, start your response with 'Feature flag payload' and then list the payload."
    )

    assert (
        "feature flag payload" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_feature_flag_payload"

    print(f"Response: {response}")
    print("✅ get_feature_flag_payload passed.")


@pytest.mark.asyncio
async def test_get_all_flags(client):
    """Get all feature flags enabled for a user.

    Verifies that all feature flags are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    distinct_id = f"test-user-{uuid.uuid4()}"

    response = await client.process_query(
        f"Use the get_all_flags tool to get all flags for user {distinct_id}. "
        "If successful, start your response with 'All feature flags' and then list them."
    )

    assert (
        "all feature flags" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_all_flags"

    print(f"Response: {response}")
    print("✅ get_all_flags passed.")


@pytest.mark.asyncio
async def test_group_identify(client):
    """Create or update a group profile with properties.

    Verifies that the group is identified successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    group_type = "company"
    group_key = f"test-company-{uuid.uuid4()}"
    properties = {"name": "Test Company", "plan": "enterprise"}

    response = await client.process_query(
        f"Use the group_identify tool to identify group {group_key} of type {group_type} with properties {properties}. "
        "If successful, start your response with 'Group identified successfully' and then list the group details."
    )

    assert (
        "group identified successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from group_identify"

    print(f"Response: {response}")
    print("✅ group_identify passed.")


@pytest.mark.asyncio
async def test_capture_group_event(client):
    """Capture an event associated with a group.

    Verifies that the group event is captured successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    distinct_id = f"test-user-{uuid.uuid4()}"
    event = "test_group_event"
    group_type = "company"
    group_key = f"test-company-{uuid.uuid4()}"
    properties = {"test_prop": "test_value"}

    response = await client.process_query(
        f"Use the capture_group_event tool to capture event {event} for user {distinct_id} in group {group_key} of type {group_type} with properties {properties}. "
        "If successful, start your response with 'Group event captured successfully' and then list the event details."
    )

    assert (
        "group event captured successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from capture_group_event"

    print(f"Response: {response}")
    print("✅ capture_group_event passed.")


@pytest.mark.asyncio
async def test_list_annotations(client):
    """List all annotations in a PostHog project.

    Verifies that annotations are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_annotations tool to fetch all annotations. "
        "If successful, start your response with 'Here are the annotations' and then list them."
    )

    assert (
        "here are the annotations" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_annotations"

    print(f"Response: {response}")
    print("✅ list_annotations passed.")


@pytest.mark.asyncio
async def test_get_annotation(client):
    """Get details of a specific annotation.

    Verifies that the annotation details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_annotation_id:
        pytest.skip("No annotation ID available - run create_annotation test first")

    response = await client.process_query(
        f"Use the get_annotation tool to fetch details for annotation ID {created_annotation_id}. "
        "If successful, start your response with 'Here are the annotation details' and then list them."
    )

    assert (
        "here are the annotation details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_annotation"

    print(f"Response: {response}")
    print("✅ get_annotation passed.")


@pytest.mark.asyncio
async def test_update_annotation(client):
    """Update an existing annotation.

    Verifies that the annotation is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_annotation_id:
        pytest.skip("No annotation ID available - run create_annotation test first")

    new_content = f"Updated Test Annotation {uuid.uuid4()}"
    new_date_marker = "2024-03-21T12:00:00Z"

    response = await client.process_query(
        f"Use the update_annotation tool to update annotation ID {created_annotation_id} with "
        f"content {new_content} and date_marker {new_date_marker}. If successful, start your response with "
        "'Updated annotation successfully' and then list the annotation details."
    )

    assert (
        "updated annotation successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_annotation"

    print(f"Response: {response}")
    print("✅ update_annotation passed.")


@pytest.mark.asyncio
async def test_delete_cohort(client):
    """Delete a cohort.

    Verifies that the cohort is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_cohort_id:
        pytest.skip("No cohort ID available - run create_cohort test first")

    response = await client.process_query(
        f"Use the delete_cohort tool to delete cohort ID {created_cohort_id}. "
        "If successful, start your response with 'Cohort deleted successfully'."
    )

    assert (
        "cohort deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_cohort"

    print(f"Response: {response}")
    print("✅ delete_cohort passed.")


@pytest.mark.asyncio
async def test_list_dashboard_collaborators(client):
    """List all collaborators of a dashboard.

    Verifies that dashboard collaborators are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_dashboard_id:
        pytest.skip("No dashboard ID available - run create_dashboard test first")

    response = await client.process_query(
        f"Use the list_dashboard_collaborators tool to fetch collaborators for dashboard ID {created_dashboard_id}. "
        "If successful, start your response with 'Here are the dashboard collaborators' and then list them."
    )

    assert (
        "here are the dashboard collaborators" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_dashboard_collaborators"

    print(f"Response: {response}")
    print("✅ list_dashboard_collaborators passed.")


@pytest.mark.asyncio
async def test_add_dashboard_collaborator(client):
    """Add a collaborator to a dashboard.

    Verifies that the collaborator is added successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_dashboard_id:
        pytest.skip("No dashboard ID available - run create_dashboard test first")

    user_uuid = str(uuid.uuid4())
    level = 21

    response = await client.process_query(
        f"Use the add_dashboard_collaborator tool to add user {user_uuid} as a collaborator to dashboard ID {created_dashboard_id} with level {level}. "
        "If successful, start your response with 'Collaborator added successfully'."
    )

    assert (
        "collaborator added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_dashboard_collaborator"

    print(f"Response: {response}")
    print("✅ add_dashboard_collaborator passed.")


@pytest.mark.asyncio
async def test_get_dashboard_sharing(client):
    """Get sharing settings of a dashboard.

    Verifies that dashboard sharing settings are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_dashboard_id:
        pytest.skip("No dashboard ID available - run create_dashboard test first")

    response = await client.process_query(
        f"Use the get_dashboard_sharing tool to fetch sharing settings for dashboard ID {created_dashboard_id}. "
        "If successful, start your response with 'Here are the dashboard sharing settings' and then list them."
    )

    assert (
        "here are the dashboard sharing settings" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_dashboard_sharing"

    print(f"Response: {response}")
    print("✅ get_dashboard_sharing passed.")


@pytest.mark.asyncio
async def test_list_persons(client):
    """List all persons in a PostHog project.

    Verifies that persons are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """

    global person_id

    response = await client.process_query(
        "Use the list_persons tool to fetch all persons. "
        "If successful, start your response with 'Here are the persons' and then list them."
        "For each person, provide ID in the format 'ID: <person_id>'."
    )

    assert (
        "here are the persons" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_persons"

    # Extract first person ID from the response
    person_id = response.split("ID:")[1].strip()

    print(f"Extracted person ID: {person_id}")

    print(f"Response: {response}")
    print("✅ list_persons passed.")


@pytest.mark.asyncio
async def test_get_person(client):
    """Get details of a specific person.

    Verifies that person details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """

    response = await client.process_query(
        f"Use the get_person tool to fetch details for person ID {person_id}. "
        "If successful, start your response with 'Here are the person details' and then list them."
    )

    assert (
        "here are the person details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_person"

    print(f"Response: {response}")
    print("✅ get_person passed.")


@pytest.mark.asyncio
async def test_get_experiment(client):
    """Get details of a specific experiment.

    Verifies that experiment details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_experiment_id:
        pytest.skip("No experiment ID available - run create_experiment test first")

    response = await client.process_query(
        f"Use the get_experiment tool to fetch details for experiment ID {created_experiment_id}. "
        "If successful, start your response with 'Here are the experiment details' and then list them."
    )

    assert (
        "here are the experiment details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_experiment"

    print(f"Response: {response}")
    print("✅ get_experiment passed.")


@pytest.mark.asyncio
async def test_update_experiment(client):
    """Update an existing experiment.

    Verifies that the experiment is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_experiment_id:
        pytest.skip("No experiment ID available - run create_experiment test first")

    new_name = f"Updated Test Experiment {uuid.uuid4()}"
    new_description = "This is an updated test experiment description."

    response = await client.process_query(
        f"Use the update_experiment tool to update experiment ID {created_experiment_id} with "
        f"name {new_name} and description {new_description}. If successful, start your response with "
        "'Updated experiment successfully' and then list the experiment details."
    )

    assert (
        "updated experiment successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_experiment"

    print(f"Response: {response}")
    print("✅ update_experiment passed.")


@pytest.mark.asyncio
async def test_check_experiments_requiring_flag(client):
    """Get experiments that require flag implementation.

    Verifies that experiments requiring flag implementation are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the check_experiments_requiring_flag tool to fetch experiments requiring flag implementation. "
        "If successful, start your response with 'Here are the experiments requiring flag implementation' and then list them."
    )

    assert (
        "here are the experiments requiring flag implementation" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from check_experiments_requiring_flag"

    print(f"Response: {response}")
    print("✅ check_experiments_requiring_flag passed.")


@pytest.mark.asyncio
async def test_get_insight_sharing(client):
    """Get sharing settings of a specific insight.

    Verifies that insight sharing settings are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_insight_id:
        pytest.skip("No insight ID available - run create_insight test first")

    response = await client.process_query(
        f"Use the get_insight_sharing tool to fetch sharing settings for insight ID {created_insight_id}. "
        "If successful, start your response with 'Here are the insight sharing settings' and then list them."
    )

    assert (
        "here are the insight sharing settings" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_insight_sharing"

    print(f"Response: {response}")
    print("✅ get_insight_sharing passed.")


@pytest.mark.asyncio
async def test_get_insight_activity(client):
    """Get activity history for a specific insight.

    Verifies that insight activity history is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_insight_id:
        pytest.skip("No insight ID available - run create_insight test first")

    response = await client.process_query(
        f"Use the get_insight_activity tool to fetch activity history for insight ID {created_insight_id}. "
        "If successful, start your response with 'Here is the insight activity history' and then list it."
    )

    assert (
        "here is the insight activity history" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_insight_activity"

    print(f"Response: {response}")
    print("✅ get_insight_activity passed.")


@pytest.mark.asyncio
async def test_mark_insight_viewed(client):
    """Mark an insight as viewed.

    Verifies that the insight is marked as viewed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_insight_id:
        pytest.skip("No insight ID available - run create_insight test first")

    response = await client.process_query(
        f"Use the mark_insight_viewed tool to mark insight ID {created_insight_id} as viewed. "
        "If successful, start your response with 'Insight marked as viewed successfully'."
    )

    assert (
        "insight marked as viewed successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from mark_insight_viewed"

    print(f"Response: {response}")
    print("✅ mark_insight_viewed passed.")


@pytest.mark.asyncio
async def test_get_insights_activity(client):
    """Get activity history for all insights.

    Verifies that activity history for all insights is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_insights_activity tool to fetch activity history for all insights. "
        "If successful, start your response with 'Here is the activity history for all insights' and then list it."
    )

    assert (
        "here is the activity history for all insights" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_insights_activity"

    print(f"Response: {response}")
    print("✅ get_insights_activity passed.")


@pytest.mark.asyncio
async def test_get_trend_insights(client):
    """Get trend insights.

    Verifies that trend insights are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_trend_insights tool to fetch trend insights. "
        "If successful, start your response with 'Here are the trend insights' and then list them."
    )

    assert (
        "here are the trend insights" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_trend_insights"

    print(f"Response: {response}")
    print("✅ get_trend_insights passed.")


@pytest.mark.asyncio
async def test_create_trend_insight(client):
    """Create a trend insight.

    Verifies that the trend insight is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    name = f"Test Trend Insight {uuid.uuid4()}"
    filters = {
        "events": [{"id": "test_event"}],
        "display": "ActionsLineGraph",
        "interval": "day",
    }

    response = await client.process_query(
        f"Use the create_trend_insight tool to create a new trend insight with name {name} and filters {filters}. "
        "If successful, start your response with 'Trend insight created successfully' and then list the insight details."
    )

    assert (
        "trend insight created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_trend_insight"

    print(f"Response: {response}")
    print("✅ create_trend_insight passed.")


@pytest.mark.asyncio
async def test_list_cohorts(client):
    """List all cohorts in a PostHog project.

    Verifies that cohorts are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_cohorts tool to fetch all cohorts. "
        "If successful, start your response with 'Here are the cohorts' and then list them."
    )

    assert (
        "here are the cohorts" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_cohorts"

    print(f"Response: {response}")
    print("✅ list_cohorts passed.")


@pytest.mark.asyncio
async def test_get_cohort(client):
    """Get details of a specific cohort.

    Verifies that cohort details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_cohort_id:
        pytest.skip("No cohort ID available - run create_cohort test first")

    response = await client.process_query(
        f"Use the get_cohort tool to fetch details for cohort ID {created_cohort_id}. "
        "If successful, start your response with 'Here are the cohort details' and then list them."
    )

    assert (
        "here are the cohort details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_cohort"

    print(f"Response: {response}")
    print("✅ get_cohort passed.")


@pytest.mark.asyncio
async def test_update_cohort(client):
    """Update an existing cohort.

    Verifies that the cohort is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_cohort_id:
        pytest.skip("No cohort ID available - run create_cohort test first")

    new_name = f"Updated Test Cohort {uuid.uuid4()}"
    new_description = "This is an updated test cohort description."

    response = await client.process_query(
        f"Use the update_cohort tool to update cohort ID {created_cohort_id} with "
        f"name {new_name} and description {new_description}. If successful, start your response with "
        "'Updated cohort successfully' and then list the cohort details."
    )

    assert (
        "updated cohort successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_cohort"

    print(f"Response: {response}")
    print("✅ update_cohort passed.")


@pytest.mark.asyncio
async def test_list_dashboards(client):
    """List all dashboards in a PostHog project.

    Verifies that dashboards are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_dashboards tool to fetch all dashboards. "
        "If successful, start your response with 'Here are the dashboards' and then list them."
    )

    assert (
        "here are the dashboards" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_dashboards"

    print(f"Response: {response}")
    print("✅ list_dashboards passed.")


@pytest.mark.asyncio
async def test_get_dashboard(client):
    """Get details of a specific dashboard.

    Verifies that dashboard details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_dashboard_id:
        pytest.skip("No dashboard ID available - run create_dashboard test first")

    response = await client.process_query(
        f"Use the get_dashboard tool to fetch details for dashboard ID {created_dashboard_id}. "
        "If successful, start your response with 'Here are the dashboard details' and then list them."
    )

    assert (
        "here are the dashboard details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_dashboard"

    print(f"Response: {response}")
    print("✅ get_dashboard passed.")


@pytest.mark.asyncio
async def test_update_dashboard(client):
    """Update an existing dashboard.

    Verifies that the dashboard is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_dashboard_id:
        pytest.skip("No dashboard ID available - run create_dashboard test first")

    new_name = f"Updated Test Dashboard {uuid.uuid4()}"
    new_description = "This is an updated test dashboard description."

    response = await client.process_query(
        f"Use the update_dashboard tool to update dashboard ID {created_dashboard_id} with "
        f"name {new_name} and description {new_description}. If successful, start your response with "
        "'Updated dashboard successfully' and then list the dashboard details."
    )

    assert (
        "updated dashboard successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_dashboard"

    print(f"Response: {response}")
    print("✅ update_dashboard passed.")


@pytest.mark.asyncio
async def test_delete_dashboard(client):
    """Delete a dashboard.

    Verifies that the dashboard is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_dashboard_id:
        pytest.skip("No dashboard ID available - run create_dashboard test first")

    response = await client.process_query(
        f"Use the delete_dashboard tool to delete dashboard ID {created_dashboard_id}. "
        "If successful, start your response with 'Dashboard deleted successfully'."
    )

    assert (
        "dashboard deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_dashboard"

    print(f"Response: {response}")
    print("✅ delete_dashboard passed.")


@pytest.mark.asyncio
async def test_list_experiments(client):
    """List all experiments in a PostHog project.

    Verifies that experiments are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_experiments tool to fetch all experiments. "
        "If successful, start your response with 'Here are the experiments' and then list them."
    )

    assert (
        "here are the experiments" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_experiments"

    print(f"Response: {response}")
    print("✅ list_experiments passed.")


@pytest.mark.asyncio
async def test_list_insights(client):
    """List all insights in a PostHog project.

    Verifies that insights are listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_insights tool to fetch all insights. "
        "If successful, start your response with 'Here are the insights' and then list them."
    )

    assert (
        "here are the insights" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_insights"

    print(f"Response: {response}")
    print("✅ list_insights passed.")


@pytest.mark.asyncio
async def test_get_insight(client):
    """Get details of a specific insight.

    Verifies that insight details are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_insight_id:
        pytest.skip("No insight ID available - run create_insight test first")

    response = await client.process_query(
        f"Use the get_insight tool to fetch details for insight ID {created_insight_id}. "
        "If successful, start your response with 'Here are the insight details' and then list them."
    )

    assert (
        "here are the insight details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_insight"

    print(f"Response: {response}")
    print("✅ get_insight passed.")


@pytest.mark.asyncio
async def test_update_insight(client):
    """Update an existing insight.

    Verifies that the insight is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_insight_id:
        pytest.skip("No insight ID available - run create_insight test first")

    new_name = f"Updated Test Insight {uuid.uuid4()}"
    new_description = "This is an updated test insight description."

    response = await client.process_query(
        f"Use the update_insight tool to update insight ID {created_insight_id} with "
        f"name {new_name} and description {new_description}. If successful, start your response with "
        "'Updated insight successfully' and then list the insight details."
    )

    assert (
        "updated insight successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_insight"

    print(f"Response: {response}")
    print("✅ update_insight passed.")
