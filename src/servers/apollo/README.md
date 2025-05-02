# Apollo Server

guMCP server implementation for interacting with Apollo.io for sales prospecting, contact management, and CRM functionality.

### 📦 Prerequisites

- Python 3.11+
- An Apollo.io account ([Sign up here](https://www.apollo.io/))

### 🔑 API Key Generation

To generate an Apollo.io API key, follow these steps:

1. Log in to your [Apollo.io account](https://www.apollo.io/)
2. Navigate to Settings > Integrations > API > Connect
3. Choose between two types of API keys:
   - **Regular API Key**: For basic operations like search and enrichment
   - **Master API Key**: For advanced operations requiring elevated permissions
4. Click "Generate New API Key"
5. Copy the generated API key

### 🔐 Local Authentication

To authenticate and save your API key for local testing, run:

```bash
python src/servers/apollo/main.py auth
```

This will prompt you to enter your API key, which will then be saved to:
```
local_auth/credentials/apollo/local_credentials.json
```

### Features

The Apollo server supports a comprehensive set of operations grouped into categories:

- **Search Tools**:
  - `search_contacts`: Search for contacts in your Apollo account
  - `search_accounts`: Search for accounts that have been added to your team's Apollo account

- **Enrichment Tools**:
  - `enrich_person`: Enrich data for a person using Apollo's People Enrichment API
  - `enrich_organization`: Enrich data for a company using Apollo's Organization Enrichment API

- **Contact Management Tools**:
  - `create_contact`: Create a new contact in Apollo
  - `update_contact`: Update an existing contact in your Apollo account
  - `list_contact_stages`: Retrieve the IDs for available contact stages in your Apollo account

- **Account Management Tools**:
  - `create_account`: Add a new account to your Apollo account
  - `update_account`: Update an existing account in your Apollo account
  - `list_account_stages`: Retrieve the IDs for available account stages in your Apollo account

- **Deal Management Tools**:
  - `create_deal`: Create a new deal for an Apollo account
  - `update_deal`: Update an existing deal in your Apollo account
  - `list_deals`: List all deals in your Apollo account
  - `list_deal_stages`: Retrieve information about every deal stage in your Apollo account

- **Task and User Management Tools**:
  - `create_task`: Create tasks in Apollo for you and your team
  - `list_users`: Get a list of all users (teammates) in your Apollo account

### Running the Server and Client

#### 1. Start the Server

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

#### 2. Connect with the Client

Once the server is running, connect to it using the test client:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/apollo/local
```

### 📎 Notes

- **API Key Types**:
  - Regular API key: Suitable for basic operations like search and enrichment
  - Master API key: Required for user management, deal management, and account management operations

- **API Usage and Credits**:
  - People Search and Organization Search consume credits
  - Enrichment operations may consume credits depending on your plan
  - Monitor your API usage and credits through the Apollo.io dashboard

- **Security**:
  - Master API keys have elevated permissions and should be handled securely
  - Never share your API keys in public repositories or unsecured channels
  - Rotate your API keys periodically for enhanced security

### 📚 Resources

- [Apollo.io API Documentation](https://www.apollo.io/api/)
- [Apollo.io API Reference](https://www.apollo.io/api/)
