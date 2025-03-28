# Discord Server
MCP server implementation for interacting with Discord.

### Prerequisites

- Python 3.11+
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/docs/getting-started))
- Appropriate bot permissions

### Authentication

Authentication uses a credentials file:
```
local_auth/credentials/discord/local_credentials.json
```
```json
{
  "token": "your_discord_bot_token_here"
}
```

To set up and verify authentication, run:
```bash
python src/servers/discord/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server discord --user-id local
```