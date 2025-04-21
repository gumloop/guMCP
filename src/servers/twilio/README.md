# Twilio Server

guMCP server implementation for interacting with Twilio's messaging, voice, verification, and communication APIs.

## 📦 Prerequisites

- Python 3.11+
- A Twilio account ([Sign up here](https://www.twilio.com/try-twilio))
- Twilio Account SID (found in your Twilio Console Dashboard)
- Twilio API Key SID (created in the Twilio Console)
- Twilio API Key Secret (provided when creating an API key)

## 🔑 API Key Generation

To generate Twilio API keys, follow these steps:

1. Log in to your [Twilio Console](https://www.twilio.com/console)
2. Navigate to Account (Create Account if you don't have one)
3. Navigate to API Keys & Tokens [API Keys & Tokens](https://console.twilio.com/us1/account/keys-credentials/api-keys)
4. Click "Create API Key"
5. Enter a friendly name for your API key
6. Select the appropriate key type:
   - Standard: Most common, good for most applications
   - Main: Has full account access, use with caution
7. Copy both the API Key SID and API Key Secret
8. You will also require your Account SID which can be found in your Account Dashboard
   
> ⚠️ **Important**: Your API Key Secret will only be shown once. Store it securely!

## 🔐 Local Authentication

To authenticate and save your Twilio credentials for local testing, run:

```bash
python src/servers/twilio/main.py auth
```

This will:
1. Prompt you to enter your:
   - Account SID (found in your Twilio Console Dashboard)
   - API Key SID
   - API Key Secret
2. Validate your credentials with Twilio
3. Store your credentials securely

## 🛠️ Features

The Twilio server supports a comprehensive set of operations grouped into categories:

### Messaging Tools:

- `send_message`: Send SMS, MMS, or WhatsApp messages
- `list_messages`: List message history 
- `fetch_message`: Fetch a message by SID
- `delete_message`: Delete a message by SID

### Voice Tools:

- `make_call`: Make an outbound voice call with TwiML or text-to-speech
- `list_calls`: List recent calls
- `fetch_call`: Fetch a call by SID

### Verify Tools:

- `list_verify_services`: List all Twilio Verify services
- `create_verify_service`: Create a new Twilio Verify service
- `start_verification`: Send a verification code via SMS, call, etc.
- `check_verification`: Check a verification code

### Lookup Tools:

- `lookup_phone_number`: Lookup phone number information and carrier data

### Conversations Tools:

- `list_conversation_services`: List all conversation services
- `create_conversation_service`: Create a new conversation service
- `list_conversations`: List conversations in a service
- `create_conversation`: Create a new conversation
- `add_conversation_participant`: Add a participant to a conversation
- `send_conversation_message`: Send a message in a conversation

### Video Tools:

- `list_video_rooms`: List all video rooms
- `create_video_room`: Create a new video room
- `fetch_video_room`: Fetch details about a video room
- `complete_video_room`: Complete (end) a video room

## ▶️ Running the Server and Client

### 1. Start the Server

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

### 2. Connect with the Client

Once the server is running, connect to it using the test client:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/twilio/local
```

## 📎 Notes

### API Key Security:
- API Keys provide better security than using your primary auth token
- Store API keys securely and never commit them to source control
- Rotate your keys periodically for enhanced security

### Phone Number Verification:
- During testing, you can only send messages to verified numbers unless your account is upgraded
- Voice calls to unverified numbers may be restricted based on your account status

### Rate Limiting:
- Twilio API has rate limits that vary by endpoint
- The server handles rate limiting gracefully with appropriate error messages

### Costs and Billing:
- SMS, voice calls, and other Twilio services incur charges
- Monitor your usage through the [Twilio Console](https://www.twilio.com/console)
- Set up spending alerts to avoid unexpected charges

## 📚 Resources

- [Twilio API Documentation](https://www.twilio.com/docs/api)
- [Twilio Python SDK Documentation](https://www.twilio.com/docs/libraries/python)
- [Twilio Console](https://www.twilio.com/console)
- [Twilio API Keys Documentation](https://www.twilio.com/docs/iam/keys/api-key)
- [Twilio Rate Limits](https://www.twilio.com/docs/usage/api/rate-limits) 