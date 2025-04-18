import uuid
import pytest


@pytest.mark.asyncio
async def test_create_shopping_list(client):
    """Test creating a shopping list on Instacart"""
    # Generate a unique title to avoid conflicts
    list_title = f"Test Shopping List {uuid.uuid4()}"

    # Add instructions
    instructions = [
        "These are items for a basic breakfast.",
        "Add more items if needed.",
    ]

    # Send the query to create the shopping list
    response = await client.process_query(
        f"Use the create_shopping_list tool to create a shopping list with the title '{list_title}'. "
        f"Include the following items: organic bananas (1 bunch), milk (1 gallon), and whole wheat bread (1 loaf). "
        f"Add instructions: '{instructions[0]} {instructions[1]}'"
        f"\n\nIf it's successful, start your response with 'Shopping list created successfully'. Tell me the URL of the shopping list created as well"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the shopping list was created
    assert (
        "shopping list created successfully" in response.lower()
    ), f"Shopping list creation failed: {response}"
    assert (
        list_title in response
    ), f"Shopping list title not found in response: {response}"

    # Check if URL is included in the response
    assert (
        "https://" in response and "instacart" in response.lower()
    ), "Shopping list URL not found in response"

    print(f"Created shopping list with title: {list_title}")
    print("✅ Shopping list creation successful")


@pytest.mark.asyncio
async def test_create_shopping_list_with_display_text(client):
    """Test creating a shopping list with display text for items"""
    # Generate a unique title to avoid conflicts
    list_title = f"Test Shopping List with Display Text {uuid.uuid4()}"

    # Send the query to create the shopping list with display text
    response = await client.process_query(
        f"Use the create_shopping_list tool to create a shopping list with the title '{list_title}'. "
        f"Include the following items with custom display text: "
        f"Apples (name: 'Apple', quantity: 6, display_text: '6 Fresh Apples (any variety)') and "
        f"Chicken (name: 'Chicken Breast', quantity: 2, unit: 'pound', display_text: 'Boneless Skinless Chicken Breasts')."
        f"\n\nIf it's successful, start your response with 'Shopping list with display text created successfully'"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the shopping list was created with display text
    assert (
        "shopping list with display text created successfully" in response.lower()
    ), f"Shopping list creation with display text failed: {response}"
    assert (
        list_title in response
    ), f"Shopping list title not found in response: {response}"

    print(f"Created shopping list with display text: {list_title}")
    print("✅ Shopping list with display text creation successful")


@pytest.mark.asyncio
async def test_create_shopping_list_with_linkback(client):
    """Test creating a shopping list with a linkback URL"""
    # Generate a unique title to avoid conflicts
    list_title = f"Test Shopping List with Linkback {uuid.uuid4()}"

    # Define linkback URL
    linkback_url = "https://example.com/myrecipes"

    # Send the query to create the shopping list with linkback URL
    response = await client.process_query(
        f"Use the create_shopping_list tool to create a shopping list with the title '{list_title}'. "
        f"Include basic items like bread and milk. "
        f"Add a partner linkback URL: '{linkback_url}'"
        f"\n\nIf it's successful, start your response with 'Shopping list with linkback created successfully'"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the shopping list was created with linkback
    assert (
        "shopping list with linkback created successfully" in response.lower()
    ), f"Shopping list creation with linkback failed: {response}"
    assert (
        list_title in response
    ), f"Shopping list title not found in response: {response}"

    print(f"Created shopping list with linkback: {list_title}")
    print("✅ Shopping list with linkback creation successful")


@pytest.mark.asyncio
async def test_create_recipe(client):
    """Test creating a recipe on Instacart"""
    # Generate a unique title to avoid conflicts
    recipe_title = f"Test Recipe {uuid.uuid4()}"

    # Send the query to create the recipe
    response = await client.process_query(
        f"Use the create_recipe tool to create a recipe with the title '{recipe_title}'. "
        f"Include ingredients like flour (2 cups), sugar (1 cup), eggs (2), butter (1 cup), and vanilla extract (1 teaspoon). "
        f"Add instructions for baking a simple cake including preheating the oven, mixing ingredients, and baking time."
        f"\n\nIf it's successful, start your response with 'Recipe created successfully'. Write the URL to the recipe in the response."
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the recipe was created
    assert (
        "recipe created successfully" in response.lower()
    ), f"Recipe creation failed: {response}"
    assert recipe_title in response, f"Recipe title not found in response: {response}"

    # Check if URL is included in the response
    assert (
        "https://" in response and "instacart" in response.lower()
    ), "Recipe URL not found in response"

    print(f"Created recipe with title: {recipe_title}")
    print("✅ Recipe creation successful")


@pytest.mark.asyncio
async def test_create_recipe_with_author_and_servings(client):
    """Test creating a recipe with author and servings information"""
    # Generate a unique title to avoid conflicts
    recipe_title = f"Test Recipe with Author {uuid.uuid4()}"
    author_name = "Test Chef"
    servings = 4

    # Send the query to create the recipe with author and servings
    response = await client.process_query(
        f"Use the create_recipe tool to create a recipe with the title '{recipe_title}'. "
        f"Set the author to '{author_name}' and servings to {servings}. "
        f"Include basic ingredients for a pasta dish and simple cooking instructions."
        f"\n\nIf it's successful, start your response with 'Recipe with author and servings created successfully'"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the recipe was created with author and servings
    assert (
        "recipe with author and servings created successfully" in response.lower()
    ), f"Recipe creation with author and servings failed: {response}"
    assert recipe_title in response, f"Recipe title not found in response: {response}"

    print(f"Created recipe with author and servings: {recipe_title}")
    print("✅ Recipe with author and servings creation successful")


@pytest.mark.asyncio
async def test_create_recipe_with_pantry_items(client):
    """Test creating a recipe with pantry items enabled"""
    # Generate a unique title to avoid conflicts
    recipe_title = f"Test Recipe with Pantry Items {uuid.uuid4()}"

    # Send the query to create the recipe with pantry items enabled
    response = await client.process_query(
        f"Use the create_recipe tool to create a recipe with the title '{recipe_title}'. "
        f"Include common ingredients for a basic pasta dish. "
        f"Enable the pantry items feature so users can mark items they already have."
        f"\n\nIf it's successful, start your response with 'Recipe with pantry items created successfully'"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the recipe was created with pantry items enabled
    assert (
        "recipe with pantry items created successfully" in response.lower()
    ), f"Recipe creation with pantry items failed: {response}"
    assert recipe_title in response, f"Recipe title not found in response: {response}"

    print(f"Created recipe with pantry items enabled: {recipe_title}")
    print("✅ Recipe with pantry items creation successful")


@pytest.mark.asyncio
async def test_create_recipe_with_cooking_time(client):
    """Test creating a recipe with cooking time specified"""
    # Generate a unique title to avoid conflicts
    recipe_title = f"Test Recipe with Cooking Time {uuid.uuid4()}"
    cooking_time = 45  # minutes

    # Send the query to create the recipe with cooking time
    response = await client.process_query(
        f"Use the create_recipe tool to create a recipe with the title '{recipe_title}'. "
        f"Set the cooking time to {cooking_time} minutes. "
        f"Include ingredients and instructions for a simple casserole dish."
        f"\n\nIf it's successful, start your response with 'Recipe with cooking time created successfully'"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the recipe was created with cooking time
    assert (
        "recipe with cooking time created successfully" in response.lower()
    ), f"Recipe creation with cooking time failed: {response}"
    assert recipe_title in response, f"Recipe title not found in response: {response}"

    print(f"Created recipe with cooking time: {recipe_title}")
    print("✅ Recipe with cooking time creation successful")


@pytest.mark.asyncio
async def test_recipe_validation_missing_ingredients(client):
    """Test validation error when ingredients are missing"""
    # Generate a unique title to avoid conflicts
    recipe_title = f"Test Recipe Missing Ingredients {uuid.uuid4()}"

    # Send the query to create the recipe without ingredients
    response = await client.process_query(
        f"Use the create_recipe tool to create a recipe with the title '{recipe_title}', "
        f"but don't include any ingredients. Only add instructions. "
        f"This should result in an error since ingredients are required."
        f"\n\nIf an error occurs as expected, start your response with 'Validation error confirmed'"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the validation error was detected
    assert (
        "validation error confirmed" in response.lower()
        or "missing required parameters" in response.lower()
    ), f"Validation error test failed: {response}"

    print("✅ Recipe validation for missing ingredients successful")


@pytest.mark.asyncio
async def test_shopping_list_validation_missing_items(client):
    """Test validation error when line items are missing"""
    # Generate a unique title to avoid conflicts
    list_title = f"Test Shopping List Missing Items {uuid.uuid4()}"

    # Send the query to create the shopping list without line items
    response = await client.process_query(
        f"Use the create_shopping_list tool to create a shopping list with the title '{list_title}', "
        f"but don't include any line items. "
        f"This should result in an error since line items are required."
        f"\n\nIf an error occurs as expected, start your response with 'Validation error confirmed'"
    )

    print("\nRaw response from process_query:")
    print(response)
    print("-" * 80)

    # Verify the validation error was detected
    assert (
        "validation error confirmed" in response.lower()
        or "missing required parameters" in response.lower()
    ), f"Validation error test failed: {response}"

    print("✅ Shopping list validation for missing items successful")
