# Instacart Server

guMCP server implementation for interacting with Instacart's API.

### Prerequisites

- Python 3.11+
- An Instacart API key (obtain from [Instacart Developer Platform](https://docs.instacart.com/developer_platform_api/))

### Features

- Create shopping lists with:
  - Custom titles and instructions
  - Product items with quantities and units
  - Custom display text for items
  - Partner linkback URLs
- Create recipes with:
  - Ingredients and measurements
  - Cooking instructions
  - Author information
  - Cooking time and servings
  - Pantry items integration

### Local Authentication

To set up and verify authentication, run:

```bash
python src/servers/instacart/main.py auth
```

You will be prompted to enter in your Instacart API key

### Run

#### Local Development

```bash
python src/servers/local.py --server instacart --user-id local
```
