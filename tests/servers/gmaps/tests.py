import pytest
import re

place_id = ""


@pytest.mark.asyncio
async def test_address_to_coordinates(client):
    """Fetch the coordinates of an address.

    Verifies that the coordinates of an address are returned.

    Args:
        client: The test client fixture for the MCP server.
    """

    address = "San Francisco , California, CA"

    response = await client.process_query(
        f"Use the address_to_coordinates tool to fetch the coordinates of the address: {address}. "
        "If successful, start your response with 'Here are the coordinates' and then list them."
    )

    assert (
        "here are the coordinates" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from address_to_coordinates"

    print(f"Response: {response}")
    print("✅ address_to_coordinates passed.")


@pytest.mark.asyncio
async def test_coordinates_to_address(client):
    """Fetch the address of a set of coordinates.

    Verifies that the address of a set of coordinates are returned.

    Args:
        client: The test client fixture for the MCP server.
    """

    coordinates = "37.774929, -122.419418"  # San Francisco

    response = await client.process_query(
        f"Use the coordinates_to_address tool to fetch the address of the coordinates: {coordinates}. "
        "If successful, start your response with 'Here is the address' and then list it."
    )

    assert (
        "here is the address" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from coordinates_to_address"

    print(f"Response: {response}")
    print("✅ coordinates_to_address passed.")


@pytest.mark.asyncio
async def test_search_places(client):
    """Search for places around a set of coordinates.

    Verifies that the places around a set of coordinates are returned.

    Args:
        client: The test client fixture for the MCP server.
    """
    global place_id

    coordinates = "37.774929, -122.419418"
    query = "Rincon Park"
    limit = 5
    radius = 20000

    response = await client.process_query(
        f"Use the search_places tool to search for places around the coordinates: {coordinates}. "
        f"The query is: {query}, the limit is: {limit}, and the radius is: {radius}."
        "If successful, start your response with 'Here are the places' and return place_id: place_id"
    )

    assert (
        "here are the places" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from search_places"

    match = re.search(r"place_id:\s*([^\s]+)", response)
    place_id = match.group(1) if match else None

    print(f"Response: {response}")
    print("✅ search_places passed.")


@pytest.mark.asyncio
async def test_get_place_details(client):
    """Get details about a place.

    Verifies that the details of a place are returned.

    Args:
        client: The test client fixture for the MCP server.
    """

    response = await client.process_query(
        f"Use the get_place_details tool to fetch the details of the place: {place_id}. "
        "If successful, start your response with 'Here are the details' and then list them."
    )

    assert (
        "here are the details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_place_details"

    print(f"Response: {response}")
    print("✅ get_place_details passed.")


@pytest.mark.asyncio
async def test_get_place_reviews(client):
    """Get reviews about a place.

    Verifies that the reviews of a place are returned.

    Args:
        client: The test client fixture for the MCP server.
    """

    limit = 1

    response = await client.process_query(
        f"Use the get_place_reviews tool to fetch the reviews of the place: {place_id}. "
        f"The limit is: {limit}."
        "If successful, start your response with 'Here are the reviews' and then list them."
    )

    assert (
        "here are the reviews" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_place_reviews"

    print(f"Response: {response}")
    print("✅ get_place_reviews passed.")


@pytest.mark.asyncio
async def test_get_distance_matrix(client):
    """Get the distance and duration between two sets of coordinates.

    Verifies that the distance and duration between two sets of coordinates are returned.

    Args:
        client: The test client fixture for the MCP server.
    """

    origins = "San Francisco, CA"
    destinations = "Los Angeles, CA"

    response = await client.process_query(
        f"Use the get_distance_matrix tool to fetch the distance and duration between the following coordinates: {origins} and {destinations}."
        "If successful, start your response with 'Here are the distance and duration' and then list them."
    )

    assert (
        "here are the distance and duration" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_distance_matrix"

    print(f"Response: {response}")
    print("✅ get_distance_matrix passed.")


@pytest.mark.asyncio
async def test_get_elevation(client):
    """Get the elevation of a set of coordinates.

    Verifies that the elevation of a set of coordinates are returned.

    Args:
        client: The test client fixture for the MCP server.
    """

    coordinates = "37.774929, -122.419418"  # San Francisco

    response = await client.process_query(
        f"Use the get_elevation tool to fetch the elevation of the following coordinates: {coordinates}."
        "If successful, start your response with 'Here is the elevation' and then list it."
    )

    assert (
        "here is the elevation" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_elevation"

    print(f"Response: {response}")
    print("✅ get_elevation passed.")


@pytest.mark.asyncio
async def test_get_directions(client):
    """Get directions between two sets of coordinates.

    Verifies that the directions between two sets of coordinates are returned.

    Args:
        client: The test client fixture for the MCP server.
    """

    origin = "San Francisco, CA"
    destination = "Los Angeles, CA"

    response = await client.process_query(
        f"Use the get_directions tool to fetch the directions between the following coordinates: {origin} and {destination}."
        "If successful, start your response with 'Here are the directions' and then list them."
    )

    assert (
        "here are the directions" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_directions"

    print(f"Response: {response}")
    print("✅ get_directions passed.")
