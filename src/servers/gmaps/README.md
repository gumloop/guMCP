# Google Maps Server

guMCP server implementation for interacting with the **Google Maps API**.

---

### 📦 Prerequisites

- Python 3.11+
- A Google Cloud project with the **Google Maps API enabled**
- Google Maps API key

---

### 🔑 API Key Generation

To generate a Google Maps API key, follow these steps:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs for your project:
   - Maps JavaScript API
   - Geocoding API
   - Places API
   - Distance Matrix API
   - Elevation API
   - Directions API
4. Navigate to "APIs & Services" > "Credentials"
5. Click "Create Credentials" and select "API key"
6. Copy the generated API key

---

### 🔐 Local Authentication

Local authentication uses a Google Maps API key stored securely. To authenticate and save your API key for local testing, run:

```bash
python src/servers/gmaps/main.py auth
```

It will ask you to enter the api key.
After successful authentication, your API key will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Google Maps:

- `address_to_coordinates` – Convert an address to latitude/longitude coordinates
- `coordinates_to_address` – Convert coordinates to a human-readable address
- `search_places` – Search for places around a specific location
- `place_details` – Get detailed information about a place
- `get_place_reviews` – Retrieve reviews for a specific place
- `distance_matrix` – Calculate distance and duration between locations
- `elevation` – Get elevation data for coordinates
- `directions` – Get directions between two locations

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Google Maps MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/gmaps/local
```

---

### 📎 Notes

- Ensure your Google Cloud project has **Google Maps API** access enabled
- If you're testing with multiple users or environments, use different `user_id` values
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic

---

### 📚 Resources

- [Google Maps API Documentation](https://developers.google.com/maps)
- [Google Maps API Reference](https://developers.google.com/maps/documentation)
