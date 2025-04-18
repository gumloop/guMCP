# Browserbase GuMCP Server

GuMCP server implementation for interacting with the **Browserbase API** for headless browser automation.

---

### 📦 Prerequisites

- Python 3.11+
- A [Browserbase](https://browserbase.com) account
- **Browserbase API key**
- **Browserbase Project ID**

---

### 🔑 API Key & Project ID Setup

To use Browserbase services, you’ll need both your API key and project ID:

1. Log in to your [Browserbase dashboard](https://app.browserbase.com/)
2. Navigate to **API Keys** section
3. Copy your API key
4. Navigate to **Projects**, and copy your desired **Project ID**

---

### 🔐 Local Authentication

For local development, securely authenticate with your API key and project ID by running:

```bash
python src/servers/browserbase/main.py auth
```

This will prompt you to enter your **Browserbase API key** and **project ID**, which will then be securely stored for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tool for interacting with Browserbase:

- `load_webpage_tool` – Load a webpage URL in a headless browser using Browserbase and return results

---

### ▶️ Run

#### Local Development

Start the server using:

```bash
./start_sse_dev_server.sh
```

This will launch the Browserbase MCP server for local development and testing.

To test using the local client:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/browserbase/local
```

---

### 📎 Notes

- Ensure that both your **API key** and **project ID** are valid and stored correctly
- Make sure you have sufficient credits in your Browserbase account
- The server leverages **Playwright** for browser automation
- All browser sessions are managed and automatically closed after each request
- Each request initializes a new headless browser instance and cleans up after execution

---

### 📚 Resources

- [Browserbase Documentation](https://docs.browserbase.com/)
- [Playwright Documentation](https://playwright.dev/python/docs/intro)
- [Browserbase API Reference](https://docs.browserbase.com/api-reference)