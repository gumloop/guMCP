# Lemlist Server

guMCP server implementation for interacting with the Lemlist API, supporting campaign management, scheduling, and outreach automation.

---

### Prerequisites

- Python 3.11+
- A Lemlist account with API access
- Lemlist API key (token) with appropriate permissions

---

#### How to Get Your Lemlist API Key

1. Log in to your Lemlist account.
2. Click on your profile icon (top right) and go to **Settings**.
3. Navigate to the **Integrations** or **API** section.
4. Locate your **API Key** (sometimes called a token or access key).
5. Copy the API key and keep it secure. You will be prompted to enter this during the authentication step above.

### Local Authentication

Local authentication uses your Lemlist API key. The credentials will be stored securely at:

```
local_auth/credentials/lemlist/
```

To authenticate and save credentials for local testing, run:

```bash
python src/servers/lemlist/main.py auth
```

This will prompt you to enter your Lemlist API key. After successful authentication, your credentials will be stored securely for reuse.



---

### Supported Tools

This server exposes the following tools for interacting with Lemlist:

#### Team & Account

- `get_team` – Get the team information.
- `get_senders` – Get the list of senders.
- `get_credits` – Get the credits information.
- `get_user` – Get the user information by user ID.

#### Campaign Management

- `get_all_campaigns` – Retrieve a paginated list of Lemlist campaigns. Supports sorting and pagination.
- `get_campaign` – Retrieve the details of a specific Lemlist campaign by its campaignId.
- `create_campaign` – Create a new campaign in Lemlist with optional name. Returns campaign, sequence, and schedule IDs.
- `update_campaign` – Update the configuration of a Lemlist campaign by campaignId. Supports updating name and multiple campaign settings.
- `pause_lemlist_campaign` – Pause a running Lemlist campaign by its campaignId.

#### Campaign Export

- `start_lemlist_campaign_export` – Initiate an asynchronous export of campaign statistics. Returns export ID for status tracking.
- `get_campaign_export_status` – Check the status of an asynchronous campaign export in Lemlist. Returns export status and CSV URL if available.
- `export_lemlist_campaign` – Set an email address to receive the download link for a Lemlist campaign export when it's done.

#### Schedules

- `get_all_schedules` – Retrieve all schedules associated with a Lemlist team, with pagination and sorting options.
- `get_schedule` – Retrieve the details of a specific Lemlist schedule by its scheduleId.
- `get_campaign_schedules` – Retrieve all schedule objects linked to a specific Lemlist campaign by campaignId.
- `create_schedule` – Create a new schedule in Lemlist. Supports custom name, delay, timezone, start/end times, and active weekdays.
- `update_schedule` – Update an existing Lemlist schedule by scheduleId. Supports updating name, delay, timezone, start/end times, and weekdays.
- `delete_schedule` – Delete a specific schedule in Lemlist by its scheduleId.
- `associate_schedule_with_campaign` – Associate a schedule with a specific Lemlist campaign using campaignId and scheduleId.

#### Leads

- `create_lead_in_campaign` – Add a lead to a specific Lemlist campaign. Supports deduplication, email verification, LinkedIn enrichment, phone finding, and custom lead data.
- `delete_lead` – Delete a lead from a specific Lemlist campaign by campaignId and leadId (email address).
- `mark_lead_as_interested_all_campaigns` – Mark a specific lead as interested in all campaigns using their email address.
- `mark_lead_as_not_interested_all_campaigns` – Mark a specific lead as not interested in all campaigns using their email address.
- `mark_lead_as_interested_in_campaign` – Mark a specific lead as interested in a specific Lemlist campaign using their email address.
- `mark_lead_as_not_interested_in_campaign` – Mark a specific lead as not interested in a specific Lemlist campaign using their email address.

#### Unsubscribes

- `get_all_unsubscribes` – Retrieve a paginated list of all unsubscribed people from Lemlist.
- `export_unsubscribes` – Download a CSV file containing all unsubscribed email addresses from Lemlist.
- `add_unsubscribe` – Add an email address or domain to Lemlist's unsubscribed list.
- `delete_unsubscribe` – Delete an email address or domain from Lemlist's unsubscribed list.

#### Database

- `get_database_filters` – Retrieve all available Lemlist database filters for constructing advanced queries.

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
python RemoteMCPTestClient.py --endpoint http://localhost:8000/lemlist/local
```

---

### Notes

- Ensure your Lemlist API key has the necessary permissions for the operations you want to perform.
- All API calls include proper error handling and response validation.
- This server is designed to integrate with guMCP agents for tool-based LLM workflows.

---

### Resources

- [Lemlist API Documentation](https://developer.lemlist.com/)
- [Lemlist Help Center](https://help.lemlist.com/)
- [Lemlist Campaigns](https://app.lemlist.com/campaigns)
