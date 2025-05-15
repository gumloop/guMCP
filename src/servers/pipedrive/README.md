# Pipedrive GuMCP Server

GuMCP server implementation for interacting with the Pipedrive API using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A Pipedrive account with API access
- OAuth credentials configured for your application

---

### 🛠️ Step 1: Create a Pipedrive Account

1. Go to [Pipedrive](https://www.pipedrive.com)
2. Click on "Get Started" or "Sign Up"
3. Choose your plan (Free or Paid)
4. Follow these steps:
   - Enter your email address
   - Create a password
   - Enter your company name
   - Select your industry
   - Choose your company size
   - Click "Create Account"
5. After account creation:
   - Complete your profile setup
   - Configure your company settings
   - Set up your sales pipeline
6. Set up Developer Account:
   - Go to [Pipedrive Developer Portal](https://developers.pipedrive.com/)
   - Sign in with your Pipedrive account
   - Navigate to User Profile in top Right corner
   - Click on Developer Hub
---

### 🛠️ Step 2: Configure OAuth Settings

1. Create a new OAuth application:
   - Click on "Create App"
   - Enter your app name
   - Set the redirect URI (e.g., http://localhost:8080)
   - Select required scopes:
     - `base` - Basic access
     - `deals:full` - Full access to deals
     - `contacts:full` - Full access to contacts
     - `products:full` - Full access to products
     - `activities:full` - Full access to activities
     - `leads:full` - Full access to leads
   - Click "Create App"
2. Note down your Client ID and Client Secret

---

### 🛠️ Step 3: Set Up Local Configuration

1. Create a new folder called `local_auth` in your project directory
2. Inside that, create a folder called `oauth_configs`
3. Inside that, create a folder called `pipedrive`
4. Create a new file called `oauth.json` in the `pipedrive` folder
5. Copy and paste this into the file, replacing the placeholders with your actual values:

```json
{
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here",
  "redirect_uri": "your-redirect-uri-here"
}
```

> ⚠️ **IMPORTANT**: Never share or commit this file to version control. Add it to your `.gitignore`.
---

### 🔐 Step 4: Authenticate Your App

1. Open your terminal
2. Run this command:
   ```bash
   python src/servers/pipedrive/main.py auth
   ```
3. The server will automatically:
   - Read the OAuth configuration
   - Generate and store the access token
   - Save the credentials securely

> You only need to do this authentication step once, unless your token expires.
---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Pipedrive:

#### Activity Management
- `create_activity` – Create a new activity (call, meeting, task, etc.)
- `get_activity` – Get details for a specific activity
- `update_activity` – Update an existing activity
- `delete_activity` – Delete an activity (soft delete)

#### Deal Management
- `create_deal` – Create a new deal
- `get_deal` – Get details for a specific deal
- `update_deal` – Update deal properties
- `delete_deal` – Delete a deal (soft delete)

#### Lead Management
- `create_lead` – Create a new lead
- `get_lead` – Get lead details
- `delete_lead` – Delete a lead (soft delete)

#### Note Management
- `create_note` – Create a new note
- `get_note` – Get note details
- `update_note` – Update note content
- `delete_note` – Delete a note (soft delete)

#### Person Management
- `create_person` – Create a new person (contact)
- `get_person` – Get person details
- `update_person` – Update person information
- `delete_person` – Delete a person (soft delete)

#### Product Management
- `create_product` – Create a new product
- `get_product` – Get product details
- `update_product` – Update product information
- `delete_product` – Delete a product (soft delete)

#### Organization Management
- `create_organization` – Create a new organization
- `get_organization` – Get organization details
- `update_organization` – Update organization information
- `delete_organization` – Delete an organization (soft delete)

#### User details
- `get_user` – List user details

#### Get tools
- `get_all_deals` – List all deals from Pipedrive
- `get_all_activities` – List all activities from Pipedrive
- `get_all_leads` – List all leads from Pipedrive
- `get_all_notes` – List all notes from Pipedrive
- `get_all_persons` – List all persons from Pipedrive
- `get_all_organizations` – List all organizations from Pipedrive
- `get_all_products` – List all products from Pipedrive
- `get_all_users` – List all users from Pipedrive

---

### ▶️ Running the Server

#### Local Development

1. Start the server:
   ```bash
   ./start_sse_dev_server.sh
   ```

2. In a new terminal, start the test client:
   ```bash
   python RemoteMCPTestClient.py --endpoint http://localhost:8000/pipedrive/local
   ```

---

### 📎 Important Notes

- Ensure your Pipedrive application is properly configured in the developer portal
- The server uses Pipedrive's production environment by default
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services
- The server implements rate limiting and proper error handling for API requests
- All API calls are authenticated using the stored OAuth tokens
- Delete operations are soft deletes - items are marked as inactive but remain in the system
- Keep track of IDs for future reference as they are required for updates and deletions
- Some operations may require specific permissions in your Pipedrive account
- The API has rate limits that should be considered when making multiple requests

---

### 📚 Need Help?

- [Pipedrive Developer Portal](https://developers.pipedrive.com/)
- [Pipedrive API Documentation](https://developers.pipedrive.com/docs/api/v1/)
- [Pipedrive OAuth Guide](https://pipedrive.readme.io/docs/marketplace-oauth-authorization)
- [Pipedrive API Reference](https://developers.pipedrive.com/docs/api/v1/Reference)
- [Pipedrive Webhooks Documentation](https://developers.pipedrive.com/docs/api/v1/Webhooks) 