# Shopify Server

guMCP server implementation for interacting with Shopify's Admin API using GraphQL.

## Features

- GraphQL support for all Shopify Admin API endpoints
- Create, read, update, and delete products, collections, orders, and more
- Support for complex queries and mutations through GraphQL

## Prerequisites

- Python 3.11+
- A Shopify store (Partner or Development store)
- A Shopify Custom App with API access

## Setting Up a Shopify Custom App

1. Log in to your Shopify Admin dashboard
2. Go to **Apps** > **App and sales channel settings**
3. Click **Develop apps** (you may need to enable Developer Preview in your store)
4. Click **Create an app**
5. Enter a name for your app (e.g. "guMCP Integration")
6. Select **Custom app** as the app type
7. Click **Create app**

### Configure API Scopes

1. In your app settings, go to the **Configuration** tab
2. Click **Configure** in the Admin API section
3. Select the required API scopes (at minimum, you'll need):
   - `read_products`, `write_products` for product operations
   - Add additional scopes as needed for your specific use case
4. Click **Save**

### Get API Credentials

1. Go to the **API credentials** tab
2. Click **Install app** to generate API credentials
3. Note your Admin API access token
4. In the same page, find the Client ID and Client Secret for OAuth 

## Local Authentication

Local authentication uses an OAuth Configuration JSON file:

```
local_auth/oauth_configs/shopify/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8080",
  "custom_subdomain": "your-store-name"
}
```

Notes:
- The `custom_subdomain` is your Shopify store name (e.g., if your Shopify store URL is `example.myshopify.com`, use `example`)

### Authentication Flow

To set up and verify authentication, run:

```bash
python src/servers/shopify/main.py auth
```

This will guide you through the authentication process and save your credentials locally.