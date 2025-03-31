# QuickBooks Server for guMCP

This server provides integration with QuickBooks Online for financial data access and analysis.

## Overview

The QuickBooks server enables:

- Access to QuickBooks resources (customers, invoices, accounts, etc.)
- Financial analysis tools (cash flow, metrics, duplicate detection)
- Customer payment pattern analysis
- SR&ED expense analysis for Canadian tax credits

## Prerequisites

- Python 3.11+
- A QuickBooks Online Developer account

## Setup

### Local Authentication

1. [Create a QuickBooks Online Developer account](https://developer.intuit.com/)
2. [Register a new application](https://developer.intuit.com/app/developer/qbo/docs/get-started)
   - The app should have the following scopes: `com.intuit.quickbooks.accounting`, `com.intuit.quickbooks.payment`
3. Configure a redirect URI for your application (e.g., http://localhost:8080)
4. Get your application's client ID and client secret
5. Local authentication uses a OAuth Configuration JSON file:

```
local_auth/oauth_configs/quickbooks/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "http://localhost:8080",
  "quickbooks_environment": "sandbox" // Optional, defaults to sandbox
}
```

6. To set up and verify authentication, run:

```bash
python src/servers/quickbooks/main.py auth
```

This will start the OAuth flow and save your credentials locally. By default, the credentials will be stored at `~/.config/gumcp/quickbooks/local.json`. Each user's credentials are stored in separate files based on their user ID.

7. To test the integration, run:

```bash
python -m tests.servers.test_runner --server=quickbooks
```

## Running the Server

There are two ways to run the QuickBooks server:

### 1. Standalone Server

```bash
python src/servers/quickbooks/main.py server
```

This runs the server in standalone mode on http://localhost:8001 using the "local" user ID.

### 2. guMCP Local Framework

```bash
python src/servers/local.py --server quickbooks --user-id <your-user-id>
```

This runs the server through the guMCP local framework. The `user-id` parameter determines which credentials file is used, and can use the placeholder `local`.

## API Keys (Optional)

For additional security, you can use API key authentication:

```bash
python src/servers/local.py --server quickbooks --user-id <your-user-id> --api-key <your-api-key>
```

For remote endpoints, the format is:

```
https://mcp.gumloop.com/quickbooks/{user_id}%3A{api_key}
```

## Credentials Storage

QuickBooks credentials are stored locally at:

```
~/.config/gumcp/quickbooks/{user_id}.json
```

Different user IDs have separate credential files, allowing multiple QuickBooks accounts to be used with the same server.

## Features

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

## Testing

### Running Tests

From the project root directory:

```bash
# Run tests locally
python -m tests.servers.test_runner --server=quickbooks

# For testing with the SSE server (requires the SSE server to be running)
python tests/servers/test_runner.py --server=quickbooks --remote

# For testing against a specific hosted guMCP server
python tests/servers/test_runner.py --server=quickbooks --remote --endpoint=https://mcp.gumloop.com/quickbooks/{user_id}%3A{api_key}
```

### Test Coverage

The QuickBooks tests cover:

1. Customer search functionality
2. Cash flow analysis
3. Duplicate transaction detection
4. Customer payment pattern analysis
5. Financial metrics generation
6. Error handling
7. Resource reading and listing
8. Server initialization and authentication
