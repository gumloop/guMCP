import os
import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing workspaces and forms from Typeform"""
    response = await client.list_resources()
    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    print("Typeform resources found:")
    workspaces = []
    forms = []

    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")
        # Convert AnyUrl to string before checking
        uri_str = str(resource.uri)
        if "workspace" in uri_str:
            workspaces.append(resource)
        elif "form" in uri_str:
            forms.append(resource)

    print(f"Found {len(workspaces)} workspaces and {len(forms)} forms")
    print("✅ Successfully listed Typeform resources")

    # Return resources for use in other tests
    return {"workspaces": workspaces, "forms": forms}


@pytest.mark.asyncio
async def test_read_workspace(client):
    """Test reading a Typeform workspace"""
    # First list resources to get a valid workspace ID
    resources = await test_list_resources(client)
    workspaces = resources["workspaces"]

    # Skip test if no workspaces found
    if not workspaces:
        print("⚠️ No Typeform workspaces found to test reading")
        pytest.skip("No Typeform workspaces available for testing")
        return

    # Test with the first workspace
    workspace_resource = workspaces[0]
    response = await client.read_resource(workspace_resource.uri)

    assert (
        response and response.contents
    ), f"Response should contain workspace contents: {response}"

    # Parse the JSON content
    import json

    workspace_data = json.loads(response.contents[0].text)

    assert "workspace" in workspace_data, "Workspace data should be in the response"
    assert "forms" in workspace_data, "Workspace forms should be in the response"

    print("Workspace read:")
    print(f"  - Name: {workspace_data['workspace'].get('name')}")
    print(f"  - Forms in workspace: {len(workspace_data['forms'])}")

    print("✅ Successfully read Typeform workspace")
    return workspace_data["workspace"]["id"]


@pytest.mark.asyncio
async def test_read_form(client):
    """Test reading a Typeform form"""
    # First list resources to get a valid form ID
    resources = await test_list_resources(client)
    forms = resources["forms"]

    # Skip test if no forms found
    if not forms:
        print("⚠️ No Typeform forms found to test reading")
        pytest.skip("No Typeform forms available for testing")
        return

    # Test with the first form
    form_resource = forms[0]
    response = await client.read_resource(form_resource.uri)

    assert (
        response and response.contents
    ), f"Response should contain form contents: {response}"

    # Parse the JSON content
    import json

    form_data = json.loads(response.contents[0].text)

    assert "form" in form_data, "Form data should be in the response"
    assert (
        "responses_summary" in form_data
    ), "Responses summary should be in the response"

    print("Form read:")
    print(f"  - Title: {form_data['form'].get('title')}")
    print(f"  - Total responses: {form_data['responses_summary'].get('total_items')}")

    print("✅ Successfully read Typeform form")
    return form_data["form"]["id"]


def has_anthropic_api_key():
    """Check if ANTHROPIC_API_KEY is set in environment"""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.mark.asyncio
async def test_list_workspaces_tool(client):
    """Test the list_workspaces tool"""
    if not has_anthropic_api_key():
        pytest.skip("ANTHROPIC_API_KEY not set, skipping tool test")

    response = await client.process_query(
        "Use the list_workspaces tool to list all workspaces in my Typeform account."
    )

    # Verify that the assistant attempted to list workspaces
    assert (
        "workspace" in response.lower()
    ), f"Workspace listing not performed: {response}"

    print("List workspaces response:")
    print(f"{response}")

    print("✅ List workspaces tool working")


@pytest.mark.asyncio
async def test_list_forms_by_workspace(client):
    """Test the list_forms_by_workspace tool"""
    # First get a valid workspace ID
    try:
        workspace_id = await test_read_workspace(client)
    except pytest.skip.Exception:
        pytest.skip("No workspaces available for testing")
        return

    if not has_anthropic_api_key():
        pytest.skip("ANTHROPIC_API_KEY not set, skipping tool test")

    response = await client.process_query(
        f"Use the list_forms_by_workspace tool to list all forms in the workspace with ID '{workspace_id}'."
    )

    # Verify that the assistant attempted to list forms by workspace
    assert (
        "workspace" in response.lower() and "form" in response.lower()
    ), f"Forms by workspace listing not performed: {response}"

    print("List forms by workspace response:")
    print(f"{response}")

    print("✅ List forms by workspace tool working")


@pytest.mark.asyncio
async def test_search_forms(client):
    """Test the search_forms tool"""
    if not has_anthropic_api_key():
        pytest.skip("ANTHROPIC_API_KEY not set, skipping tool test")

    # Use a generic search term that's likely to find something
    search_query = "test"
    response = await client.process_query(
        f"Use the search_forms tool to search for forms containing '{search_query}' in their title."
    )

    # Verify that the assistant attempted to search forms
    assert (
        "form" in response.lower() and search_query.lower() in response.lower()
    ), f"Form search not performed: {response}"

    print("Search forms response:")
    print(f"{response}")

    print("✅ Search forms tool working")


@pytest.mark.asyncio
async def test_search_forms_by_workspace(client):
    """Test the search_forms tool with workspace filter"""
    # First get a valid workspace ID
    try:
        workspace_id = await test_read_workspace(client)
    except pytest.skip.Exception:
        pytest.skip("No workspaces available for testing")
        return

    if not has_anthropic_api_key():
        pytest.skip("ANTHROPIC_API_KEY not set, skipping tool test")

    # Use a generic search term that's likely to find something
    search_query = "test"
    response = await client.process_query(
        f"Use the search_forms tool to search for forms containing '{search_query}' in their title, but only in the workspace with ID '{workspace_id}'."
    )

    # Verify that the assistant attempted to search forms in a specific workspace
    assert (
        "workspace" in response.lower() and search_query.lower() in response.lower()
    ), f"Form search by workspace not performed: {response}"

    print("Search forms by workspace response:")
    print(f"{response}")

    print("✅ Search forms by workspace tool working")


@pytest.mark.asyncio
async def test_get_form_responses(client):
    """Test the get_form_responses tool"""
    # First get a valid form ID
    try:
        form_id = await test_read_form(client)
    except pytest.skip.Exception:
        pytest.skip("No forms available for testing")
        return

    if not has_anthropic_api_key():
        pytest.skip("ANTHROPIC_API_KEY not set, skipping tool test")

    response = await client.process_query(
        f"Use the get_form_responses tool to get the responses from the form with ID '{form_id}', limiting to 5 responses."
    )

    # Verify that the assistant attempted to get form responses
    assert (
        "response" in response.lower() and "form" in response.lower()
    ), f"Get form responses not performed: {response}"

    print("Get form responses:")
    print(f"{response}")

    print("✅ Get form responses tool working")


@pytest.mark.asyncio
async def test_get_form_responses_with_fields(client):
    """Test the get_form_responses tool with field filtering"""
    # First get a valid form ID and identify a field
    try:
        form_id = await test_read_form(client)
    except pytest.skip.Exception:
        pytest.skip("No forms available for testing")
        return

    if not has_anthropic_api_key():
        pytest.skip("ANTHROPIC_API_KEY not set, skipping tool test")

    # Get form details to find field IDs
    form_uri = f"typeform:///form/{form_id}"
    form_response = await client.read_resource(form_uri)

    import json

    form_data = json.loads(form_response.contents[0].text)

    # Get the first field ID if available
    field_ids = []
    if "form" in form_data and "fields" in form_data["form"]:
        fields = form_data["form"]["fields"]
        if fields and len(fields) > 0:
            field_ids = [fields[0]["id"]]

    field_param = (
        f"with specific field filtering to only include {field_ids}"
        if field_ids
        else ""
    )

    response = await client.process_query(
        f"Use the get_form_responses tool to get the responses from the form with ID '{form_id}', limiting to 3 responses {field_param}."
    )

    # Verify that the assistant attempted to get form responses with field filtering
    assert (
        "response" in response.lower() and "form" in response.lower()
    ), f"Get form responses with fields not performed: {response}"

    print("Get form responses with field filtering:")
    print(f"{response}")

    print("✅ Get form responses with field filtering tool working")
