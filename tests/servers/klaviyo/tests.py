import pytest
import uuid


# Global variables to store created resources
metric_id = None
created_list_id = None
created_profile_id = None

# ===== SETUP =====
# You need to create a campaign before running this test and set the campaign_id variable
campaign_id = ""


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing resources from Klaviyo"""
    response = await client.list_resources()
    assert response, "No response returned from list_resources"
    print(f"Response: {response}")

    for i, resource in enumerate(response.resources):
        print(f"- {i}: {resource.name} ({resource.uri}) {resource.description}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading a resource from Klaviyo"""
    list_response = await client.list_resources()

    # Test reading a list resource
    list_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("klaviyo://list/")
    ]

    if len(list_resource_uri) > 0:
        list_resource_uri = list_resource_uri[0]
        response = await client.read_resource(list_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for list passed.")

    # Test reading a campaign resource
    campaign_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("klaviyo://campaign/")
    ]

    if len(campaign_resource_uri) > 0:
        campaign_resource_uri = campaign_resource_uri[0]
        response = await client.read_resource(campaign_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for campaign passed.")

    # Test reading a profile resource
    profile_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("klaviyo://profile/")
    ]

    if len(profile_resource_uri) > 0:
        profile_resource_uri = profile_resource_uri[0]
        response = await client.read_resource(profile_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for profile passed.")


# ===== CREATE Operations =====


@pytest.mark.asyncio
async def test_create_profile(client):
    """Test creating a new profile in Klaviyo"""
    global created_profile_id
    email = f"test_{uuid.uuid4()}@example.com"
    first_name = "Test"
    last_name = "User"

    response = await client.process_query(
        f"""Use the create_profile tool to create a new profile with email "{email}",
        first_name "{first_name}", and last_name "{last_name}".
        If successful, start your response with 'Profile created successfully' and then include the profile ID.
        Your format for ID will be ID: <profile_id>"""
    )

    assert (
        "profile created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_profile"

    try:
        created_profile_id = response.split("ID: ")[1].split()[0]
        print(f"Created profile ID: {created_profile_id}")
    except IndexError:
        pytest.fail("Could not extract profile ID from response")

    print(f"Response: {response}")
    print("✅ create_profile passed.")


@pytest.mark.asyncio
async def test_create_list(client):
    """Test creating a new list in Klaviyo"""
    global created_list_id
    list_name = f"Test List {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the create_list tool to create a new list with name "{list_name}".
        If successful, start your response with 'List created successfully' and then include the list ID.
        Your format for ID will be ID: <list_id>"""
    )

    assert (
        "list created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_list"

    try:
        created_list_id = response.split("ID: ")[1].split()[0]
        print(f"Created list ID: {created_list_id}")
    except IndexError:
        pytest.fail("Could not extract list ID from response")

    print(f"Response: {response}")
    print("✅ create_list passed.")


# ===== READ Operations =====


@pytest.mark.asyncio
async def test_get_profile(client):
    """Test getting a specific profile from Klaviyo"""
    if not created_profile_id:
        pytest.skip("No profile ID available - run create_profile test first")

    response = await client.process_query(
        f"""Use the get_profile tool to fetch profile with ID {created_profile_id}.
        If successful, start your response with 'Here is the profile information' and then list it."""
    )

    assert (
        "here is the profile information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_profile"

    print(f"Response: {response}")
    print("✅ get_profile passed.")


@pytest.mark.asyncio
async def test_get_profiles(client):
    """Test getting all profiles from Klaviyo"""
    response = await client.process_query(
        """Use the get_profiles tool to fetch all profiles.
        If successful, start your response with 'Here are the profiles' and then list them."""
    )

    assert (
        "here are the profiles" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_profiles"

    print(f"Response: {response}")
    print("✅ get_profiles passed.")


@pytest.mark.asyncio
async def test_get_list(client):
    """Test getting a specific list from Klaviyo"""
    if not created_list_id:
        pytest.skip("No list ID available - run create_list test first")

    response = await client.process_query(
        f"""Use the get_list tool to fetch list with ID {created_list_id}.
        If successful, start your response with 'Here is the list information' and then list it."""
    )

    assert (
        "here is the list information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_list"

    print(f"Response: {response}")
    print("✅ get_list passed.")


@pytest.mark.asyncio
async def test_get_lists(client):
    """Test getting all lists from Klaviyo"""
    response = await client.process_query(
        """Use the get_lists tool to fetch all lists.
        If successful, start your response with 'Here are the lists' and then list them."""
    )

    assert (
        "here are the lists" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_lists"

    print(f"Response: {response}")
    print("✅ get_lists passed.")


@pytest.mark.asyncio
async def test_get_list_profiles(client):
    """Test getting profiles from a specific list"""
    if not created_list_id:
        pytest.skip("No list ID available - run create_list test first")

    response = await client.process_query(
        f"""Use the get_list_profiles tool to fetch profiles from list with ID {created_list_id}.
        If successful, start your response with 'Here are the list profiles' and then list them."""
    )

    assert (
        "here are the list profiles" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_list_profiles"

    print(f"Response: {response}")
    print("✅ get_list_profiles passed.")


@pytest.mark.asyncio
async def test_list_campaigns(client):
    """Test listing campaigns from Klaviyo"""
    global campaign_id
    response = await client.process_query(
        """Use the list_campaigns tool to fetch campaigns with channel "email".
        If successful, start your response with 'Here are the campaigns' and then list them.
        Your format will be, Found <number> campaigns"""
    )

    assert (
        "here are the campaigns" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_campaigns"

    print(f"Response: {response}")
    print("✅ list_campaigns passed.")


@pytest.mark.asyncio
async def test_get_campaign(client):
    """Test getting a specific campaign from Klaviyo"""
    if not campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"""Use the get_campaign tool to fetch campaign with ID {campaign_id}.
        If successful, start your response with 'Here is the campaign information' and then list it."""
    )

    assert (
        "here is the campaign information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign"

    print(f"Response: {response}")
    print("✅ get_campaign passed.")


@pytest.mark.asyncio
async def test_list_metrics(client):
    """Test listing metrics from Klaviyo"""
    global metric_id
    response = await client.process_query(
        """Use the list_metrics tool to fetch all metrics.
        If successful, start your response with 'Here are the metrics' and then list them.
        Your format for ID will be ID: <metric_id>"""
    )

    assert (
        "here are the metrics" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_metrics"

    try:
        metric_id = response.split("ID: ")[1].split()[0]
        print(f"Metric ID: {metric_id}")
    except IndexError:
        pytest.fail("Could not extract metric ID from response")

    print(f"Response: {response}")
    print("✅ list_metrics passed.")


@pytest.mark.asyncio
async def test_get_metric(client):
    """Test getting a specific metric from Klaviyo"""
    # First get a metric ID from list_metrics
    response = await client.process_query(
        f"""Use the get_metric tool to fetch metric with ID {metric_id}.
        If successful, start your response with 'Here is the metric information' and then list it."""
    )

    assert (
        "here is the metric information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_metric"

    print(f"Response: {response}")
    print("✅ get_metric passed.")


# ===== UPDATE Operations =====


@pytest.mark.asyncio
async def test_update_profile(client):
    """Test updating a profile in Klaviyo"""
    if not created_profile_id:
        pytest.skip("No profile ID available - run create_profile test first")

    new_first_name = f"Updated {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the update_profile tool to update profile with ID {created_profile_id}
        and set first_name to "{new_first_name}".
        If successful, start your response with 'Profile updated successfully'."""
    )

    assert (
        "profile updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_profile"

    print(f"Response: {response}")
    print("✅ update_profile passed.")


@pytest.mark.asyncio
async def test_update_campaign(client):
    """Test updating a campaign in Klaviyo"""
    if not campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    new_name = f"Updated Campaign {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the update_campaign tool to update campaign with ID {campaign_id}
        and set name to "{new_name}".
        If successful, start your response with 'Campaign updated successfully'."""
    )

    assert (
        "campaign updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_campaign"

    print(f"Response: {response}")
    print("✅ update_campaign passed.")


@pytest.mark.asyncio
async def test_add_profiles_to_list(client):
    """Test adding profiles to a list in Klaviyo"""
    if not created_list_id or not created_profile_id:
        pytest.skip(
            "No list ID or profile ID available - run create_list and create_profile tests first"
        )

    response = await client.process_query(
        f"""Use the add_profiles_to_list tool to add profile with ID {created_profile_id}
        to list with ID {created_list_id}.
        If successful, start your response with 'Profiles added to list successfully'."""
    )

    assert (
        "profiles added to list successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_profiles_to_list"

    print(f"Response: {response}")
    print("✅ add_profiles_to_list passed.")


@pytest.mark.asyncio
async def test_remove_profiles_from_list(client):
    """Test removing profiles from a list in Klaviyo"""
    if not created_list_id or not created_profile_id:
        pytest.skip(
            "No list ID or profile ID available - run create_list and create_profile tests first"
        )

    response = await client.process_query(
        f"""Use the remove_profiles_from_list tool to remove profile with ID {created_profile_id}
        from list with ID {created_list_id}.
        If successful, start your response with 'Profiles removed from list successfully'."""
    )

    assert (
        "profiles removed from list successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from remove_profiles_from_list"

    print(f"Response: {response}")
    print("✅ remove_profiles_from_list passed.")


@pytest.mark.asyncio
async def test_send_campaign(client):
    """Test sending a campaign in Klaviyo"""
    if not campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"""Use the send_campaign tool to send campaign with ID {campaign_id}.
        If successful, start your response with 'Campaign sent successfully'."""
    )

    assert (
        "campaign sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_campaign"

    print(f"Response: {response}")
    print("✅ send_campaign passed.")


# ===== DELETE Operations =====


@pytest.mark.asyncio
async def test_delete_campaign(client):
    """Test deleting a campaign in Klaviyo"""
    if not campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"""Use the delete_campaign tool to delete campaign with ID {campaign_id}.
        If successful, start your response with 'Campaign deleted successfully'."""
    )

    assert (
        "campaign deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_campaign"

    print(f"Response: {response}")
    print("✅ delete_campaign passed.")
