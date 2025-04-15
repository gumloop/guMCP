import pytest
import re

# Define test configurations for each tool
TOOL_TESTS = [
    # Overview tools
    {
        "name": "domain_rating",
        "args": "for ahrefs.com",
        "expected_keyword": "domain_rating",
        "regex_pattern": r"domain_rating:\s*\d+",
        "description": "domain rating information",
    },
    {
        "name": "backlinks_stats",
        "args": "for wordcount.com",
        "expected_keyword": "backlinks_stats_summary",
        "regex_pattern": None,
        "description": "backlinks statistics",
    },
    {
        "name": "outlinks_stats",
        "args": "for ahrefs.com",
        "expected_keyword": "outlinks_stats_summary",
        "regex_pattern": None,
        "description": "outgoing links statistics",
    },
    {
        "name": "metrics",
        "args": "for wordcount.com with mode='domain' and date='2023-06-01'",
        "expected_keyword": "metrics_status_traffic",
        "regex_pattern": r"metrics_status_traffic:\s*\d+",
        "description": "comprehensive site metrics",
    },
    {
        "name": "metrics_by_country",
        "args": "for ahrefs.com with date='2023-06-01'",
        "expected_keyword": "countries_count",
        "regex_pattern": r"countries_count:\s*\d+",
        "description": "metrics filtered by country",
        "select_param": "paid_cost",
    },
    {
        "name": "pages_by_traffic",
        "args": "for ahrefs.com",
        "expected_keyword": "traffic_pages_count",
        "regex_pattern": r"traffic_pages_count:\s*\d+",
        "description": "pages by traffic report",
    },
    # Backlinks profile tools
    {
        "name": "backlinks",
        "args": "for wordcount.com with date='2023-06-01' and limit=5",
        "expected_keyword": "backlink_count",
        "regex_pattern": r"backlink_count:\s*\d+",
        "description": "backlinks information",
    },
    {
        "name": "broken_backlinks",
        "args": "for ahrefs.com with date='2023-06-01' and limit=5",
        "expected_keyword": "broken_backlinks_count",
        "regex_pattern": r"broken_backlinks_count:\s*\d+",
        "description": "broken backlinks information",
    },
    {
        "name": "refdomains",
        "args": "for wordcount.com with date='2023-06-01' and limit=5",
        "expected_keyword": "refdomains_count",
        "regex_pattern": r"refdomains_count:\s*\d+",
        "description": "referring domains information",
    },
    {
        "name": "anchors",
        "args": "for ahrefs.com with date='2023-06-01' and limit=5",
        "expected_keyword": "anchors_count",
        "regex_pattern": r"anchors_count:\s*\d+",
        "description": "anchor text information",
    },
    # Organic search tools
    {
        "name": "organic_keywords",
        "args": "for wordcount.com with date='2023-06-01' and limit=5 and country='us'",
        "expected_keyword": "keywords_count",
        "regex_pattern": r"keywords_count:\s*\d+",
        "description": "organic keywords information",
        "select_param": "best_position",
    },
    {
        "name": "organic_competitors",
        "args": "for ahrefs.com with date='2023-06-01' and limit=5 and country='us'",
        "expected_keyword": "competitors_count",
        "regex_pattern": r"competitors_count:\s*\d+",
        "description": "competitor information",
        "select_param": "competitor_domain",
    },
    {
        "name": "top_pages",
        "args": "for wordcount.com with date='2023-06-01' and limit=5",
        "expected_keyword": "pages_count",
        "regex_pattern": r"pages_count:\s*\d+",
        "description": "top organic pages",
        "select_param": "top_keyword_best_position",
    },
    # Paid search tools
    {
        "name": "paid_pages",
        "args": "for ahrefs.com with date='2023-06-01' and limit=5",
        "expected_keyword": "paid_pages_count",
        "regex_pattern": r"paid_pages_count:\s*\d+",
        "description": "paid pages information",
        "select_param": "ads_count",
    },
    # Pages tools
    {
        "name": "best_by_external_links",
        "args": "for ahrefs.com with limit=5",
        "expected_keyword": "external_links_pages_count",
        "regex_pattern": r"external_links_pages_count:\s*\d+",
        "description": "pages with most external links",
        "select_param": "url_to,title_target,links_to_target",
    },
    {
        "name": "best_by_internal_links",
        "args": "for wordcount.com with limit=5",
        "expected_keyword": "internal_links_pages_count",
        "regex_pattern": r"internal_links_pages_count:\s*\d+",
        "description": "pages with most internal links",
        "select_param": "url_to,title_target,links_to_target",
    },
    # Outgoing links tools
    {
        "name": "linked_domains",
        "args": "for ahrefs.com with date='2023-06-01' and limit=5",
        "expected_keyword": "linked_domains_count",
        "regex_pattern": r"linked_domains_count:\s*\d+",
        "description": "linked domains information",
        "select_param": "dofollow_linked_domains",
    },
    {
        "name": "outgoing_external_anchors",
        "args": "for wordcount.com with limit=5",
        "expected_keyword": "outgoing_external_anchors_count",
        "regex_pattern": r"outgoing_external_anchors_count:\s*\d+",
        "description": "outgoing external anchor text",
        "select_param": "anchor",
    },
    {
        "name": "outgoing_internal_anchors",
        "args": "for ahrefs.com with limit=5",
        "expected_keyword": "outgoing_internal_anchors_count",
        "regex_pattern": r"outgoing_internal_anchors_count:\s*\d+",
        "description": "outgoing internal anchor text",
        "select_param": "anchor",
    },
    # History tracking tools
    {
        "name": "domain_rating_history",
        "args": "for wordcount.com with date_from='2023-01-01' and date_to='2023-06-01'",
        "expected_keyword": "history_points_count",
        "regex_pattern": r"history_points_count:\s*\d+",
        "description": "domain rating history",
    },
    {
        "name": "url_rating_history",
        "args": "for https://ahrefs.com with date_from='2023-01-01' and date_to='2023-06-01'",
        "expected_keyword": "url_history_points_count",
        "regex_pattern": r"url_history_points_count:\s*\d+",
        "description": "URL rating history",
    },
    {
        "name": "pages_history",
        "args": "for wordcount.com with date_from='2023-01-01' and date_to='2023-06-01'",
        "expected_keyword": "pages_history_points_count",
        "regex_pattern": r"pages_history_points_count:\s*\d+",
        "description": "pages history",
    },
    {
        "name": "refdomains_history",
        "args": "for ahrefs.com with date_from='2023-01-01' and date_to='2023-06-01'",
        "expected_keyword": "refdomains_history_points_count",
        "regex_pattern": r"refdomains_history_points_count:\s*\d+",
        "description": "referring domains history",
    },
    {
        "name": "keywords_history",
        "args": "for wordcount.com with date_from='2023-01-01' and date_to='2023-06-01'",
        "expected_keyword": "keywords_history_points_count",
        "regex_pattern": r"keywords_history_points_count:\s*\d+",
        "description": "keywords history",
    },
    {
        "name": "metrics_history",
        "args": "for ahrefs.com with date_from='2023-01-01' and date_to='2023-06-01'",
        "expected_keyword": "metrics_history_points_count",
        "regex_pattern": r"metrics_history_points_count:\s*\d+",
        "description": "metrics history",
    },
    {
        "name": "total_search_volume_history",
        "args": "for wordcount.com with date_from='2023-01-01' and date_to='2023-06-01'",
        "expected_keyword": "volume_history_points",
        "regex_pattern": r"volume_history_points:\s*\d+",
        "description": "search volume history",
    },
    # Keywords Explorer tools
    {
        "name": "keywords_overview",
        "args": "for the keyword 'ahrefs' in country 'us'",
        "expected_keyword": "keyword_clicks",
        "regex_pattern": r"keyword_clicks:\s*\d+",
        "description": "keyword overview information",
        "select_param": "clicks",
    },
    {
        "name": "volume_by_country",
        "args": "for the keyword 'wordcount'",
        "expected_keyword": "countries_count",
        "regex_pattern": r"countries_count:\s*\d+",
        "description": "keyword volume by country",
    },
    {
        "name": "matching_terms",
        "args": "for the keyword 'ahrefs'",
        "expected_keyword": "matching_terms_count",
        "regex_pattern": r"matching_terms_count:\s*\d+",
        "description": "matching terms",
        "select_param": "global_volume",
    },
    {
        "name": "related_terms",
        "args": "for the keyword 'wordcount' with view_for='top_10' and terms='all'",
        "expected_keyword": "related_terms_count",
        "regex_pattern": r"related_terms_count:\s*\d+",
        "description": "related terms",
    },
    {
        "name": "search_suggestions",
        "args": "for the keyword 'ahrefs'",
        "expected_keyword": "suggestions_count",
        "regex_pattern": r"suggestions_count:\s*\d+",
        "description": "search suggestions",
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_config", TOOL_TESTS)
async def test_ahrefs_tool(client, tool_config):
    """Generic test function for Ahrefs tools"""
    tool_name = tool_config["name"]
    args = tool_config["args"]
    expected_keyword = tool_config["expected_keyword"]
    regex_pattern = tool_config.get("regex_pattern")
    description = tool_config["description"]
    expect_success = tool_config.get("expect_success", False)
    select_param = tool_config.get("select_param", "")

    # Create prompt for the client
    prompt = (
        "Not interested in your recommendations or what you think is best practice, just use what's given. "
        "Only pass required arguments to the tool and in case I haven't provided a required argument, you can try to pass your own that makes sense. "
        f"Use the {tool_name} tool to get {description} {args}. "
        f"Make sure to use EXACTLY this select parameter: '{select_param}'. "
        f"Only return the {expected_keyword} with keyword '{expected_keyword}' if successful and if keyword contains 'count', count the output and just pass the count or error with keyword 'error_message'. "
        "Sample response: keyword: output_data"
    )

    response = await client.process_query(prompt)

    if "error_message" in response:
        pytest.fail(f"{tool_name} : Failed to get {description}: {response}")

    assert (
        expected_keyword in response
    ), f"{tool_name} : Expected {expected_keyword} in response: {response}"

    if regex_pattern:
        assert re.search(
            regex_pattern, response
        ), f"{tool_name} : Expected {regex_pattern} pattern in response: {response}"

    if expect_success:
        assert (
            "success" in response.lower()
        ), f"{tool_name} : Expected success status in response: {response}"

    print(f"✅ {tool_name.replace('_', ' ').title()} test completed")
