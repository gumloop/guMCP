# QuickBooks Server

guMCP server implementation for interacting with QuickBooks Online.

### Prerequisites

- Python 3.11+
- A QuickBooks Online Developer account


### Local Authentication

1. [Create a QuickBooks Online Developer account](https://developer.intuit.com/)
2. [Register a new application](https://developer.intuit.com/app/developer/qbo/docs/get-started)
3. Configure a redirect URI for your application (e.g., http://localhost:8080)
4. Get your application's client ID and client secret
5. Create an `oauth.json` file:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "http://localhost:8080"
}
```

Save this file at:
```
local_auth/oauth_configs/quickbooks/oauth.json
```

6. To set up and verify authentication, run:

```bash
python src/servers/quickbooks/main.py auth
```

7. To test the integration, run:

```bash
python src/servers/quickbooks/main.py test
```

### Available Tools

The QuickBooks server provides the following tools:

- `search_customers`: Search for customers by name, email, or phone
- `analyze_sred`: Analyze expenses for potential SR&ED eligibility
- `analyze_cash_flow`: Analyze cash flow trends and patterns
- `find_duplicate_transactions`: Identify potential duplicate transactions
- `analyze_customer_payment_patterns`: Analyze customer payment behavior
- `generate_financial_metrics`: Generate key financial metrics and ratios

### Available Resources

The server provides access to the following QuickBooks resources:

- Customers (`quickbooks://customers`)
- Invoices (`quickbooks://invoices`)
- Accounts (`quickbooks://accounts`)
- Items/Products (`quickbooks://items`)
- Bills (`quickbooks://bills`)
- Payments (`quickbooks://payments`)

### Run

#### Local Development

```bash
python src/servers/local.py --server quickbooks --user-id local
```

#### Standalone Server

```bash
python src/servers/quickbooks/main.py server
``` 