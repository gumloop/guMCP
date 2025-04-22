# Apify GuMCP Server

GuMCP server implementation for interacting with the Apify API using token-based authentication.

## 📦 Prerequisites

- Python 3.11+
- An Apify account ([Sign up here](https://apify.com/))
- Apify API token (found in your Apify account settings)

## 🔑 API Token Generation

To generate your Apify API token, follow these steps:

1. Log in to your [Apify Console](https://console.apify.com/)
2. Navigate to Settings > API & Integrations [API & Integrations](https://console.apify.com/settings/integrations)
3. Create a new API token if not already created by clicking the "Create a new token" button.
4. Copy the token value - you will need it for authentication

> ⚠️ **Important**: Your API token provides access to your Apify account and resources. Store it securely and never share it publicly!

## 🔐 Local Authentication

To authenticate and save your Apify credentials for local testing, run:

```bash
python src/servers/apify/main.py auth
```

This will:
1. Prompt you to enter your Apify API token
2. Store your credentials securely for future use

## 🛠️ Features

The Apify server supports the following operations grouped by resource type:

### Actor Tools:

- `create_actor` – Create a new Actor
- `build_actor` – Build an Actor from source code
- `list_actors` – List all Actors
- `get_actor` – Get metadata for one Actor
- `delete_actor` – Delete an Actor
- `run_actor` – Start an Actor run asynchronously
- `list_actor_runs` – List runs for an Actor

### Task Tools:

- `list_tasks` – List all Tasks
- `get_task` – Get a Task
- `create_task` – Create a new Task
- `update_task` – Update an existing Task
- `delete_task` – Delete a Task
- `update_task_input` – Update input for a Task
- `run_task` – Run a Task
- `list_task_runs` – List runs for a Task

### Dataset Tools:

- `list_datasets` – List all Datasets
- `delete_dataset` – Delete a Dataset

## 🔄 Actor Build and Run Workflow

When working with custom actors, you must follow this workflow:

1. **Create the actor** - Use the `create_actor` tool to set up a new actor with source code
2. **Build the actor** - Use the `build_actor` tool to compile the actor's code
3. **Run the actor** - Only after a successful build can you use the `run_actor` tool

If you try to run an actor that hasn't been built yet, you'll receive an error message prompting you to build it first.

## ▶️ Running the Server and Client

### 1. Start the Server

Launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

### 2. Connect with the Client

Once the server is running, connect to it using the test client:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/apify/local
```


## 📎 Notes

- All requests to the Apify API require authentication
- The free plan has usage limits - check the [Apify pricing page](https://apify.com/pricing) for details
- Some operations may take time to complete, especially actor runs

## 📚 Resources

- [Apify API Documentation](https://docs.apify.com/api/v2)
- [Apify Platform Documentation](https://docs.apify.com/platform)
- [Apify Console](https://console.apify.com/)
- [Apify SDK Documentation](https://sdk.apify.com/)
- [Apify Actors Documentation](https://docs.apify.com/platform/actors)