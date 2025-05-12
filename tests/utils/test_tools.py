import pytest
import re


def get_test_id(test_config):
    """Generate a unique test ID based on the test name and description hash"""
    return f"{test_config['name']}_{hash(test_config['description']) % 1000}"


@pytest.mark.asyncio
async def run_tool_test(client, context: dict, test_config: dict) -> dict:
    """
    Common test function for running tool tests across different servers.

    Args:
        client: The client fixture
        context: Module-scoped context dictionary to store test values
        test_config: Configuration for the specific test to run

    Returns:
        Updated context dictionary with test results
    """
    if test_config.get("skip", False):
        pytest.skip(f"Test {test_config['name']} marked to skip")
        return

    missing_deps = []
    for dep in test_config.get("depends_on", []):
        if dep not in context:
            missing_deps.append(dep)
        elif context[dep] in ["empty_list", "not_found", "empty"]:
            missing_deps.append(f"{dep} (has placeholder value)")

    if missing_deps:
        pytest.skip(f"Missing dependencies: {', '.join(missing_deps)}")
        return

    if "setup" in test_config and callable(test_config["setup"]):
        setup_result = test_config["setup"](context)
        if isinstance(setup_result, dict):
            context.update(setup_result)

    tool_name = test_config["name"]
    expected_keywords = test_config["expected_keywords"]
    description = test_config["description"]

    if "args" in test_config:
        args = test_config["args"]
    elif "args_template" in test_config:
        try:
            args = test_config["args_template"].format(**context)
        except KeyError as e:
            pytest.skip(f"Missing context value: {e}")
            return
        except Exception as e:
            pytest.skip(f"Error formatting args: {e}")
            return
    else:
        args = ""

    keywords_str = ", ".join(expected_keywords)
    prompt = (
        "Not interested in your recommendations or what you think is best practice, just use what's given. "
        "Only pass required arguments to the tool and in case I haven't provided a required argument, you can try to pass your own that makes sense. "
        f"Only return the value with following keywords: {keywords_str} if successful or error with keyword 'error_message'. ensure to keey the keywords name exact same "
        f"Use the {tool_name} tool to {description} {args}. "
        "Sample response: keyword: output_data keyword2: output_data2 keyword3: [] always ensure keyword is in same format as in expected_keywords"
    )

    response = await client.process_query(prompt)

    if (
        "empty" in response.lower()
        or "[]" in response
        or "no items" in response.lower()
        or "not found" in response.lower()
    ):
        if "regex_extractors" in test_config:
            for key, pattern in test_config["regex_extractors"].items():
                if key not in context:
                    context[key] = "empty_list"

        pytest.skip(f"Empty result from API for {tool_name}")
        return

    if "error_message" in response.lower() and "error_message" not in expected_keywords:
        pytest.fail(f"API error for {tool_name}: {response}")
        return

    missing_keywords = []
    for keyword in expected_keywords:
        if keyword != "error_message" and keyword.lower() not in response.lower():
            missing_keywords.append(keyword)

    if missing_keywords:
        pytest.skip(f"Keywords not found: {', '.join(missing_keywords)}")
        return

    if "regex_extractors" in test_config:
        for key, pattern in test_config["regex_extractors"].items():
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match and len(match.groups()) > 0:
                context[key] = match.group(1).strip()
            else:
                pytest.fail(
                    f"Failed to extract '{key}' using pattern '{pattern}' from response: {response}"
                )

    return context


@pytest.mark.asyncio
async def run_resources_test(client):
    """
    Generic test function for list_resources and read_resource handlers.
    """
    # List resources
    response = await client.list_resources()
    assert (
        response
        and hasattr(response, "resources")
        and isinstance(response.resources, list)
    ), f"Invalid list_resources response: {response}"
    if not response.resources:
        pytest.skip("No resources found")

    # Test only the first resource
    resource = response.resources[0]
    assert (
        isinstance(resource.name, str) and resource.name
    ), f"Invalid resource name for URI {resource.uri}"

    contents = await client.read_resource(resource.uri)
    assert hasattr(contents, "contents") and isinstance(
        contents.contents, list
    ), f"Invalid read_resource response for {resource.uri}"
    assert contents.contents, f"No content returned for {resource.uri}"

    return response
