import pytest
import re
import json


@pytest.mark.asyncio
async def test_serpapi_search(client):
    """Test the serpapi_search tool to search for 'gumloop university' and extract titles"""
    response = await client.process_query(
        "Use the serpapi_search tool to search for 'gumloop university'. "
        "After getting the results, extract the titles from organic_results and "
        "return them with the prefix 'title_data:' followed by the titles separated by commas."
    )

    title_match = re.search(r"title_data:(.*?)(?:\n|$)", response, re.DOTALL)
    assert title_match, f"Expected 'title_data:' in response, but got: {response}"

    titles = title_match.group(1).strip()
    assert "gumloop" in titles.lower(), f"Expected 'gumloop' in titles: {titles}"

    print("✅ SerpAPI search completed successfully")
