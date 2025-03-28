import pytest


@pytest.mark.asyncio
async def test_search_with_recency(client):
    """Test searching with recency filter"""
    response = await client.process_query(
        "Use the search tool to search for 'latest AI developments' with recency filter set to 'week'. "
        "If you find anything, start your response with 'Search results found' and then provide the information."
    )

    assert "search results found" in response.lower(), f"Search failed: {response}"
    print("Search results:")
    print(f"\t{response}")
    print("✅ Search with recency filter working")


@pytest.mark.asyncio
async def test_code_assistant(client):
    """Test code assistant functionality"""
    response = await client.process_query(
        "Use the chat tool to help with this Python problem: 'Write a simple function to calculate fibonacci numbers'. "
        "If you can provide a solution, start your response with 'Code solution provided' and then show the code."
    )

    assert (
        "code solution provided" in response.lower()
    ), f"Code assistant failed: {response}"
    print("Code assistant response:")
    print(f"\t{response}")
    print("✅ Code assistant working")


@pytest.mark.asyncio
async def test_chat_with_different_models(client):
    """Test chat functionality with different models"""
    models = ["sonar", "sonar-pro"]

    for model in models:
        response = await client.process_query(
            f"Use the chat tool with model '{model}' to explain what is quantum computing. "
            f"If you can provide an explanation, start your response with 'Using {model} model' "
            "and then provide the explanation."
        )

        assert (
            f"using {model} model" in response.lower()
        ), f"Chat with {model} failed: {response}"
        print(f"Chat response from {model}:")
        print(f"\t{response}")

    print("✅ Chat with different models working")


@pytest.mark.asyncio
async def test_search_with_related_questions(client):
    """Test search with related questions enabled"""
    response = await client.process_query(
        "Use the search tool to search for 'machine learning basics' with return_related set to true. "
        "If you find results and related questions, start your response with 'Results with related questions' "
        "and include both the search results and related questions."
    )

    assert (
        "results with related questions" in response.lower()
    ), f"Search with related questions failed: {response}"
    print("Search results with related questions:")
    print(f"\t{response}")
    print("✅ Search with related questions working")
