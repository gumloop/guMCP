# DocuSign Server

guMCP server implementation for interacting with DocuSign for electronic signatures, document management, and user administration.

### Prerequisites

- Python 3.11+
- A DocuSign account ([Sign up here](https://www.docusign.com/))
- API access with appropriate permissions:
  - OAuth authentication credentials for secure API access
  - Appropriate DocuSign plan to access the required features

### Local Authentication

Create a file named `oauth.json`:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "http://localhost:8080"
}
```

Authenticate with DocuSign:

**Using the OAuth authentication flow**:
   ```bash
   python src/servers/docusign/main.py auth
   ```
   This will guide you through the OAuth process and save your credentials to:
   ```
   local_auth/credentials/docusign/local_credentials.json
   ```

### Features

The DocuSign server supports a comprehensive set of operations grouped into categories:

- **Template Management Tools**: List, retrieve, and create templates
- **Envelope Management Tools**: Create, retrieve, send, and track envelopes
- **User Management Tools**: Create, list, and retrieve user information

### Running the Server and Client

#### 1. Start the Server

```bash
# Run the server with saved credentials (after running the auth command)
python src/servers/main.py
```

#### 2. Connect with the Client

Once the server is running, connect to it using the test client:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/docusign/local
```

### Tool Documentation

#### Template Management

- **list_templates**: List all templates in your DocuSign account with optional filtering
- **get_template**: Get detailed information about a specific template
- **create_template**: Create a new template in your DocuSign account

#### Envelope Management

- **create_envelope**: Create a new envelope in DocuSign from a template or with documents
- **get_envelope**: Get detailed information about a specific envelope
- **send_envelope**: Send a draft envelope to recipients for signing
- **get_envelope_status_bulk**: Get status information for multiple envelopes at once

#### User Management

- **create_user**: Create new users in your DocuSign account
- **list_users**: List all users in your DocuSign account with optional filtering
- **get_user**: Get detailed information about a specific user

### Notes on DocuSign API Usage

- When using the DocuSign API, you may need to specify an account ID for most operations if you have access to multiple accounts.
- Envelope operations require careful setup of recipients, documents, and sometimes tabs (signature fields).
- Document data is typically passed in base64-encoded format.
- The API follows REST principles and returns detailed JSON responses for all operations.