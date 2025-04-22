# Hunter.io Server

guMCP server implementation for interacting with **Hunter.io** API V2.

---

### 📦 Prerequisites

- Python 3.11+
- A Hunter.io account
- Hunter.io API key

---

### 🔑 API Key Generation

To generate a Hunter.io API key, follow these steps:

1. Go to the [Hunter.io API Keys](https://hunter.io/api-keys) page
2. Click "Generate API Key" if you don't have one already
3. Copy the generated API key

---

### 🔐 Local Authentication

Local authentication uses a Hunter.io API key stored securely. To authenticate and save your API key for local testing, run:

```bash
python src/servers/hunter_io/main.py auth
```

It will ask you to enter the api key.
After successful authentication, your API key will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Hunter.io:

#### Core API Tools
- `domain_search` – Search for all email addresses associated with a given domain
- `email_finder` – Find a specific email address using domain and name
- `email_verifier` – Verify the deliverability and validity of an email address
- `email_count` – Get the count of email addresses for a domain
- `email_enrichment` – Get detailed information about an email address
- `company_enrichment` – Get detailed information about a company
- `account_info` – Get your Hunter.io account information

#### Lead Management Tools
- `list_leads` – List all leads with optional filtering
- `get_lead` – Get detailed information about a specific lead
- `create_lead` – Create a new lead with contact information
- `update_lead` – Update an existing lead's information
- `delete_lead` – Delete a lead from your account

#### Leads Lists Tools
- `list_leads_lists` – Get all leads lists in your account
- `get_leads_list` – Get a specific leads list by ID
- `create_leads_list` – Create a new leads list with a name
- `update_leads_list` – Update a leads list by ID
- `delete_leads_list` – Delete a leads list by ID

#### Campaign Tools
- `list_campaigns` – List all campaigns in your account
- `list_campaign_recipients` – List all recipients of a campaign
- `add_campaign_recipients` – Add recipients to a campaign
- `cancel_campaign_recipients` – Cancel scheduled emails to recipients
- `start_campaign` – Start a campaign that is in draft state

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Hunter.io MCP server and make it available for integration and testing.

You can also start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/hunter_io/local
```

---

### 📎 Notes

- The server respects Hunter.io's API rate limits:
  - 50 requests per day on the free plan
  - 500 requests per day on the starter plan
  - Custom limits for higher-tier plans
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic

---

### 📚 Resources

- [Hunter.io API Documentation](https://hunter.io/api/docs)
