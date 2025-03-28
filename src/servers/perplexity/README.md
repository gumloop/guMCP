# Perplexity Server

GuMCP server implementation for interacting with Perplexity AI's API.

### Prerequisites

- Python 3.11+
- A Perplexity API key (obtain from [Perplexity AI](https://www.perplexity.ai/))

### Features

- Web search with recency filters (hour, day, week, month, year)
- Chat with different Perplexity models:
  - sonar
  - sonar-pro
  - sonar-deep-research
  - sonar-reasoning
  - sonar-reasoning-pro
- Code assistance with customizable language settings
- Related questions retrieval

### Local Authentication

To set up and verify authentication, run:

```bash
python src/servers/perplexity/main.py auth
```

You will be prompted to enter in your Perplexity API key

### Run

#### Local Development

```bash
python src/servers/local.py --server perplexity --user-id local
```
