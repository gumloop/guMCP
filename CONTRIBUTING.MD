# Contributing to guMCP

Thank you for your interest in contributing to guMCP! This document provides guidelines and instructions to help you get started with development.

## Project Overview

- `src/`: Contains the main source code
  - `auth/`: Authentication components
  - `servers/`: Server implementations
- `tests/`: Test suite for the project
- `scripts/`: Utility scripts

## Development Environment Setup

### Prerequisites

- Python 3.11
- Git

### Setting Up Your Development Environment

1. **Clone the repository**

```bash
git clone https://github.com/gumloop/guMCP.git
cd guMCP
```

2. **Create a virtual environment**

```bash
python -m venv venv
```

3. **Activate the virtual environment**

On macOS/Linux:

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

4. **Install dependencies**

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

5. **Set up environment variables**

Copy the example .env file and update it with your configuration:

```bash
cp .env.example .env  # If an example exists, otherwise create your own
```

## Development Workflow

### Code Style and Standards

This project follows these coding standards:

- PEP 8 for Python code style
- Type hints for all functions and methods
- Documentation using docstrings

We use several tools to enforce these standards:

- Black for code formatting
- Flake8 for linting
- MyPy for type checking

### Running Code Quality Tools

You can run the code quality tools with the following command from the root directory:

```bash
# Format code with Black
python scripts/format_code.py
```

## Authentication

### OAuth 2.0

For local development and usage with OAuth-based integrations, we use the `LocalAuthClient` to manage credentials:

1. **Create OAuth Configuration**

   Create a JSON configuration file for your service in `local_auth/oauth_configs/<service_name>/oauth.json`:

   ```json
   {
     "client_id": "your_client_id",
     "client_secret": "your_client_secret",
     "redirect_uri": "http://localhost:8080" // This is the default recommended redirect_uri as it is the default used in `src/utils/oauth/util.py`, which should be used for retrieving the authorization code
   }
   ```

2. **Authenticate Users**

   Use the authentication flow in your server's main module:

   ```python
   # Run authentication flow
   authenticate_and_save_credentials("local", "service_name", ["scope1", "scope2"])
   ```

   The recommmendation here is to create a util function (in `src/utils/{service_name}/util.py`) to `get_credentials` which wraps `run_oauth_flow()` from [OAuth Utils](src/utils/oauth/util.py)

3. **Access Credentials**

   The `LocalAuthClient` stores credentials in `local_auth/credentials/<service_name>/<user_id>_credentials.json`.

   You can retrieve them in your code:

   ```python
   from src.auth.factory import create_auth_client

   auth_client = create_auth_client()
   credentials = auth_client.get_user_credentials("service_name", "user_id")
   ```

   The recommendation here is to create a util function (in `src/utils/{service_name}/util.py`) to `get_credentials` which wraps `refresh_token_if_needed()` to automatically handles the refresh from [OAuth Utils](src/utils/oauth/util.py)

4. **Example Implementations**

   For reference, check out these example implementations:

   - [Slack](src/utils/slack/util.py) - Uses OAuth 2.0 without refresh tokens
   - [Attio](src/utils/attio/util.py) - Uses OAuth 2.0 with refresh token support, stores some additional params from token response as well
   - [Airtable](src/utils/airtable/util.py) - Uses OAuth 2.0 with refresh token support, uses challenge code as well

   These examples demonstrate how to properly implement the authentication flow, token handling, and credential management for different OAuth 2.0 patterns.

   **HIGHLY RECOMMENDED**: Review these examples before implementing your own OAuth integration, as they provide clear patterns for both simple OAuth flows (Slack) and more complex flows with refresh tokens (Airtable).

### Non-OAuth

For non-oauth flows like those requiring API keys or similar, the approach can be much more straight forward, working with the `auth_client` directly.

See [Perplexity](src/servers/perplexity/main.py) for a clear example

### Remote Auth Clients

If implementing your own AuthClient to host and run guMCP servers remotely, please note that the assumption made in [BaseAuthClient](src/auth/clients/BaseAuthClient.py) is that `get_user_credentials()` returns a _refreshed and ready-to-use_ version of the credential. That is, refreshing should be taken care of on the side of the `AuthClient`.

## Implementation

### Tools

When implementing tools for a server, please follow these guidelines:

1. **Focus on Utility**: Implement tools that are actually useful and widely used by the service's users. Avoid niche functionality that few people would need.

2. **Completeness**: Ensure your tools cover the core functionality of the service. For example, if implementing a messaging service, include tools for sending messages, reading messages, listing messaging channels, etc.

3. **Arguments**: The arguments for the tool should be generally understandable to humans if possible. For example, with an `add_member` tool, having it require a `member_email` instead of `member_id` is preferred

4. **Documentation**: Each tool should have clear documentation in its docstring explaining what it does, required parameters, and expected output.

5. **Error Handling**: Implement proper error handling with informative error messages to help users understand what went wrong.

6. **Test Framework Compliance**: We strongly recommend implementing your tools following our [guMCP Test](../tests/README.md). This helps with testing and generating accurate outputSchema.

