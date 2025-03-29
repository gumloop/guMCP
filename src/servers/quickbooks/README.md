# QuickBooks Server for guMCP

This server provides integration with QuickBooks Online for financial data access and analysis.

## Dependencies

This server requires the following dependencies which have been added to the project requirements:
- `python-quickbooks`: The QuickBooks Python SDK
- `intuit-oauth`: For OAuth authentication with Intuit's API

## Authentication

To authenticate with QuickBooks:

```bash
python src/servers/quickbooks/main.py auth
```

This will start the OAuth flow and save your credentials locally. By default, the credentials will be stored at `~/.config/gumcp/quickbooks/local.json`. Each user's credentials are stored in separate files based on their user ID.

## Features

- Access to QuickBooks resources like customers, invoices, accounts, bills, and payments
- Financial analysis tools including cash flow analysis and financial metric generation
- SR&ED expense analysis for Canadian tax credits
- Duplicate transaction detection
- Customer payment pattern analysis

### Prerequisites

- Python 3.11+
- A QuickBooks Online Developer account


### Local Authentication

1. [Create a QuickBooks Online Developer account](https://developer.intuit.com/)
2. [Register a new application](https://developer.intuit.com/app/developer/qbo/docs/get-started)
3. Configure a redirect URI for your application (e.g., http://localhost:8080)
4. Get your application's client ID and client secret
5. Set the following environment variables:

```bash
export QUICKBOOKS_CLIENT_ID="your_client_id_here"
export QUICKBOOKS_CLIENT_SECRET="your_client_secret_here"
export QUICKBOOKS_REDIRECT_URI="http://localhost:8080"  # Optional, defaults to OAuth Playground URL
export QUICKBOOKS_ENVIRONMENT="sandbox"  # Optional, defaults to sandbox
```

6. To set up and verify authentication, run:

```bash
python src/servers/quickbooks/main.py auth
```

7. To test the integration, run:

```bash
python -m tests.servers.test_runner --server=quickbooks
```

### Available Tools

The QuickBooks server provides the following tools:

- `search_customers`: Search for customers by name, email, or phone
- `generate_financial_metrics`: Generate key financial metrics and ratios
- `analyze_cash_flow`: Analyze cash flow trends and patterns
- `find_duplicate_transactions`: Identify potential duplicate transactions
- `analyze_customer_payment_patterns`: Analyze customer payment behavior

### Available Resources

The server provides access to the following QuickBooks resources:

- Customers (`quickbooks://customers`)
- Invoices (`quickbooks://invoices`)
- Accounts (`quickbooks://accounts`)
- Items/Products (`quickbooks://items`)
- Bills (`quickbooks://bills`)
- Payments (`quickbooks://payments`)

### Run

There are two ways to run the QuickBooks server:

#### 1. Standalone Server (Recommended)

```bash
python src/servers/quickbooks/main.py server
```

This runs the server in standalone mode on http://localhost:8001 using the "local" user ID (credentials stored at `~/.config/gumcp/quickbooks/local.json`).

#### 2. guMCP Local Framework

```bash
python src/servers/local.py --server quickbooks --user-id <your-user-id>
```

This runs the server through the guMCP local framework. The `user-id` parameter determines which credentials file is used for authentication (stored at `~/.config/gumcp/quickbooks/{user_id}.json`). For local testing, you can use "local" as your user ID.

> **Note:** The standalone server method is simpler and more reliable, especially if you encounter import errors with the local framework approach.

### API Keys (Optional)

The server also supports API key authentication for additional security. If you're using API keys, you'll need to include both the user ID and API key when connecting:

```bash
python src/servers/local.py --server quickbooks --user-id <your-user-id> --api-key <your-api-key>
```

For remote endpoints, the format is:
```
https://mcp.gumloop.com/quickbooks/{user_id}%3A{api_key}
```

### Credentials Storage

Your QuickBooks credentials are stored locally at:
```
~/.config/gumcp/quickbooks/{user_id}.json
```

Different user IDs will have separate credential files, allowing multiple QuickBooks accounts to be used with the same server installation.

## Testing

The tests for this server use pytest. To run the tests:

```bash
python -m tests.servers.test_runner --server=quickbooks
```

#### Running Tests

From the project root directory:

```bash
python tests/servers/test_runner.py --server=quickbooks
```

For testing with the SSE server (requires the SSE server to be running):

```bash
python tests/servers/test_runner.py --server=quickbooks --remote
```

For testing against a specific hosted guMCP server:

```bash
python tests/servers/test_runner.py --server=quickbooks --remote --endpoint=https://mcp.gumloop.com/quickbooks/{user_id}%3A{api_key}
```
#### Test Coverage

The QuickBooks tests cover:

1. Customer search functionality
2. Cash flow analysis
3. Duplicate transaction detection
4. Customer payment pattern analysis
5. Financial metrics generation
6. Error handling
7. Resource reading and listing
8. Server initialization and authentication


