# WhatsApp Business API Server

guMCP server implementation for interacting with **WhatsApp Business API**.

---

### 📦 Prerequisites

- Python 3.11+
- A WhatsApp Business Account
- WhatsApp Business API credentials

---

### 🔑 API Credentials Setup

#### Step 1: Create WhatsApp Business Account (WABA)
1. Go to [Meta Business Manager](https://business.facebook.com/)
2. Create a new business account or select an existing one
3. Navigate to Business Settings > Accounts > WhatsApp Accounts
4. Click "Add" and follow the setup wizard
5. Note down your WhatsApp Business Account ID (WABA ID)

#### Step 2: Set Up Developer Account
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app or select an existing one:
   - Click "Create App"
   - Select "Business" as the app type
   - Choose "Other" for the use case
   - Select your business portfolio
   - Add WhatsApp as a product

#### Step 3: Configure App Permissions
1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from the dropdown
3. Add the following permissions:
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`
   - `whatsapp_business_manage_events`
   - `email`

#### Step 4: Get Required Credentials

1. Generate Permanent Access Token:
   - Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
   - Select your app
   - Click "Generate Access Token"
   - Select your business account
   - Copy the generated token
   - Note down the WABA ID
   - Note down the Phone Number ID

#### Required Credentials Summary
- WhatsApp Business Account ID (WABA ID)
- Phone Number ID
- Permanent Access Token

---

### 🔐 Local Authentication

To authenticate and save your WhatsApp API credentials for local testing, run:

```bash
python src/servers/whatsapp/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with WhatsApp Business API:

#### Account Management Tools
- `get_account_info` – Get information about your WhatsApp Business Account
- `get_account_verification_status` – Check the verification status of your account

#### Phone Number Tools
- `list_phone_numbers` – List all phone numbers associated with your account
- `get_phone_number_details` – Get detailed information about a phone number
- `get_business_profile` – Get your WhatsApp Business Profile information

#### Template Management Tools
- `list_message_templates` – List all your message templates
- `create_message_template` – Create a new message template
- `get_template_preview` – Preview a message template
- `get_message_template_details` – Get details about a specific template
- `update_message_template` – Update an existing template
- `delete_message_template` – Delete a template from your account

#### Messaging Tools
- `send_template_message` – Send a message using a template

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the WhatsApp MCP server and make it available for integration and testing.

You can also start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/whatsapp/local
```

---

### 📎 Notes

- The server respects WhatsApp's API rate limits and guidelines
- Template messages must follow WhatsApp's content policies
- All phone numbers must be in international format (e.g., +1XXXXXXXXXX)
- Template messages require approval before they can be used
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services

---

### 📚 Resources

- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp)
- [WhatsApp Business API Reference](https://developers.facebook.com/docs/whatsapp/api/messages)
- [WhatsApp Business API Templates](https://developers.facebook.com/docs/whatsapp/api/messages/message-templates)
