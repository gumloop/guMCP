# Shopify Server

guMCP server implementation for interacting with Shopify's Admin API using GraphQL.

## Prerequisites

- Python 3.11+
- A Shopify store (Partner or Development store)
- A Shopify Custom App with API access

## Creating a Development Store

1. Log in to your Shopify partners dashboard (https://partners.shopify.com/)
2. Go to **Stores** > **Add store**
3. Select **Development store**
4. Fill in the required information:
   - Store name (will become your `your-store-name.myshopify.com` URL)
   - Store type (Development store)
   - Development store purpose (choose appropriate option)
   - Login credentials
5. Click **Save** to create your test store
6. Once created, you can access your development store from the Stores section

## Setting Up a Shopify Custom App

1. Log in to your Shopify partners dashboard (https://partners.shopify.com/)
2. Go to **Apps**
3. Click **Create an app**
4. Click on **Create app manually**
5. Enter a name for your app (e.g. "guMCP Integration")
6. Copy the `client id` and `client secrets`
7. Click on **Choose Distribution** > **Public distribution** 
8. Click on **Configuration** > Add your desired **Allowed redirection URL**
9. Select **Store** > select the store you created above

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

## Testing with Development Store

1. Ensure your app is installed on your development store
2. Update the `custom_subdomain` in your OAuth config to match your development store
3. Run the authentication flow to generate credentials for your development store
4. All API calls will now use your development store data, keeping your production data safe
