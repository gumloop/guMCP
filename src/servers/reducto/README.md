# Reducto Server

guMCP server implementation for interacting with Reducto's document processing API.

### Prerequisites

- Python 3.11+
- A Reducto API key

### Features

- Document Processing:
  - Upload PDF documents
  - Parse documents with OCR
  - Split documents into sections
  - Extract structured data using schemas
- Job Management:
  - Check job status
  - Cancel running jobs
  - Synchronous and asynchronous operations
- Webhook Configuration:
  - Configure webhook portal for job notifications

### Local Authentication

To set up and verify authentication, run:

```bash
python src/servers/reducto/main.py auth
```

You will be prompted to enter your Reducto API key.
