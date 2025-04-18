# Discourse Server

guMCP server implementation for interacting with Discourse forums and communities.

### Prerequisites

- Python 3.11+
- A Discourse instance
- A Discourse API key with appropriate permissions

### Features

- List categories from your Discourse instance
- Search for topics using keywords
- Create new topics in specific categories
- Post replies to existing topics
- Retrieve user information

### Local Authentication

To set up and authenticate with your Discourse instance, run:

```bash
python src/servers/discourse/main.py auth
```

You will be prompted to enter:
1. Your Discourse instance URL (e.g., https://forum.example.com)
2. Your Discourse API key
3. The username associated with the API key