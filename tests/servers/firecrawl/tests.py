import pytest
import json
import os
import re
import ast


@pytest.mark.asyncio
async def test_scrape_url(client):
    """Test scraping a single URL with Firecrawl"""
    response = await client.process_query(
        "I need to scrape a website. Please use the scrape_url tool to get the content from https://gumloop.com with formats=['markdown'] and onlyMainContent=true."
        "and only return the markdown with keyword 'markdown_data' if successful or error with keyword 'error_message'"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to scrape URL: {response}")

    assert (
        "markdown_data" in response
    ), f"Expected markdown_data in response: {response}"
    assert "gumloop" in response, f"Expected gumloop in response: {response}"

    print("✅ Scrape URL flow completed")


@pytest.mark.asyncio
async def test_batch_flow(client):
    """Test batch flow with Firecrawl"""
    urls = ["https://gumloop.com", "https://gumloop.com/about"]

    # Start batch scrape
    response = await client.process_query(
        f"Call the batch_scrape tool with the following urls: {json.dumps(urls)}"
        f"and only return the batch id with keyword 'batch_id' if successful or error with keyword 'error_message'"
    )

    # Check for errors in batch creation
    if "error_message" in response:
        pytest.fail(f"Failed to create batch: {response}")

    assert "batch_id" in response, f"Expected batch_id in response: {response}"
    batch_id = response.split("batch_id: ")[1].split("\n")[0].strip()

    # Get batch status
    get_batch_status_response = await client.process_query(
        f"Call the get_batch_status tool with the following batch id: {batch_id}"
        f"and only return the status with keyword 'batch_status' if successful or error with keyword 'error_message'"
    )
    print("Batch Status: ", get_batch_status_response)

    # Check for errors in status retrieval
    if "error_message" in get_batch_status_response:
        pytest.fail(f"Failed to get batch status: {get_batch_status_response}")

    assert (
        "batch_status" in get_batch_status_response
    ), f"Expected batch_status in response: {get_batch_status_response}"
    status = get_batch_status_response.split("batch_status: ")[1].split("\n")[0].strip()

    # Handle failed batch
    if status == "failed":
        get_error_response = await client.process_query(
            f"Call the get_batch_error tool with the following batch id: {batch_id}"
            f"and only return the errors with keyword 'errors' if successful or error with keyword 'error_message'"
        )
        print("Failed to scrape: ", get_error_response)
        pytest.skip("Failed to scrape the batch")

    print("✅ Batch flow completed")


@pytest.mark.asyncio
async def test_crawl_flow(client):
    """Test crawl flow with Firecrawl"""
    response = await client.process_query(
        "Use crawl_website tool to crawl the website https://gumloop.com"
        "and only return the crawl id with keyword 'crawl_id' if successful or error with keyword 'error_message'"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to create crawl: {response}")

    assert "crawl_id" in response, f"Expected crawl_id in response: {response}"

    crawl_id = response.split("crawl_id: ")[1].split("\n")[0].strip()
    print("Crawl ID: ", crawl_id)

    get_crawl_status_response = await client.process_query(
        f"Call the get_crawl_status tool with the following crawl id: {crawl_id}"
        f"and only return the status with keyword 'crawl_status' if successful or error with keyword 'error_message'"
    )

    if "error_message" in get_crawl_status_response:
        pytest.fail(f"Failed to get crawl status: {get_crawl_status_response}")

    assert (
        "crawl_status" in get_crawl_status_response
    ), f"Expected crawl_status in response: {get_crawl_status_response}"

    crawl_status = (
        get_crawl_status_response.split("crawl_status: ")[1].split("\n")[0].strip()
    )

    if crawl_status == "failed":
        get_crawl_error_response = await client.process_query(
            f"Call the get_crawl_error tool with the following crawl id: {crawl_id}"
        )
        print("Failed to crawl: ", get_crawl_error_response)
        pytest.skip("Failed to crawl the website")

    print("✅ Crawl flow completed")


@pytest.mark.asyncio
async def test_crawl_cancel_flow(client):
    """Test crawl cancel with Firecrawl"""
    response = await client.process_query(
        "Use crawl_website tool to crawl the website https://gumloop.com"
        "and only return the crawl id with keyword 'crawl_id' if successful or error with keyword 'error_message'"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to create crawl: {response}")

    assert "crawl_id" in response, f"Expected crawl_id in response: {response}"

    crawl_id = response.split("crawl_id: ")[1].split("\n")[0].strip()
    print("Crawl ID: ", crawl_id)

    cancel_crawl_response = await client.process_query(
        f"Call the cancel_crawl tool with the following crawl id: {crawl_id}"
        "and only return the status with keyword 'crawl_status' if successful or error with keyword 'error_message'"
    )

    if "error_message" in cancel_crawl_response:
        pytest.fail(f"Failed to cancel crawl: {cancel_crawl_response}")

    assert (
        "crawl_status" in cancel_crawl_response
    ), f"Expected crawl_status in response: {cancel_crawl_response}"

    crawl_status = (
        cancel_crawl_response.split("crawl_status: ")[1].split("\n")[0].strip()
    )

    if crawl_status == "cancelled":
        print("✅ Crawl cancelled successfully")
    else:
        pytest.fail(f"Expected crawl to be cancelled, but got {crawl_status}")


@pytest.mark.asyncio
async def test_map_website(client):
    """Test map website with Firecrawl"""
    response = await client.process_query(
        "Use map_website tool to map the website https://gumloop.com"
        "and only return the links in list format with keyword 'mapped_links' if successful or error with keyword 'error_message'"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to map website: {response}")

    assert "mapped_links" in response, f"Expected mapped_links in response: {response}"

    assert "mapped_links" in response, f"Expected mapped_links in response: {response}"

    print("✅ Map website completed")


@pytest.mark.asyncio
async def test_extract_flow(client):
    """Test extract flow with Firecrawl"""
    response = await client.process_query(
        "Use extract_data tool with url as https://gumloop.com , no need to provide any recommendations just pass the url"
        "and only return the id with keyword 'extract_id' if successful or error with keyword 'error_message'"
        "sample extract_id: id"
    )

    print("Extract Response: ", response)

    if "error_message" in response:
        pytest.fail(f"Failed to extract data: {response}")

    assert "extract_id" in response, f"Expected extract_id in response: {response}"

    extract_id = response.split("extract_id: ")[1].split("\n")[0].strip()
    print("Extract ID: ", extract_id)

    get_extract_status_response = await client.process_query(
        f"Call the get_extract_status tool with the following extract id: {extract_id}"
        "and only return the status with keyword 'extract_status' if successful or error with keyword 'error_message'"
    )

    if "error_message" in get_extract_status_response:
        pytest.fail(f"Failed to get extract status: {get_extract_status_response}")

    assert (
        "extract_status" in get_extract_status_response
    ), f"Expected extract_status in response: {get_extract_status_response}"
    if get_extract_status_response.split("extract_status: ")[1].split("\n")[
        0
    ].strip().lower() in ["completed", "processing", "failed", "cancelled"]:
        print("✅ Extract flow completed")
    else:
        pytest.fail(
            f"Expected extract to be completed, processing, failed, or cancelled, but got {get_extract_status_response}"
        )


@pytest.mark.asyncio
async def test_search(client):
    """Test search flow with Firecrawl"""
    response = await client.process_query(
        "Use search tool to search gumloop"
        "and only return the title in array format with keyword 'search_results' if successful or error with keyword 'error_message'"
        "sample search_results: ['tittle 1', 'tittle 2', 'tittle 3']"
    )

    print("Search Response: ", response)
    if "error_message" in response:
        pytest.fail(f"Failed to search: {response}")

    assert (
        "search_results" in response
    ), f"Expected search_results in response: {response}"
    assert "gumloop" in response, f"Expected gumloop in search_results: {response}"

    print("✅ Search flow completed")


@pytest.mark.asyncio
async def test_get_credit_usage(client):
    """Test get credit usage with Firecrawl"""
    response = await client.process_query(
        "Use get_credit_usage tool to get the credit usage"
        "and only return the remaining_credits with keyword 'remaining_credits' if successful or error with keyword 'error_message'"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to get credit usage: {response}")

    assert (
        "remaining_credits" in response
    ), f"Expected remaining_credits in response: {response}"

    print("✅ Get credit usage flow completed")
