# Cal.com Server

guMCP server implementation for interacting with Cal.com's API.

### Prerequisites

- Python 3.11+
- A Cal.com API key (obtain from [Cal.com API Settings](https://app.cal.com/settings/developer/api-keys))

### Features

- Manage Cal.com user profile
- Access and work with event types
- Create and manage bookings:
  - Create new bookings with attendee details
  - Reschedule existing bookings
  - Cancel bookings
  - Confirm pending bookings
  - Decline bookings
- Retrieve schedules and availability

### Local Authentication

To set up and verify authentication, run:

```bash
python src/servers/cal/main.py auth
```

You will be prompted to enter your Cal.com API key.

### Run

#### Local Development

```bash
python src/servers/local.py --server cal --user-id local
```
