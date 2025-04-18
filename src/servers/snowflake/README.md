# ❄️ Snowflake Server

guMCP server implementation for interacting with **Snowflake**.

---

### 📦 Prerequisites

- Python 3.11+
- A valid Snowflake account with appropriate roles and privileges

---

### 🔐 Authentication

Before using the server, you need to authenticate with your Snowflake account.

To authenticate and save credentials locally, run:

```bash
python src/servers/snowflake/main.py auth
```

You'll be prompted to enter the following:

- Username
- Password
- Account identifier (e.g., `abcd.us-east-1`) - you can find this by following the [Snowflake documentation on account identifiers](https://docs.snowflake.com/en/user-guide/admin-account-identifier#finding-the-organization-and-account-name-for-an-account)

These credentials will be stored securely for reuse during development.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Snowflake:

#### 📁 Database Management

- `create_database` – Create a new database in Snowflake
- `list_databases` – List all databases in Snowflake

#### 📦 Table Management

- `create_table` – Create a new table in Snowflake with support for constraints and indexes
- `list_tables` – List all tables in a database with filtering and sorting options
- `describe_table` – Describe the structure of a table in Snowflake

#### ⚙️ Warehouse Management

- `create_warehouse` – Create a new warehouse in Snowflake
- `list_warehouses` – List all warehouses in Snowflake

#### 🔍 Query Execution

- `execute_query` – Execute a SQL query on Snowflake

---

### ▶️ Run

#### Local Development

Start the Snowflake MCP server using:

```bash
./start_sse_dev_server.sh
```

Then run the local test client with:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/snowflake/local
```

---

### 🔒 Security Best Practices

- Never commit secrets or config files with sensitive data to version control
- Use least privilege roles for all Snowflake operations
- Enable Multi-Factor Authentication (MFA) for all user accounts

---

### 📚 Resources

- [Snowflake Documentation](https://docs.snowflake.com/)
- [Snowflake Python Connector](https://docs.snowflake.com/en/user-guide/python-connector)
- [SQL Command Reference](https://docs.snowflake.com/en/sql-reference)
