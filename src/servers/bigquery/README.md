# BigQuery guMCP Server

guMCP server implementation for interacting with Google BigQuery for data analytics and SQL queries.

---

### 🚀 Prerequisites

- Python 3.11+
- A **Google Cloud Project** with BigQuery API enabled
- OAuth 2.0 credentials with appropriate permissions for BigQuery

---

### 🔐 Google Cloud Project Setup (First-time Setup)

1. [Create a new Google Cloud project](https://console.cloud.google.com/projectcreate)
2. [Enable the BigQuery API](https://console.cloud.google.com/apis/library/bigquery.googleapis.com)
3. [Configure an OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) ("internal" is fine for testing)
4. Add OAuth scopes:
   - https://www.googleapis.com/auth/bigquery
   - https://www.googleapis.com/auth/cloud-platform
5. [Create an OAuth Client ID](https://console.cloud.google.com/apis/credentials/oauthclient) for application type "Desktop App"
6. Download the JSON file of your client's OAuth keys

---

### 📄 Local OAuth Credentials Setup

Rename the downloaded OAuth key file to `oauth.json` and place it in:
```
local_auth/oauth_configs/bigquery/oauth.json
```

---

### 🔓 Authentication with BigQuery

Run the following command to initiate the OAuth login:

```bash
python src/servers/bigquery/main.py auth
```

This will open your browser and prompt you to log in to your Google account. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/bigquery/local_credentials.json
```

---

### 🛠 Features

This server exposes tools grouped into the following categories:

#### 📊 Query Tools

- `run_query` – Execute a SQL query on BigQuery and return formatted results

#### 📚 Dataset Management Tools

- `list_datasets` – List all available datasets in the BigQuery project
- `get_dataset_info` – Get detailed information about a specific dataset

#### 📋 Table Management Tools

- `list_tables` – List tables within a specific dataset
- `get_table_schema` – Get the schema details of a specific table
- `preview_table_data` – Preview data from a table (first rows)

---

### ▶️ Running the Server and Client

#### 1. Start the Server

```bash
./start_sse_dev_server.sh
```

Ensure your service account credentials are properly set up.

#### 2. Run the Client

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/bigquery/local
```

---

### 📌 Notes on BigQuery API Usage

- SQL queries must be valid [GoogleSQL](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax)
- Projects, datasets, and tables must exist for operations to succeed
- Queries may incur costs based on the amount of data processed
- Consider using dataset and table prefetching to improve performance
- Results are paginated for large queries to manage memory usage