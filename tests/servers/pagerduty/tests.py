import pytest
import re
import json

# Define test configurations for each tool
TOOL_TESTS = [
    {
        "name": "create_service",
        "args": "with name='Service Test API', description='Service created via API for testing', email_from='jyoti@gumloop.com', escalation_policy_id='PABC123'",
        "expected_keyword": "service_id",
        "regex_pattern": r"service_id:\s*([A-Z0-9]+)",
        "description": "create a new service in PagerDuty",
        "extract_value": True  
    },
    {
        "name": "list_services", 
        "args": "with email_from='jyoti@gumloop.com', limit=5",
        "expected_keyword": "services",
        "regex_pattern": r"services",
        "description": "list existing services from PagerDuty"
    },
    {
        "name": "create_incident",
        "args": "with title='The server is on fire.', service_id='{create_service}', email_from='jyoti@gumloop.com', priority_id='P53ZZH5', urgency='high', incident_key='baf7cf21b1da41b4b0221008339ff357', details='A disk is getting full on this machine.', escalation_policy_id='PT20YPA'",
        "expected_keyword": "incident_id",
        "regex_pattern": r"incident_id:\s*([A-Z0-9]+)",
        "description": "create a new incident in PagerDuty",
        "extract_value": True  # Extract the value using regex capture group
    },
    {
        "name": "list_incidents",
        "args": "with email_from='jyoti@gumloop.com', limit=10, statuses=['triggered', 'acknowledged'], include=['services', 'first_trigger_log_entries']",
        "expected_keyword": "incidents",
        "regex_pattern": r"incidents",
        "description": "list existing incidents from PagerDuty",
    },
]

# Storage for test outputs that need to be shared between tests
test_outputs = {}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_config", TOOL_TESTS)
async def test_pagerduty_tool(client, tool_config):
    """Generic test function for PagerDuty tools"""
    tool_name = tool_config["name"]
    args = tool_config["args"]
    expected_keyword = tool_config["expected_keyword"]
    regex_pattern = tool_config.get("regex_pattern")
    description = tool_config["description"]
    select_param = tool_config.get("select_param", "")
    extract_value = tool_config.get("extract_value", False)
    
    # Process args string using Python string formatting
    args = args.format(**test_outputs) if test_outputs else args
    
    # Create prompt for the client
    prompt = (
        "Not interested in your recommendations or what you think is best practice, just use what's given. "
        "Only pass required arguments to the tool and in case I haven't provided a required argument, you can try to pass your own that makes sense. "
        f"Use the {tool_name} tool to {description} {args}. "
        f"If select parameter is provided: '{select_param}', use it. "
        f"Only return the {expected_keyword} with keyword '{expected_keyword}' if successful or error with keyword 'error_message'. "
        "Sample response: keyword: output_data"
    )

    print(f"Running {tool_name} with args: {args}")

    response = await client.process_query(prompt)
    
    if "error_message" in response:
        pytest.fail(f"{tool_name} : Failed to {description}: {response}")

    assert (
        expected_keyword in response
    ), f"{tool_name} : Expected {expected_keyword} in response: {response}"

    if regex_pattern:
        match = re.search(regex_pattern, response)
        assert match, f"{tool_name} : Expected {regex_pattern} pattern in response: {response}"
        
        # Extract value from regex if needed
        if extract_value and match.groups():
            # Store the captured value in test_outputs
            extracted_value = match.group(1)
            test_outputs[tool_name] = extracted_value
            print(f"Extracted value for {tool_name}: {extracted_value}")

    print(f"✅ {tool_name.replace('_', ' ').title()} test completed")
