import os
import sys
import json
import logging
from pathlib import Path
import httpx
from typing import Optional, Iterable, Dict, Any, List

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
AHREFS_API_URL = "https://api.ahrefs.com/v3"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

SITE_EXPLORER_DEFAULT_SELECT = {
    "backlinks": "ahrefs_rank_source,ahrefs_rank_target,alt,anchor,broken_redirect_new_target,broken_redirect_reason,broken_redirect_source,class_c,domain_rating_source,domain_rating_target,drop_reason,encoding,first_seen,first_seen_link,http_code,http_crawl,ip_source,is_alternate,is_canonical,is_content,is_dofollow,is_form,is_frame,is_image,is_nofollow,is_redirect,is_root_source,url_from,url_to",
    "broken_backlinks": "ahrefs_rank_source,ahrefs_rank_target,alt,anchor,class_c,domain_rating_source,domain_rating_target,encoding,first_seen,first_seen_link,http_code,http_code_target,http_crawl,ip_source,is_alternate,is_canonical,is_content,is_dofollow,is_form,is_frame,is_image,is_nofollow,is_redirect,is_root_source,url_from,url_to",
    "refdomains": "dofollow_linked_domains,dofollow_links,dofollow_refdomains,domain,domain_rating,first_seen,ip_source,is_root_domain,last_seen,links_to_target,lost_links,new_links,positions_source_domain,traffic_domain",
    "anchors": "anchor,dofollow_links,first_seen,last_seen,links_to_target,lost_links,new_links,refdomains,refpages,top_domain_rating",
    "organic_keywords": "keyword,best_position,keyword_difficulty,volume,cpc,traffic,serp_features,language",
    "organic_competitors": "domain,domain_rating,intersections,keywords,keywords_unique,traffic,traffic_estimated",
    "top_pages": "url,top_keyword,keywords,traffic,traffic_value",
    "paid_pages": "url,keywords,sum_traffic,value,ads_count",
    "best_by_external_links": "url_to,title_target,links_to_target,refdomains_target,dofollow_to_target",
    "best_by_internal_links": "url_to,title_target,links_to_target,dofollow_to_target",
    "linked_domains": "domain,domain_rating,dofollow_linked_domains,dofollow_links,dofollow_refdomains,first_seen,is_root_domain,linked_domain_traffic,linked_pages,links_from_target",
    "outgoing_external_anchors": "anchor,linked_domains,linked_pages,links_from_target,dofollow_links",
    "outgoing_internal_anchors": "anchor,linked_pages,links_from_target,dofollow_links",
    "metrics_history": "date,org_cost,org_traffic,paid_cost,paid_traffic",
    "keywords_history": "date,top3,top4_10,top11_plus",
}

KEYWORD_DIFFICULTY_DEFAULT_SELECT = "keyword,difficulty"

KEYWORDS_EXPLORER_DEFAULT_SELECT = {
    "keywords_overview": "keyword,difficulty,volume",
    "matching_terms": "keyword,difficulty,volume",
    "related_terms": "keyword,difficulty,volume",
    "search_suggestions": "keyword,difficulty,volume",
}


