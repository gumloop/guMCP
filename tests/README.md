# guMCP Testing Framework

This directory contains the testing framework for guMCP servers and tools.

## Test Structure

Each server should have a test file (`tests.py`) in its directory that implements both tool tests and resource tests. You can reference this file using [@tests/servers/word/tests.py](../tests/servers/word/tests.py) as an example.

### Test Components

- **Resources Test**: Tests for resource operations using `run_resources_test`
- **Tool Tests**: Tests for server tools using `run_tool_test`
- **Shared Context**: A dictionary that persists between tests to maintain state

## Testing Resources

Resources can be tested using the simplified `run_resources_test` helper:

```python
from tests.utils.test_tools import run_resources_test

@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response
```

This helper:
- Checks for a valid list_resources response
- Skips if no resources are found
- Validates the first resource and its read_resource response
- Stores the first resource URI in context for use in tool tests

## Tool Test Configuration Format

Tool tests use the following configuration format:

```python
{
    "name": "tool_name",
    "args_template": "with param1={value1} param2={value2}",  # Optional
    "args": "with static_param=value",  # Optional alternative to args_template
    "expected_keywords": ["keyword1", "keyword2"],  # Must appear in response
    "regex_extractors": {  # Optional, extracts values from response
        "value_name": r'"?field_name"?[:\s]+"?([^"]+)"?',
    },
    "description": "Describes what this tool does",
    "depends_on": ["value_name"],  # Optional, dependencies from context
    "setup": lambda context: {"key": "value"},  # Optional setup function
    "skip": False  # Optional, skip this test if True
}
```

## Context and Dependencies

- Tests can depend on values from previous tests via the `depends_on` list
- Values are extracted using regex patterns in `regex_extractors`
- The shared context dictionary persists between tests
- The first resource URI is available as `first_resource_uri` in context

## Example

```python
# Import required components
import pytest
import random
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test

# Define tool tests
TOOL_TESTS = [
    {
        "name": "create_document",
        "args_template": 'with name="Test-{random_id}"',
        "expected_keywords": ["created_file_id"],
        "regex_extractors": {
            "created_file_id": r'"?created_file_id"?[:\s]+"?([0-9A-Z!]+)"?',
        },
        "description": "create a document and return its ID",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "read_document",
        "args_template": 'with file_id="{created_file_id}"',
        "expected_keywords": ["content"],
        "description": "read document content",
        "depends_on": ["created_file_id"],
    },
]

# Shared context dictionary
SHARED_CONTEXT = {}

@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT

# Test resources
@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response

# Test tools
@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)
```

## Running Tests

Use the test runner to execute tests:

```bash
# Run tests for a specific server
python tests/servers/test_runner.py --server=server-name
```

See [CONTRIBUTING.md](../CONTRIBUTING.MD) for more details on running tests.