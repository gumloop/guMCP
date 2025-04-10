# Calendly Server

guMCP server implementation for interacting with Calendly scheduling and event management.

### Prerequisites

- Python 3.11+
- A Calendly account with API access
- Calendly OAuth credentials

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```json
local_auth/oauth_configs/calendly/oauth.json
```

Create the following file with the relevant attributes for your Calendly app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "xxxxxxxxxxxxxxxxxxxxx"
}
```

When authorizing users, the server will automatically:

1. Redirect to Calendly's authorization URL with your configured credentials
2. Exchange the received code for an access token using Calendly's OAuth endpoints

For local development, you can authenticate using:

```bash
python src/servers/calendly/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.

### Available Tools

The Calendly server provides the following functionality:

#### List Event Types
Get all available event types (meeting templates) in your Calendly account.

#### Get Availability
Check available time slots for a specific event type within a date range.

#### List Scheduled Events
View all scheduled meetings in a given time range with optional status filtering.

#### Cancel Event
Cancel a scheduled event with an optional cancellation reason.

#### Create Scheduling Link
Generate a single-use scheduling link for a specific event type.