def authenticate_and_save_ahrefs_key(user_id):
    logger = logging.getLogger("ahrefs")
    logger.info(f"Starting Ahrefs authentication for user {user_id}...")

    auth_client = create_auth_client()
    api_key = input("Please enter your Ahrefs API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    auth_client.save_user_credentials("ahrefs", user_id, {"api_key": api_key})
    logger.info(f"Ahrefs API key saved for user {user_id}. You can now run the server.")
    return api_key


async def get_ahrefs_credentials(user_id, api_key=None):
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials("ahrefs", user_id)

    def handle_missing_credentials():
        error_str = f"Ahrefs API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    api_key = (
        credentials_data.get("api_key")
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


async def make_ahrefs_request(endpoint, params, api_key):
    if not api_key:
        raise ValueError("Ahrefs API key is required")

    url = f"{AHREFS_API_URL}/{endpoint}"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, params=params, headers=headers, timeout=30.0
            )
            response.raise_for_status()
            response_json = response.json()
            response_json["_status_code"] = response.status_code
            return response_json
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        )
        error_message = f"Ahrefs API error: {e.response.status_code}"
        try:
            error_details = e.response.json()
            if isinstance(error_details, dict) and "error" in error_details:
                error_message = error_details["error"]
        except:
            pass
        raise ValueError(error_message)
    except Exception as e:
        logger.error(f"Error making request to Ahrefs API: {str(e)}")
        raise ValueError(f"Error communicating with Ahrefs API: {str(e)}")


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("ahrefs-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List saved reports from Ahrefs"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Ahrefs"""
        logger.info(f"Listing tools for user: {server.user_id}")

        # Overview tools
        overview_tools = [
            Tool(
                name="domain_rating",
                description="Get domain rating for a domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain to analyze",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="backlinks_stats",
                description="Get backlinks statistics for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="outlinks_stats",
                description="Get outlinks statistics for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target"],
                },
            ),
            Tool(
                name="metrics",
                description="Get comprehensive metrics for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="metrics_by_country",
                description="Get metrics filtered by country for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return (default: paid_cost,paid_keywords,org_cost,paid_pages,org_keywords_1_3,org_keywords,org_traffic,paid_traffic,country)",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="pages_by_traffic",
                description="Get pages by traffic for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="domain_rating_history",
                description="Get domain rating history for a domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain to analyze",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for history in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for history in YYYY-MM-DD format",
                        },
                        "history_grouping": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time interval for grouping historical data",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date_from"],
                },
            ),
            Tool(
                name="url_rating_history",
                description="Get URL rating history for a URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target URL to analyze",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for history in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for history in YYYY-MM-DD format",
                        },
                        "history_grouping": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time interval for grouping historical data",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date_from"],
                },
            ),
            Tool(
                name="refdomains_history",
                description="Get referring domains history for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for history in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for history in YYYY-MM-DD format",
                        },
                        "history_grouping": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time interval for grouping historical data",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date_from"],
                },
            ),
            Tool(
                name="pages_history",
                description="Get pages history for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for history in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for history in YYYY-MM-DD format",
                        },
                        "history_grouping": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time interval for grouping historical data",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date_from"],
                },
            ),
            Tool(
                name="metrics_history",
                description="Get metrics history for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for history in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for history in YYYY-MM-DD format",
                        },
                        "history_grouping": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time interval for grouping historical data",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return (default: date,org_cost,org_traffic,paid_cost,paid_traffic)",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date_from"],
                },
            ),
            Tool(
                name="keywords_history",
                description="Get keywords history for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for history in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for history in YYYY-MM-DD format",
                        },
                        "history_grouping": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time interval for grouping historical data",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return (default: date,top3,top4_10,top11_plus)",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date_from"],
                },
            ),
            Tool(
                name="total_search_volume_history",
                description="Get total search volume history for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date for history in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date for history in YYYY-MM-DD format",
                        },
                        "history_grouping": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time interval for grouping historical data",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "Mode of analysis (default: subdomains)",
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "top_positions": {
                            "type": "string",
                            "enum": ["top_10", "top_100"],
                            "description": "Number of top positions to consider (default: top_10)",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["target", "date_from"],
                },
            ),
        ]

        # Backlinks profile tools
        backlinks_tools = [
            Tool(
                name="backlinks",
                description="Get backlinks for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis: 'domain', 'subdomains', 'prefix', or 'exact'",
                            "enum": ["domain", "subdomains", "prefix", "exact"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10, max: 1000)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "aggregation": {
                            "type": "string",
                            "enum": ["similar_links", "1_per_domain", "all"],
                            "description": "The backlinks grouping mode (default: similar_links)",
                        },
                        "history": {
                            "type": "string",
                            "enum": ["live", "all_time", "since:<date>"],
                            "description": "Time frame to add lost backlinks to the report (default: all_time)",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="broken_backlinks",
                description="Get broken backlinks for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis: 'domain', 'subdomains', 'prefix', or 'exact'",
                            "enum": ["domain", "subdomains", "prefix", "exact"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10, max: 1000)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "aggregation": {
                            "type": "string",
                            "enum": ["similar_links", "1_per_domain", "all"],
                            "description": "The backlinks grouping mode (default: similar_links)",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="refdomains",
                description="Get referring domains for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis: 'domain', 'subdomains', 'prefix', or 'exact'",
                            "enum": ["domain", "subdomains", "prefix", "exact"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10, max: 1000)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "history": {
                            "type": "string",
                            "enum": ["live", "all_time", "since:<date>"],
                            "description": "Time frame to add lost backlinks to the report (default: all_time)",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
            Tool(
                name="anchors",
                description="Get anchor text for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis: 'domain', 'subdomains', 'prefix', or 'exact'",
                            "enum": ["domain", "subdomains", "prefix", "exact"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10, max: 1000)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "history": {
                            "type": "string",
                            "enum": ["live", "all_time", "since:<date>"],
                            "description": "Time frame to add lost backlinks to the report (default: all_time)",
                        },
                    },
                    "required": ["target", "date"],
                },
            ),
        ]

        # Organic search tools
        organic_tools = [
            Tool(
                name="organic_keywords",
                description="Get organic keywords for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "date_compared": {
                            "type": "string",
                            "description": "Date to compare metrics with in YYYY-MM-DD format",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "country", "date", "select"],
                },
            ),
            Tool(
                name="organic_competitors",
                description="Get organic competitors for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "date_compared": {
                            "type": "string",
                            "description": "Date to compare metrics with in YYYY-MM-DD format",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "country", "date", "select"],
                },
            ),
            Tool(
                name="top_pages",
                description="Get top organic pages for a domain",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain to analyze",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "date_compared": {
                            "type": "string",
                            "description": "Date to compare metrics with in YYYY-MM-DD format",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "date", "select"],
                },
            ),
        ]

        # Paid search tools
        paid_tools = [
            Tool(
                name="paid_pages",
                description="Get paid pages for a domain or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for analysis in YYYY-MM-DD format",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for the search",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "date_compared": {
                            "type": "string",
                            "description": "Date to compare metrics with in YYYY-MM-DD format",
                        },
                        "volume_mode": {
                            "type": "string",
                            "enum": ["monthly", "average"],
                            "description": "Search volume calculation mode",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "date", "select"],
                },
            ),
        ]

        # Pages tools
        pages_tools = [
            Tool(
                name="best_by_external_links",
                description="Get pages with the most external links",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "history": {
                            "type": "string",
                            "enum": ["live", "all_time", "since:<date>"],
                            "description": "Time frame to add lost backlinks to the report (default: all_time)",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "select"],
                },
            ),
            Tool(
                name="best_by_internal_links",
                description="Get pages with the most internal links",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "select"],
                },
            ),
        ]

        # Outgoing links tools
        outgoing_tools = [
            Tool(
                name="linked_domains",
                description="Get domains that are linked from the target",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "select"],
                },
            ),
            Tool(
                name="outgoing_external_anchors",
                description="Get external anchor texts used in outgoing links",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "select"],
                },
            ),
            Tool(
                name="outgoing_internal_anchors",
                description="Get internal anchor texts used in outgoing links",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Mode of analysis",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                        },
                        "protocol": {
                            "type": "string",
                            "enum": ["both", "http", "https"],
                            "description": "Protocol to analyze (default: both)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 1000)",
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter expression to apply",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                    },
                    "required": ["target", "select"],
                },
            ),
        ]

        # Keywords Explorer tools
        keywords_tools = [
            Tool(
                name="keywords_overview",
                description="Get metrics for keywords from Keywords Explorer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "string",
                            "description": "Comma-separated list of keywords to show metrics for",
                        },
                        "keyword_list_id": {
                            "type": "integer",
                            "description": "The ID of an existing keyword list to show metrics for",
                        },
                        "country": {
                            "type": "string",
                            "description": "Two-letter country code (ISO 3166-1 alpha-2)",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "target": {
                            "type": "string",
                            "description": "Target domain or URL to analyze",
                        },
                        "target_mode": {
                            "type": "string",
                            "enum": ["exact", "prefix", "domain", "subdomains"],
                            "description": "The scope of the target URL you specified",
                        },
                        "target_position": {
                            "type": "string",
                            "enum": ["in_top10", "in_top100"],
                            "description": "Filters keywords based on the ranking position of the specified target",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return (default: 1000)",
                        },
                        "where": {"type": "string", "description": "Filter expression"},
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["country", "select"],
                },
            ),
            Tool(
                name="volume_history",
                description="Get search volume history for a keyword",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "The keyword to show metrics for",
                        },
                        "country": {
                            "type": "string",
                            "description": "Two-letter country code (ISO 3166-1 alpha-2)",
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["keyword", "country"],
                },
            ),
            Tool(
                name="volume_by_country",
                description="Get search volume by country for a keyword",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "The keyword to show metrics for",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["keyword"],
                },
            ),
            Tool(
                name="matching_terms",
                description="Get matching terms for keywords",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "string",
                            "description": "Comma-separated list of keywords to show metrics for",
                        },
                        "keyword_list_id": {
                            "type": "integer",
                            "description": "The ID of an existing keyword list to show metrics for",
                        },
                        "country": {
                            "type": "string",
                            "description": "Two-letter country code (ISO 3166-1 alpha-2)",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "match_mode": {
                            "type": "string",
                            "enum": ["terms", "phrase"],
                            "description": "Keyword ideas contain words in any order (terms) or exact order (phrase)",
                        },
                        "terms": {
                            "type": "string",
                            "enum": ["all", "questions"],
                            "description": "All keywords ideas or keywords ideas phrased as questions",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return (default: 1000)",
                        },
                        "where": {"type": "string", "description": "Filter expression"},
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["country", "select"],
                },
            ),
            Tool(
                name="related_terms",
                description="Get related terms for keywords",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "string",
                            "description": "Comma-separated list of keywords to show metrics for",
                        },
                        "keyword_list_id": {
                            "type": "integer",
                            "description": "The ID of an existing keyword list to show metrics for",
                        },
                        "country": {
                            "type": "string",
                            "description": "Two-letter country code (ISO 3166-1 alpha-2)",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "view_for": {
                            "type": "string",
                            "enum": ["top_10", "top_100"],
                            "description": "View keywords for top 10 or top 100 ranking pages",
                        },
                        "terms": {
                            "type": "string",
                            "enum": ["also_rank_for", "also_talk_about", "all"],
                            "description": "Related keywords type",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return (default: 1000)",
                        },
                        "where": {"type": "string", "description": "Filter expression"},
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["country", "select"],
                },
            ),
            Tool(
                name="search_suggestions",
                description="Get search suggestions for keywords",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "string",
                            "description": "Comma-separated list of keywords to show metrics for",
                        },
                        "keyword_list_id": {
                            "type": "integer",
                            "description": "The ID of an existing keyword list to show metrics for",
                        },
                        "country": {
                            "type": "string",
                            "description": "Two-letter country code (ISO 3166-1 alpha-2)",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of columns to return",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return (default: 1000)",
                        },
                        "where": {"type": "string", "description": "Filter expression"},
                        "order_by": {
                            "type": "string",
                            "description": "Column to order results by",
                        },
                        "output": {
                            "type": "string",
                            "enum": ["json", "csv", "xml", "php"],
                            "description": "Output format",
                        },
                    },
                    "required": ["country", "select"],
                },
            ),
        ]

        # Combine all tools
        all_tools = (
            overview_tools
            + backlinks_tools
            + organic_tools
            + paid_tools
            + pages_tools
            + outgoing_tools
            + keywords_tools
        )

        return all_tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Ahrefs"""
        logger.info(f"Tool: {name}, User: {server.user_id}")

        api_key = await get_ahrefs_credentials(server.user_id, server.api_key)
        arguments = arguments or {}

        # Initialize endpoints mapping
        endpoints = {
            # Overview endpoints
            "domain_rating": "site-explorer/domain-rating",
            "backlinks_stats": "site-explorer/backlinks-stats",
            "outlinks_stats": "site-explorer/outlinks-stats",
            "metrics": "site-explorer/metrics",
            "refdomains_history": "site-explorer/refdomains-history",
            "domain_rating_history": "site-explorer/domain-rating-history",
            "url_rating_history": "site-explorer/url-rating-history",
            "pages_history": "site-explorer/pages-history",
            "metrics_history": "site-explorer/metrics-history",
            "keywords_history": "site-explorer/keywords-history",
            "metrics_by_country": "site-explorer/metrics-by-country",
            "pages_by_traffic": "site-explorer/pages-by-traffic",
            "total_search_volume_history": "site-explorer/total-search-volume-history",
            # Backlinks profile endpoints
            "backlinks": "site-explorer/all-backlinks",
            "broken_backlinks": "site-explorer/broken-backlinks",
            "refdomains": "site-explorer/refdomains",
            "anchors": "site-explorer/anchors",
            # Organic search endpoints
            "organic_keywords": "site-explorer/organic-keywords",
            "organic_competitors": "site-explorer/organic-competitors",
            "top_pages": "site-explorer/top-pages",
            # Paid search endpoints
            "paid_pages": "site-explorer/paid-pages",
            # Pages endpoints
            "best_by_external_links": "site-explorer/best-by-external-links",
            "best_by_internal_links": "site-explorer/best-by-internal-links",
            # Outgoing links endpoints
            "linked_domains": "site-explorer/linkeddomains",
            "outgoing_external_anchors": "site-explorer/linked-anchors-external",
            "outgoing_internal_anchors": "site-explorer/linked-anchors-internal",
            # Keywords Explorer endpoints
            "keywords_overview": "keywords-explorer/overview",
            "volume_history": "keywords-explorer/volume-history",
            "volume_by_country": "keywords-explorer/volume-by-country",
            "matching_terms": "keywords-explorer/matching-terms",
            "related_terms": "keywords-explorer/related-terms",
            "search_suggestions": "keywords-explorer/search-suggestions",
        }

        if name not in endpoints:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        # Start parameter handling
        params = {"output": "json"}

        # For almost all endpoint types, we can simply pass all arguments directly
        params.update(arguments)

        # Handle the select parameter for some endpoint types if not provided
        if "select" not in params:
            if name in SITE_EXPLORER_DEFAULT_SELECT:
                params["select"] = SITE_EXPLORER_DEFAULT_SELECT[name]
            elif name in KEYWORDS_EXPLORER_DEFAULT_SELECT:
                params["select"] = KEYWORDS_EXPLORER_DEFAULT_SELECT[name]
            elif name == "linked_domains":
                params["select"] = "domain,domain_rating,links_from_target,linked_pages"
            elif name in ["outgoing_external_anchors", "outgoing_internal_anchors"]:
                params["select"] = "anchor,links_from_target,linked_pages"

        # Make the API request
        try:
            encoded_params = {k: str(v) for k, v in params.items()}
            response = await make_ahrefs_request(
                endpoints[name], encoded_params, api_key
            )

            if response.get("_status_code", 0) != 200:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {response.get('error', 'Unknown error')}",
                    )
                ]

            # Default response for all other endpoints
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing {name}: {error_msg}")
            return [TextContent(type="text", text=f"Error: {error_msg}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="ahrefs-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_ahrefs_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
