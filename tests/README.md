# guMCP Testing Framework

This directory contains the testing framework for guMCP servers and tools.

## Test Structure

Each server should have a test file (`tests.py`) in its directory that implements both tool tests and resource tests. You can reference this file using [@tests/servers/word/tests.py](../tests/servers/word/tests.py) as an example.

### Test Components

- **RESOURCE_TESTS**: Tests for resource operations (e.g., list_resources, read_resource)
- **TOOL_TESTS**: Tests for server tools (e.g., create_document, read_document)
- **Shared Context**: A dictionary that persists between tests to maintain state

## Test Configuration Format

Both TOOL_TESTS and RESOURCE_TESTS use the same configuration format:

```python
{
    "name": "tool_or_resource_operation_name",
    "args_template": "with param1={value1} param2={value2}",  # Optional
    "args": "with static_param=value",  # Optional alternative to args_template
    "expected_keywords": ["keyword1", "keyword2"],  # Must appear in response
    "regex_extractors": {  # Optional, extracts values from response
        "value_name": r'"?field_name"?[:\s]+"?([^"]+)"?',
    },
    "description": "Describes what this test does",
    "depends_on": ["value_name"],  # Optional, dependencies from context
    "setup": lambda context: {"key": "value"},  # Optional setup function
    "skip": False  # Optional, skip this test if True
}
```

## Context and Dependencies

- Tests can depend on values from previous tests via the `depends_on` list
- Values are extracted using regex patterns in `regex_extractors`
- The shared context dictionary persists between tests

## Example

```python
RESOURCE_TESTS = [
    {
        "name": "list_resources",
        "expected_keywords": ["resources"],
        "regex_extractors": {
            "resource_uri": r'"?uri"?[:\s]+"?(server://type/[^"]+)"?',
        },
        "description": "list resources and extract a URI",
    },
    {
        "name": "read_resource",
        "args_template": 'with uri="{resource_uri}"',
        "expected_keywords": ["contents"],
        "description": "read a resource's details",
        "depends_on": ["resource_uri"],
    },
]

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
```

## Running Tests

Use the test runner to execute tests:

```bash
# Run tests for a specific server
python tests/servers/test_runner.py --server=server-name
```

See [CONTRIBUTING.md](../CONTRIBUTING.MD) for more details on running tests.