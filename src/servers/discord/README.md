# Discord Server
MCP server implementation for interacting with Discord.

### Prerequisites

- Python 3.11+
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/docs/getting-started))
- Appropriate bot permissions

### Authentication

Three authentication methods are supported:

1. **Environment variable**:
   ```bash
   export DISCORD_BOT_TOKEN=your_token_here
   ```

2. **OAuth configuration file**:
   ```
   local_auth/oauth_configs/discord/oauth.json
   ```
   ```json
   {
     "token": "your_token_here"
   }
   ```

3. **Interactive prompt** (local development only):
   ```bash
   python src/servers/discord/main.py auth
   ```

### Run

#### Local Development

```bash
python src/servers/local.py --server discord --user-id local
```