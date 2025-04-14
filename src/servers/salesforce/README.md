# Salesforce Server

guMCP server implementation for interacting with Salesforce.

### Prerequisites

- Python 3.11+
- A Salesforce Developer Account ([Sign up for Developer Edition](https://developer.salesforce.com/signup))
- A Connected App in Salesforce with the following OAuth scopes:
  - full
  - api
  - id
  - profile
  - email
  - address
  - phone
  - web
  - refresh_token
  - offline_access
  - openid
  - custom_permissions

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```
local_auth/oauth_configs/salesforce/oauth.json
```

Create the following file with the relevant attributes for your Connected App:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "https://xxxxxxxxxxxxx"
}
```

- Note: Salesforce requires https for the redirect uri, so if running locally, setup an [ngrok redirect](https://ngrok.com/docs/universal-gateway/http/) to port 8080

To set up and verify authentication, run:

```bash
python src/servers/salesforce/main.py auth
```

### Available Tools

The Salesforce server provides the following tools:

1. **SOQL Query** (`soql_query`)
   - Executes SOQL queries to retrieve Salesforce records
   - Supports relationships and complex filters
   - Example: `SELECT Id, Name FROM Account WHERE Industry = 'Technology'`

2. **SOSL Search** (`sosl_search`)
   - Performs text-based searches across multiple Salesforce objects
   - Example: `FIND {Cloud} IN ALL FIELDS RETURNING Account, Opportunity`

3. **Object Description** (`describe_object`)
   - Retrieves detailed metadata about a Salesforce object
   - Includes fields, relationships, and permissions
   - Shows field types, requirements, and picklist values

4. **Record Operations**
   - **Get Record** (`get_record`): Retrieve specific records by ID
   - **Create Record** (`create_record`): Create new records
   - **Update Record** (`update_record`): Modify existing records
   - **Delete Record** (`delete_record`): Remove records

5. **Organization Limits** (`get_org_limits`)
   - Retrieves current organization limits and usage
   - Shows maximum, used, and remaining values
   - Calculates usage percentages

### Run

#### Local Development

```bash
python src/servers/local.py --server salesforce --user-id local
```

### Security Notes

- Always keep your OAuth credentials secure
- Use appropriate OAuth scopes for your use case
- Regularly rotate your client secret
- Monitor API usage to stay within limits

### Error Handling

The server provides detailed error messages for:
- Missing or invalid parameters
- API limits exceeded
- Authentication issues
- Invalid SOQL/SOSL syntax
- Record access permissions

### Rate Limiting

- Be mindful of Salesforce API limits
- Check organization limits before performing bulk operations
- Use `get_org_limits` to monitor API usage

### Best Practices

1. Always use SOQL queries with appropriate WHERE clauses
2. Include only necessary fields in queries
3. Use SOSL search for text-based queries across multiple objects
4. Check field accessibility before performing operations
5. Handle rate limits and bulk operations appropriately
