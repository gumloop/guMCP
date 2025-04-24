# PayPal GuMCP Server

GuMCP server implementation for interacting with the PayPal API using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A PayPal Developer account with a REST API application created
- OAuth credentials configured for your application

---

### 🛠️ Step 1: Create a PayPal Account

#### Option A: Personal Account
1. Go to [PayPal](https://www.paypal.com)
2. Click on "Sign Up" in the top right corner
3. Select "Personal Account"
4. Follow these steps:
   - Enter your email address and click "Next"
   - Enter your phone number and click "Next"
   - Set a secure password and click "Next"
   - Enter your personal information:
     - Nationality
     - First Name
     - Middle Name (optional)
     - Last Name
     - Date of Birth
   - Click "Next"
   - Enter your address details:
     - Street Address
     - Town/City
     - State
     - ZIP/Postal Code
   - Agree to PayPal's terms and conditions
   - Click "Create Account"
5. After account creation, link your payment method:
   - Click on "Wallet" in your PayPal dashboard
   - Select "Link a card"
   - Choose card type (Debit or Credit)
   - Enter card details:
     - Card number
     - Expiration date (MM/YY)
     - CVV/Security code
     - Cardholder name
   - Enter billing address (if different from account address)
   - Click "Link Card" to complete the process
6. Set up Developer Account:
   - Go to [PayPal Developer Portal](https://developer.paypal.com/)
   - Sign in with your PayPal account
   - Navigate to Dashboard > My Apps & Credentials
   - Create a new app or use Default app:
     - Click on "Create App" button
     - Enter your app name
     - Select your account type (Personal)
     - Choose the sandbox environment for testing
     - Click "Create App"
   - Generate API credentials:
     - In your app dashboard, find the "Live" and "Sandbox" tabs
     - For development, use the "Sandbox" tab
     - Click on "Show" under "Secret" to reveal your Client Secret
     - Copy both the Client ID and Client Secret
     - Store these credentials securely

#### Option B: Business Account
1. Go to [PayPal](https://www.paypal.com)
2. Click on "Sign Up" in the top right corner
3. Select "Business Account"
4. Follow these steps:
   - Enter your business email address and click "Next"
   - Set a secure password and click "Next"
   - Select your business type:
     - Individual/Sole Trader
     - Partnership
     - Corporation
   - Enter your business details:
     - Product or service keywords
     - Business purpose code
     - Personal PAN (if applicable)
     - PayPal CC statement
     - Website URL (optional)
   - Complete the verification process
5. Set up Developer Account:
   - Go to [PayPal Developer Portal](https://developer.paypal.com/)
   - Sign in with your PayPal account
   - Navigate to Dashboard > My Apps & Credentials
   - Create a new app or use Default app:
     - Click on "Create App" button
     - Enter your app name
     - Select your account type (Business)
     - Choose the sandbox environment for testing
     - Click "Create App"
   - Generate API credentials:
     - In your app dashboard, find the "Live" and "Sandbox" tabs
     - For development, use the "Sandbox" tab
     - Click on "Show" under "Secret" to reveal your Client Secret
     - Copy both the Client ID and Client Secret
     - Store these credentials securely

---

### 🛠️ Step 2: Configure OAuth Settings

1. Once the app is created, you'll see your Client ID and Client Secret in the app details
2. Make sure to note these down securely

---

### 🛠️ Step 3: Set Up Local Configuration

1. Create a new folder called `local_auth` in your project directory
2. Inside that, create a folder called `oauth_configs`
3. Inside that, create a folder called `paypal`
4. Create a new file called `oauth.json` in the `paypal` folder
5. Copy and paste this into the file, replacing the placeholders with your actual values:

```json
{
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here"
}
```

> ⚠️ **IMPORTANT**: Never share or commit this file to version control. Add it to your `.gitignore`.
---

### 🔐 Step 4: Authenticate Your App

1. Open your terminal
2. Run this command:
   ```bash
   python src/servers/paypal/main.py auth
   ```
3. The server will automatically:
   - Read the OAuth configuration
   - Generate and store the access token
   - Save the credentials securely

> You only need to do this authentication step once, unless your token expires.
---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with PayPal:

#### Order Management
- `create_order` – Create a new PayPal order with purchase units
- `get_order` – Get details for a specific order
- `confirm_order` – Confirm an order with payment source

#### Plan Management
- `create_plan` – Create a new billing plan
- `list_plans` – List available billing plans
- `get_plan` – Get plan details
- `update_plan` – Update plan properties
- `activate_plan` – Activate a plan
- `deactivate_plan` – Deactivate a plan

#### Product Management
- `create_product` – Create a new product
- `list_products` – List available products
- `get_product` – Get product details
- `update_product` – Update product properties

#### Invoice Management
- `search_invoices` – Search for invoices based on various criteria including recipient info, invoice details, date ranges, and status

#### Subscription Management
- `create_subscription` – Create a new subscription with plan ID, optional quantity, auto-renewal, custom ID, and subscriber details
- `get_subscription` – Get detailed information for a specific subscription including billing info, status, and subscriber details

---

### ▶️ Running the Server

#### Local Development

1. Start the server:
   ```bash
   ./start_sse_dev_server.sh
   ```

2. In a new terminal, start the test client:
   ```bash
   python RemoteMCPTestClient.py --endpoint http://localhost:8000/paypal/local
   ```

---

### 📎 Important Notes

- Ensure your PayPal application is properly configured in the developer portal
- The server uses PayPal's sandbox environment by default
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services
- The server implements rate limiting and proper error handling for API requests
- All API calls are authenticated using the stored OAuth tokens
- Subscription operations require a valid plan ID
- Invoice searches support multiple criteria combinations
- Subscription and invoice status changes may take time to reflect
- Always verify subscription status before processing payments
- Keep track of subscription IDs for future reference

---

### 📚 Need Help?

- [PayPal Developer Portal](https://developer.paypal.com/)
- [PayPal REST API Documentation](https://developer.paypal.com/docs/api/overview/)
- [PayPal OAuth 2.0 Guide](https://developer.paypal.com/docs/api/overview/#get-an-access-token)
- [PayPal Subscriptions API Documentation](https://developer.paypal.com/docs/api/subscriptions/v1/)
- [PayPal Invoicing API Documentation](https://developer.paypal.com/docs/api/invoicing/v2/)
