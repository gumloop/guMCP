# Apollo Server

guMCP server implementation for interacting with Apollo.io for sales prospecting, contact management, and CRM functionality.

### Prerequisites

- Python 3.11+
- An Apollo.io account ([Sign up here](https://www.apollo.io/))
- API key with appropriate permissions:
  - Regular API key for basic operations
  - Master API key for advanced operations (required for user management, deal management, etc.)

### Local Authentication

There are two ways to provide your Apollo API key:

1. **Using the authentication flow**:
   ```bash
   python src/servers/apollo/main.py auth
   ```
   This will prompt you to enter your API key, which will then be saved to:
   ```
   local_auth/credentials/apollo/local_credentials.json
   ```

2. **Provide it on the command line**:
   You can pass your API key directly when running the server (recommended for development):
   ```bash
   python src/servers/local.py --server apollo --user-id local --api-key your_master_api_key_here
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

```bash
# Run the server with saved API key (after running the auth command)
python src/servers/main.py
```

#### 2. Connect with the Client

Once the server is running, connect to it using the test client:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/apollo/local
```

### Note on API Usage and Master API Key

Some operations in Apollo.io consume credits:
- People Search and Organization Search consume credits
- Enrichment operations may consume credits depending on your plan

Several operations require a master API key:
- User management operations
- Deal management operations
- Account management operations
- Contact management operations requiring write access

A master API key has elevated permissions and should be handled securely.