7. **Output Schema**: Every tool definition must include an outputSchema to help Gummie understand the response format:

   ```python
   outputSchema={
      "type": "array",
      "items": {"type": "string"},
      "description": "Array of JSON strings containing the operation results",
      "examples": [
         '[{"status":"success","document_id":"doc123","name":"Example Document"}]'
      ],
   }
   ```

   You can manually create `outputSchema` following our guidelines, but we recommend using:
   
   - The `scripts/tool_test_executor.py` script which runs tools and saves their outputs to `./scripts/logs/<server_name>.json`
   - If using tool_test_executor.py, ensure your server follows the testing framework structure in [guMCP Test](../tests/README.md) for optimal results
   - Example command: `python scripts/tool_test_executor.py <server_name>`

   After generating tool outputs, provide both the generated output file (from `./scripts/logs/<server_name>.json`) and your tool definition file to Cursor, ChatGPT or other LLMs along with this prompt to create high-quality outputSchema:

   ```
   When updating outputSchema example, please follow these guidelines:
   1. Be reasonable and detailed in your descriptions. Clearly explain any changes or logic so the modifications are easy to understand and trace.
   2. Use obfuscation thoughtfully. Avoid confusing large language models. For example, instead of modifying actual URLs or IDs, use placeholders like <URL> or <ID> to maintain clarity while abstracting sensitive or irrelevant data.
   3. Avoid excessive output. You don't need to include full data sets—just enough to preserve the structure. For instance, if the data is an array with 100 items, include only 2–3 representative examples.
   4. Make sure the output schema example is similar to actual output responses by tool and description should be relevant enough to the example.
   ```

### Resources

Resources in guMCP follow a consistent URI format:

```
{server_id}://{resource_type}/{resource_id}
```

When implementing resources, follow these guidelines:

1. **URI Structure**: Use the format `{server_id}://{resource_type}/{resource_id}` for all resource URIs.

   - `server_id`: The unique identifier for your server (e.g., `slack`, `gdrive`)
   - `resource_type`: The type of resource (e.g., `channel`, `file`, `folder`)
   - `resource_id`: The unique identifier for the specific resource instance
   - Example: `slack://channel/C05AD7ZD41L`

2. **Name Format**: Use clear, user-friendly names that reflect the resource in the source system.

   - For example, a Slack channel's `uri` would include the `channel_id`, but the name would just be the human readable channel name

3. **Complete Implementation**: Implement both `list_resources()` and `read_resource()` handlers for your server.

4. **Resource Description**: Include helpful descriptions that convey the nature and purpose of the resource.

## Testing

### Running Tests

Tests can be run from the root directory using:

```bash
# Run specific tests locally (stdio)
python tests/servers/test_runner.py --server=simple-tools-server
# Run specific tests locally (sse) -- you would need to have the sse server running, ex. by running ./start_sse_dev_server.sh from the root directory
python tests/servers/test_runner.py --server=simple-tools-server --remote
# Run tests on a specific hosted guMCP server (ex. Gumloop's MCP Server)
python tests/servers/test_runner.py --server=simple-tools-server --remote --endpoint=https://mcp.gumloop.com/gdrive/{user_id}%3A{api_key}
```

### Manually Using Testing Clients

For Sandbox environments, we also provide `tests/clients/LocalMCPTestClient.py` and `tests/clients/RemoteMCPTestClient.py`.

These are based on Anthropic's example clients that connect to the MCP server and run a chat loop with stdio and SSE respectively.

Note: You must have an `ANTHROPIC_API_KEY` in your `.env` file for this to work correctly

### Writing Tests

When adding new features, please ensure you:

1. Write tests following our [guMCP Test](../tests/README.md) framework
2. Implement both RESOURCE_TESTS and TOOL_TESTS for complete coverage
3. Ensure all tests pass before submitting a PR
4. Use the shared context to pass values between tests
5. Use descriptive test names that follow the pattern `test_<functionality>_<expected_behavior>`
6. Every tool must have a corresponding test in the TOOL_TESTS array

All servers should have a corresponding `tests.py` file testing all tools, resources, prompts, etc. This not only ensures functionality but also helps generate accurate outputSchema examples through the auto_generator.py script.

Please have some tests that do NOT use mocks and expect the user to already be authenticated locally. This helps us ensure that functionality is actually correct and working end-to-end.

## Pull Request Process

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** and ensure they follow the project's code style
3. **Add tests** for any new functionality
4. **Ensure all tests pass** by running the test suite
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description of the changes and why they're needed

## Request for PRs

- Add Support for New MCP Spec
  - [Streamable HTTP Transport](https://github.com/gumloop/guMCP/issues/26)
  - Client/Server Authentication Mechanism
- [Add Support for FastMCP](https://github.com/gumloop/guMCP/issues/24)

## Versioning

We follow [Semantic Versioning](https://semver.org/) for this project.

## License

By contributing to this project, you agree that your contributions will be licensed under the project's license.

## Communication

If you have questions or need help, you can:

- Open an issue in the GitHub repository
- Contact the project maintainers via email or other communication channels

Thank you for contributing to guMCP!
