# Stripe Server

guMCP server implementation for interacting with Stripe API.

---

### 📦 Prerequisites

- Python 3.11+
- A Stripe account with API access
- OAuth 2.0 credentials configured for standard accounts

---

### 🔐 Local Authentication

Local authentication uses a Stripe OAuth Configuration JSON file located at:

```
local_auth/oauth_configs/stripe/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx", // The client_secret is your secret API key, see the Reference guides below
  "redirect_uri": "http://localhost:8080"
}
```

To set this up properly, refer to Stripe's official documentation for creating and managing OAuth applications:

➡️ [Stripe OAuth Standard Accounts Guide](https://docs.stripe.com/connect/oauth-standard-accounts#integrating-oauth)
➡️ [Stripe OAuth Reference](https://docs.stripe.com/connect/oauth-reference)

To authenticate and save credentials for local testing, run:

```bash
python src/servers/stripe/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Stripe:

- `list_customers` – List all customers
- `retrieve_balance` – Retrieve current account balance
- `list_subscriptions` – List all subscriptions
- `create_payment_intent` – Create a new payment intent
- `update_subscription` – Update subscription metadata or settings
- `list_payment_intents` – List all payment intents
- `list_charges` – List charges made to customers
- `create_customer` – Create a new customer
- `create_invoice` – Create a draft invoice for a customer
- `list_invoices` – List all invoices
- `retrieve_customer` – Get detailed information of a customer
- `create_product` – Create a product
- `confirm_payment_intent` – Confirm a payment intent
- `list_products` – List all products
- `cancel_subscription` – Cancel a subscription
- `retrieve_subscription` – Retrieve subscription details
- `create_price` – Create a recurring or one-time price for a product
- `create_subscription` – Create a subscription with a customer and price
- `update_customer` – Update customer fields

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/stripe/local
```

---

### 📎 Notes

- Ensure your Stripe app has the required permissions enabled in the dashboard.
- Use different `user_id` values if you're testing with multiple environments.
- This server is designed to integrate with guMCP agents for tool-based LLM workflows.
- Make sure you have provided your Anthropic API key in the `.env` file.

---

### 📚 Resources

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe OAuth Guide](https://docs.stripe.com/connect/oauth-standard-accounts#connect-users)
