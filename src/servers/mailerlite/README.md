# MailerLite Server

guMCP server implementation for interacting with the MailerLite API, supporting subscriber management, campaign automation, form creation, and email marketing features.

---

### Prerequisites

- Python 3.11+
- A MailerLite account with API access
- MailerLite API key with appropriate permissions

---

#### How to Get Your MailerLite API Key

1. Log in to your MailerLite account at [MailerLite](https://app.mailerlite.com)
2. Click on **Integrations** option in the left side bar once logged in [Integrations](https://dashboard.mailerlite.com/integrations)
3. Click on **API** under the MailerLite API section and click on Use
4. Click the **Generate new token** button
5. Give your API key a descriptive name (e.g., "guMCP Integration")
6. Choose IP Restriction to "All" if you want to allow all IPs to access the API, else choose "Enable IP Allowlist" and enter the IP address of the server you want to allow.
7. Copy the generated API key and keep it secure. You will be prompted to enter this during the authentication step.

### Local Authentication

Local authentication uses your MailerLite API key. The credentials will be stored securely at:

```
local_auth/credentials/mailerlite/
```

To authenticate and save credentials for local testing, run:

```bash
python src/servers/mailerlite/main.py auth
```

This will prompt you to enter your MailerLite API key. After successful authentication, your credentials will be stored securely for reuse.

---

### Supported Tools

This server exposes the following tools for interacting with MailerLite:

#### Subscriber Management

- `list_all_subscribers` – List all subscribers with optional filtering and pagination
- `create_subscriber` – Add a new subscriber with custom fields
- `update_subscriber` – Update an existing subscriber's information
- `get_subscriber` – Retrieve details of a specific subscriber
- `delete_subscriber` – Remove a subscriber from your list

#### Group Management

- `list_groups` – List all groups with optional filtering and sorting
- `create_group` – Create a new subscriber group
- `update_group` – Update an existing group's name
- `delete_group` – Remove a group
- `get_group_subscribers` – Get subscribers belonging to a specific group
- `assign_subscriber_to_group` – Add a subscriber to a group
- `unassign_subscriber_from_group` – Remove a subscriber from a group

#### Field Management

- `list_fields` – List all custom fields
- `create_field` – Create a new custom field
- `update_field` – Update an existing field
- `delete_field` – Remove a custom field

#### Campaign Management

- `list_campaigns` – List all campaigns with optional filtering
- `get_campaign` – Get details of a specific campaign
- `create_campaign` – Create a new email campaign
- `update_campaign` – Update an existing campaign
- `schedule_campaign` – Schedule a campaign for delivery
- `cancel_campaign` – Cancel a scheduled campaign
- `delete_campaign` – Delete a campaign
- `list_campaign_languages` – Get available languages for campaigns

#### Form Management

- `list_forms` – List all forms with optional filtering and pagination
- `get_form` – Get details of a specific form
- `update_form` – Update a form's name
- `delete_form` – Delete a form

#### Webhook Management

- `list_webhooks` – List all webhooks
- `get_webhook` – Get details of a specific webhook
- `create_webhook` – Create a new webhook
- `update_webhook` – Update an existing webhook
- `delete_webhook` – Delete a webhook

---

### Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the MCP server and make it available for integration and testing.

You can also start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/mailerlite/local
```

---

### Notes

- Ensure your MailerLite API key has the necessary permissions for the operations you want to perform
- All API calls include proper error handling and response validation
- This server is designed to integrate with guMCP agents for tool-based LLM workflows

---

### Resources

- [MailerLite API Documentation](https://developers.mailerlite.com/)
- [MailerLite Help Center](https://www.mailerlite.com/help)
- [MailerLite Dashboard](https://app.mailerlite.com)
