# Supabase Server

guMCP server implementation for interacting with Supabase for project management, database, and storage operations.

---

### 🚀 Prerequisites

- Python 3.11+
- A **Supabase Account** – [Sign up here](https://supabase.com/)

---

### 🔐 Supabase OAuth App Setup (First-time Setup)

1. **Log in to your [Supabase Dashboard](https://app.supabase.com/)**
2. Click on your **Organization name** in the top left
3. Go to **Organization Settings** (from the dropdown menu)
4. In the sidebar, click on **OAuth Apps**
5. Click the **Add Application** button
6. Fill out the application details:
   - **Application Name**: e.g., `guMCP Integration`
   - **Authorization callback URLs**: Your redirect URI (e.g., `http://localhost:8080/auth/callback`)
   - **Website URL**: Your application's URL (e.g., `http://localhost:8000`)
7. Select the following permissions:
   - **Organizations**: Organizations and all its members (Read and write)
   - **Projects**: Metadata, upgrade status, network restrictions and network bans (Read and write)
   - **REST**: PostgREST configurations (Read and write)
   - **Storage**: Storage buckets and files (Read and write)
8. Click **Confirm** to create the OAuth app
9. Save the generated **Client ID** and **Client Secret**

---

### 🔑 Obtaining Project ID and Service Role Key

For storage operations and data management tools, you'll need to use your project's reference ID and API key:

1. **Log in to your [Supabase Dashboard](https://app.supabase.com/)**
2. Select the **Project** you want to work with
3. Go to **Project Settings** in the sidebar
4. Click on **API** in the settings menu
5. In the **Project API Keys** section, you'll find:
   - **Project Reference ID**: The unique identifier for your project (displayed in the URL and in the Project Settings)
   - **Project API Keys**: 
     - **anon public**: For client-side operations with RLS policies
     - **service_role secret**: For admin operations (required for storage and some data operations)
     - Click the **Copy** button next to the appropriate key
6. Save these values to use with the tools

> ⚠️ **Important**: The service_role key has admin rights to your entire project. Never expose it in client-side code or public repositories.

---

### 📄 Local OAuth Configuration

Create a file named `oauth.json` in your directory (local_auth/oauth_configs/supabase/) with the following content:

```json
{
  "client_id": "your-oauth-client-id",
  "client_secret": "your-oauth-client-secret",
  "redirect_uri": "your-redirect-uri"
}
```

---

### 🔓 Authenticate with Supabase

Run the following command to initiate the OAuth login:

```bash
python src/servers/supabase/main.py auth
```

This will open your browser and prompt you to log in to Supabase. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/supabase/local_credentials.json
```

---

### 🛠 Features

This server exposes tools grouped into the following categories:

#### 🏢 Organization Management

- `list_organizations` – List all organizations you are a member of

#### 📂 Project Management

- `list_projects` – List all your Supabase projects
- `get_project` – Get details of a specific project
- `create_project` – Create a new Supabase project

#### 📊 Data Management

- `read_table_data` – Read data from a table in a Supabase project
- `create_table_data` – Create new rows in a table in a Supabase project
- `update_table_data` – Update rows in a table in a Supabase project
- `delete_table_data` – Delete rows from a table in a Supabase project

> ⚠️ **Important**: Tables must be created manually through the Supabase Dashboard. The data management tools only allow you to interact with existing tables. To create a table:
> 1. Navigate to the **Table Editor** section in your Supabase project
> 2. Click **New Table** and define your table schema
> 3. Set up appropriate columns with data types and constraints
> 4. Configure Row Level Security (RLS) policies as needed

#### 🗄️ Storage Management

- `create_storage_bucket` – Create a new storage bucket
- `list_storage_buckets` – List all storage buckets in a project
- `get_storage_bucket` – Get details of a specific bucket
- `delete_storage_bucket` – Delete a storage bucket

---

### ▶️ Running the Server and Client

#### 1. Start the Server

```bash
./start_sse_dev_server.sh
```

Make sure you've already authenticated using the `auth` command.

#### 2. Run the Client

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/supabase/local
```

---

### 📌 Notes on Supabase API Usage

- The server interacts with Supabase's management API for project/org operations
- Data management operations use the Supabase PostgreSQL database API
- Storage operations require a project-specific service_role API key
- Service_role keys should be used carefully and never exposed in client code
- The API uses standard REST endpoints for all operations
- Resource-level permissions apply in Supabase projects
- For storage operations, bucket-level permissions and RLS policies apply
- For data operations, Row Level Security (RLS) policies apply

### ⚠️ Important Security Notes

1. For all storage operations, you must use a service_role key, not an anon key
2. You can find your service_role key in the Supabase Dashboard under Project Settings → API
3. Service_role keys have full admin access to your project, so keep them secure
4. Use RLS policies to secure your storage buckets and database tables properly
5. Tables must be created manually through the Supabase Dashboard before using data management tools
