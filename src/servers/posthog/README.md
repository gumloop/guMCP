# PostHog Server

guMCP server implementation for interacting with PostHog Analytics API.

---

### 📦 Prerequisites

- Python 3.11+
- A PostHog account with API access
- PostHog API key with appropriate permissions

---

### 🛠️ Step 1: Create a PostHog Account

1. Go to [PostHog](https://app.posthog.com/signup)
2. Sign up for a new account or log in to your existing account

---

### 🛠️ Step 2: Set Up Your Organization and Project

1. If you don't have an organization:
   - Click "Create Organization"
   - Enter your organization name and details
   - Click "Create Organization"
2. If you don't have a project:
   - Click "Create Project"
   - Enter your project name and details
   - Click "Create Project"

---

### 🛠️ Step 3: Generate Your API Key

1. Go to Project Settings
2. Navigate to Access Tokens
3. Click on "User" in the top navigation bar
4. Select "Personal API Keys" from the dropdown
5. Click "Create Personal API Key"
6. Choose the access level:
   - Select "All Access" for full access
   - Or select specific organization/project access
7. Click "Create Token"
8. Copy the generated API key (you won't be able to see it again)

---

### 🔐 Step 4: Authenticate Your App

1. Open your terminal
2. Run this command:
   ```bash
   python src/servers/posthog/main.py auth
   ```
3. Enter your API key when prompted
4. You're now authenticated! 🎉

> You only need to do this authentication step once, unless your API key changes.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with PostHog:

#### Actions Management Tools
- `list_actions` – List all actions in PostHog
- `create_action` – Create a new action in PostHog
- `get_action` – Get details of a specific action
- `update_action` – Update an existing action

#### Event Tracking Tools
- `capture_event` – Capture a new event in PostHog
- `identify_user` – Identify a user with properties
- `group_identify` – Identify a group with properties
- `capture_group_event` – Capture an event for a group

#### Feature Flag Tools
- `check_feature_flag` – Check if a feature flag is enabled
- `get_feature_flag_payload` – Get the payload for a feature flag
- `get_all_flags` – Get all feature flags

#### Annotation Management Tools
- `list_annotations` – List all annotations
- `create_annotation` – Create a new annotation
- `get_annotation` – Get details of a specific annotation
- `update_annotation` – Update an existing annotation

#### Cohort Management Tools
- `list_cohorts` – List all cohorts
- `create_cohort` – Create a new cohort
- `get_cohort` – Get details of a specific cohort
- `update_cohort` – Update an existing cohort
- `delete_cohort` – Delete a cohort

#### Dashboard Management Tools
- `list_dashboards` – List all dashboards
- `create_dashboard` – Create a new dashboard
- `get_dashboard` – Get details of a specific dashboard
- `update_dashboard` – Update an existing dashboard
- `delete_dashboard` – Delete a dashboard
- `list_dashboard_collaborators` – List collaborators for a dashboard
- `add_dashboard_collaborator` – Add a collaborator to a dashboard
- `get_dashboard_sharing` – Get sharing settings for a dashboard

#### Person Management Tools
- `list_persons` – List all persons
- `get_person` – Get details of a specific person

#### Experiment Management Tools
- `list_experiments` – List all experiments
- `create_experiment` – Create a new experiment
- `get_experiment` – Get details of a specific experiment
- `update_experiment` – Update an existing experiment
- `check_experiments_requiring_flag` – Check experiments that require a feature flag

#### Insight Management Tools
- `list_insights` – List all insights
- `create_insight` – Create a new insight
- `get_insight` – Get details of a specific insight
- `update_insight` – Update an existing insight
- `get_insight_sharing` – Get sharing settings for an insight
- `get_insight_activity` – Get activity for a specific insight
- `mark_insight_viewed` – Mark an insight as viewed
- `get_insights_activity` – Get activity for all insights
- `get_trend_insights` – Get trend insights
- `create_trend_insight` – Create a new trend insight

---

### ▶️ Running the Server

#### Local Development

1. Start the server:
   ```bash
   ./start_sse_dev_server.sh
   ```

2. In a new terminal, start the test client:
   ```bash
   python RemoteMCPTestClient.py --endpoint http://localhost:8000/posthog/local
   ```

---

### 📎 Important Notes

- Ensure your PostHog API key has the necessary permissions for the operations you want to perform
- Event capture and feature flag evaluations use the project API token, which is automatically retrieved during authentication
- For group analytics, make sure group analytics is enabled in your PostHog instance
- This server is designed to integrate with guMCP agents for tool-based LLM workflows
- All API calls include proper error handling and response validation

---

### 📚 Resources

- [PostHog API Documentation](https://posthog.com/docs/api)
- [PostHog Feature Flags](https://posthog.com/docs/feature-flags)
- [PostHog Event Tracking](https://posthog.com/docs/api/ingest-live-data)
- [PostHog Cohorts](https://posthog.com/docs/api/cohorts)
- [PostHog Actions](https://posthog.com/docs/api/actions)
- [PostHog Annotations](https://posthog.com/docs/api/annotations)
- [PostHog Dashboards](https://posthog.com/docs/api/dashboards)
- [PostHog Insights](https://posthog.com/docs/api/insights)
- [PostHog Experiments](https://posthog.com/docs/api/experiments)
