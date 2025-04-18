# SendGrid Server

guMCP server implementation for interacting with SendGrid's email API.

### Prerequisites

- Python 3.11+
- A SendGrid API key (obtain from [SendGrid Dashboard](https://app.sendgrid.com/settings/api_keys))

### Features

- Send emails with customizable content and sender information
- Use email templates with dynamic variables
- Schedule email sending for future delivery
- Retrieve email statistics and performance metrics
- Manage contacts in your SendGrid marketing lists
- Control email suppression lists (bounces, blocks, spam reports, unsubscribes)

### Local Authentication

To set up and verify authentication, run:

```bash
python src/servers/sendgrid/main.py auth
```

You will be prompted to enter your SendGrid API key.
