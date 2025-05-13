# Gmail Server

guMCP server implementation for interacting with Gmail.

### Prerequisites

- Python 3.11+
- A Google Cloud Project with Gmail API enabled
- OAuth 2.0 credentials with the following scopes:
  - https://www.googleapis.com/auth/gmail.modify

### Local Authentication

1. [Create a new Google Cloud project](https://console.cloud.google.com/projectcreate)
2. [Enable the Gmail API](https://console.cloud.google.com/workspace-api/products)
3. [Configure an OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) ("internal" is fine for testing)
4. Add OAuth scope `https://www.googleapis.com/auth/gmail.modify`
5. [Create an OAuth Client ID](https://console.cloud.google.com/apis/credentials/oauthclient) for application type "Desktop App"
6. Download the JSON file of your client's OAuth keys
7. Rename the key file to `oauth.json` and place into the `local_auth/oauth_configs/gmail/oauth.json`

To authenticate and save credentials:

```bash
python src/servers/gmail/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.

### Available Tools

The Gmail server provides the following tools:

1. **read_emails**: Search and read emails in Gmail with filters
2. **send_email**: Send an email to one or more recipients
3. **update_email**: Update email labels (mark as read/unread, move to folders)
4. **create_draft**: Prepare emails without sending them (supports thread replies)
5. **forward_email**: Forward an email to other recipients
6. **list_labels**: Get all available Gmail labels
7. **create_label**: Create a new Gmail label for organization
8. **archive_email**: Move emails out of inbox
9. **trash_email**: Move emails to trash
10. **star_email**: Flag an email as important by adding a star
11. **unstar_email**: Remove the star flag from an email
12. **get_attachment_details**: Get details about attachments in an email
13. **download_attachment**: Generate a download link for an email attachment

All tools return the raw response data from the Gmail API, providing complete access to the information returned by Gmail.
