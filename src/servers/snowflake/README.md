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
- Account identifier (e.g., `abcd.us-east-1`)

These credentials will be stored securely for reuse during development.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Snowflake:

#### 📁 Database Management
- `create_database` – Create a new database
- `list_databases` – List all databases
- `use_database` – Switch to a specific database
- `drop_database` – Drop a database

#### 📦 Table Management
- `create_table` – Create a new table with specified columns
- `list_tables` – List all tables in a given schema
- `drop_table` – Drop an existing table
- `describe_table` – View the structure of a table

#### ⚙️ Warehouse Management
- `create_warehouse` – Create a warehouse with custom size and settings
- `list_warehouses` – List all configured warehouses
- `use_warehouse` – Set the current warehouse

#### 🔍 Query Execution
- `execute_query` – Execute raw SQL queries
- `fetch_query_results` – Retrieve results of a previously executed query
- `handle_query_errors` – Standardized handling of SQL and connection errors

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
