# Snowflake Server

guMCP server implementation for interacting with the **Snowflake**.

---

### 📦 Prerequisites

- Python 3.11+
- Snowflake account with appropriate privileges
- OAuth 2.0 credentials from Snowflake Security Integration

---

### 🔐 OAuth Setup

#### Option 1: HTTPS Setup (Recommended)
```sql
CREATE SECURITY INTEGRATION MY_SNOWSQL_CLIENT
TYPE = OAUTH
ENABLED = TRUE
OAUTH_CLIENT = CUSTOM
OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
OAUTH_REDIRECT_URI = 'https://your-redirect-uri'
OAUTH_ISSUE_REFRESH_TOKENS = TRUE
OAUTH_REFRESH_TOKEN_VALIDITY = 86400;
```

#### Option 2: HTTP Setup (Development Only)
```sql
CREATE SECURITY INTEGRATION MY_SNOWSQL_CLIENT
TYPE = OAUTH
ENABLED = TRUE
OAUTH_CLIENT = CUSTOM
OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
OAUTH_REDIRECT_URI = 'http://your-redirect-uri'
OAUTH_ISSUE_REFRESH_TOKENS = TRUE
OAUTH_REFRESH_TOKEN_VALIDITY = 86400
OAUTH_ALLOW_NON_TLS_REDIRECT_URI = TRUE;
```

After creating the security integration, run these commands to get the required credentials:

```sql
-- Get OAuth details
DESC SECURITY INTEGRATION MY_SNOWSQL_CLIENT;

-- Get client secret
SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('MY_SNOWSQL_CLIENT');

You will get 2 secrets, note down either one.
```

---

### 🔐 Local Authentication

Create a file named `oauth_configs/snowflake/oauth.json` with the following structure:

```json
{
  "client_id": "your-oauth-client-id",
  "client_secret": "your-oauth-client-secret",
  "redirect_uri": "your-redirect-uri",
  "account": "your-account-identifier",
}
```

To authenticate and save credentials for local testing, run:

```bash
python src/servers/snowflake/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Snowflake:

- `create_database` – Create a new database in Snowflake
- `create_schema` – Create a new schema in Snowflake
- `list_schemas` – List all schemas in a database
- `list_databases` – List all databases in Snowflake
- `create_table` – Create a new table with support for constraints and indexes
- `list_tables` – List all tables in a database with filtering and sorting options
- `describe_table` – Get the structure of a Snowflake table including columns, data types, and constraints
- `create_warehouse` – Create a new warehouse in Snowflake
- `list_warehouses` – List all warehouses in Snowflake
- `execute_query` – Execute any SQL query on Snowflake with transaction support

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Snowflake MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/snowflake/local
```

---

### 📎 Notes

- Ensure your Snowflake account has the necessary privileges to create and manage databases and tables
- For production environments, always use HTTPS for OAuth redirect URIs
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic.

---

### 📚 Resources

- [Snowflake OAuth Documentation](https://docs.snowflake.com/en/user-guide/oauth-custom)
- [Snowflake SQL Reference](https://docs.snowflake.com/en/sql-reference)
