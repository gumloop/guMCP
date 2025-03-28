# Discord Server

GuMCP server implementation for interacting with Discord.

### Prerequisites

- Python 3.11+
- A Discord OAuth2 application ([Discord Developer Portal](https://discord.com/developers/applications))
- Appropriate bot permissions and OAuth2 scopes

### Authentication

Authentication uses OAuth2 and requires a configuration file:

```
local_auth/oauth_configs/discord/oauth.json
```

```json
{
  "client_id": "YOUR_DISCORD_APP_CLIENT_ID",
  "client_secret": "YOUR_DISCORD_APP_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8080"
}
```

#### Setting Up Your Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select an existing one
3. Under the "OAuth2" section:
   - Add `http://localhost:8080` as a redirect URI
   - Save changes
4. Note your Client ID and Client Secret
5. Under "Bot" section:
   - Create a bot if you haven't already
   - Enable Scopes:
     - bot
     - identify
     - guilds
     - messages.read

#### Running Authentication

To set up authentication:

```bash
python src/servers/discord/main.py auth
```

This will:

1. Open your browser to the Discord authorization page
2. Ask you to authorize your application
3. Redirect back to localhost to complete authentication
4. Store your credentials securely for future use

### Run

#### Local Development

```bash
python src/servers/local.py --server discord --user-id local
```
