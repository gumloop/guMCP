# Loops Server

guMCP server implementation for interacting with Loops email marketing and customer engagement APIs.

## 📦 Prerequisites

- Python 3.11+
- A Loops account
- Loops API Key (found in your Loops Dashboard)

## 🔑 API Key Generation

To generate a Loops API key, follow these steps:

1. Log in to your Loops Dashboard
2. Navigate to your User profile on the top left corner of the page
3. Click on the settings icon present over there
4. Navigate to API section [API Section](https://app.loops.so/settings?page=api)
5. Click on Generate Key 
   
> ⚠️ **Important**: Your API Key will only be shown once. Store it securely!

## 🔐 Local Authentication

To authenticate and save your Loops credentials for local testing, run:

```bash
python src/servers/loops/main.py auth
```

This will:
1. Prompt you to enter your Loops API key
2. Store your credentials securely

## 🛠️ Features

The Loops server supports a comprehensive set of operations grouped into categories:

### Contact Management:

- `add_contact`: Adds a contact to your Loops account. Include a userId field to enable contact deletion by user ID
- `add_custom_property`: Adds a new custom property for contacts
- `delete_contact_by_email`: Deletes a contact by email
- `delete_contact_by_user_id`: Deletes a contact by user ID. Only works if userId was provided when creating the contact
- `get_contact_by_email`: Gets a contact by email
- `get_contact_by_user_id`: Gets a contact by user ID
- `update_contact_by_email`: Updates a contact by email, or creates one if not existing
- `update_contact_by_user_id`: Updates a contact by user ID

### Email Tools:

- `send_transactional_email`: Sends a transactional email

### Events:

- `send_event_by_email`: Sends an event by email
- `send_event_by_user_id`: Sends an event by user ID

API call

## Understanding User IDs in Loops

When working with contacts in Loops, there are two different types of IDs:

1. **Contact ID**: This is an internal ID that Loops generates when a contact is created. While this ID is returned in API responses, it's primarily for internal use and is not directly usable for deletion or fetching operations.

2. **User ID**: This is a custom identifier that YOU provide when creating a contact. This is the ID you should use with `delete_contact_by_user_id` and other user ID-based operations.

To use user ID-based operations effectively:
- When creating a contact with `add_contact`, include a `user_id` field in your request
- Use this same `user_id` in subsequent operations that require a user ID

If you don't have a user ID for a contact, you can still delete the contact using the email address with `delete_contact_by_email`.

## ▶️ Running the Server and Client

### 1. Start the Server

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

### 2. Connect with the Client

Once the server is running, connect to it using the test client:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/loops/local
```

## 📎 Notes

### API Key Security:
- Store API keys securely and never commit them to source control
- Rotate your keys periodically for enhanced security
- Use appropriate access levels for different environments

### Rate Limiting:
- Loops API has rate limits that vary by endpoint
- The server handles rate limiting gracefully with appropriate error messages

### Email Delivery:
- Transactional emails have higher delivery priority
- Test transactional templates before sending to customers
- Monitor your email performance through the Loops Dashboard

## 📚 Resources

- [Loops API Documentation](https://docs.loops.so/reference)
- [Loops Dashboard](https://app.loops.so)
- [Loops API Usage Guide](https://docs.loops.so/reference/api-key-reference) 