import pytest
import random


@pytest.mark.asyncio
async def test_list_categories(client):
    """Test listing all categories using the tool"""
    response = await client.process_query(
        "Use the list_categories tool to list all categories on the Discourse forum."
    )

    eval = await client.llm_as_a_judge(
        "It should pass if the response successfully lists categories from the Discourse forum. The response should contain category information.",
        response,
    )

    assert eval["passed"], eval["reasoning"]
    print(eval)
    print("✅ List categories tool working")


@pytest.mark.asyncio
async def test_search_topics(client):
    """Test searching for topics"""
    response = await client.process_query(
        "Use the search_topics tool to search for topics with query 'welcome'."
        "if there is any error in the response directly from the tool, ensure to return the error message"
    )

    eval = await client.llm_as_a_judge(
        "It should pass if the response was successful in searching and finding response, its fine if it returns no results",
        response,
    )

    assert eval["passed"], eval["reasoning"]
    print(eval)
    print("✅ Search topics tool working")


@pytest.mark.asyncio
async def test_get_user_info(client):
    """Test getting user information"""
    admin_username = "system"

    response = await client.process_query(
        f"Use the get_user_info tool to get information about the user with username '{admin_username}'."
    )

    eval = await client.llm_as_a_judge(
        f"It should pass if the response successfully retrieves information about the user '{admin_username}'. The response should contain user information.",
        response,
    )

    assert eval["passed"], eval["reasoning"]
    print(eval)
    print("✅ Get user info tool working")


@pytest.mark.asyncio
async def test_create_topic_and_post_flow(client):
    """Test creating a topic and then posting in that topic"""
    categories_response = await client.process_query(
        "Use the list_categories tool to list all categories on the Discourse forum."
    )

    category_id = await client.fetch_value_from_response(
        categories_response,
        {"extract_category_id": "extract any one category id from the response"},
    )

    assert category_id, "Failed to find a valid category ID"

    title = f"Test Topic from MCP API {random.randint(1, 1000000)}"
    create_topic_response = await client.process_query(
        f"Use the create_topic tool to create a new topic with title '{title}' and random content not more then 2 lines', "
        f"and category_id {category_id}. and return post id"
    )

    eval_topic = await client.llm_as_a_judge(
        f"It should pass if the response successfully creates a new topic with title '{title}'. The response should contain a topic_id.",
        create_topic_response,
    )

    assert eval_topic["passed"], eval_topic["reasoning"]

    topic_id = await client.fetch_value_from_response(
        create_topic_response,
        {"extract_topic_id": "extract the topic id from the response"},
    )

    assert topic_id, "Failed to extract topic ID from response"

    post_content = "This is a reply to the test topic via the MCP API."

    create_post_response = await client.process_query(
        f"Use the create_post tool to create a new post in topic {topic_id} with raw '{post_content}'.`"
        f"and return post id"
    )

    eval_post = await client.llm_as_a_judge(
        f"It should pass if the response successfully creates a new post in topic ID {topic_id}. The response should contain a post id.",
        create_post_response,
    )

    assert eval_post["passed"], eval_post["reasoning"]
    print(eval_post)
    print("✅ Create topic and post flow working")
