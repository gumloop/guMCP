# Gumloop Unified Model Context Protocol (guMCP)

guMCP is an open-source collection of Model Context Protocol (MCP) servers that can be run both remotely and locally. The project aims to create the largest collection of MCP servers with a unified backend, fostering a community around AI integrations and the future of AGI.

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Overview](#overview)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [Running Stdio Servers](#running-stdio-servers)
  - [Running SSE Servers](#running-sse-servers)
- [What We're Building](#what-were-building)
- [Features](#features)
- [Current MCP Landscape](#current-mcp-landscape)
- [Client Compatibility](#client-compatibility)
- [Supported Servers and Authentication Methods](#supported-servers-and-authentication-methods)
  - [Authentication Method Summary](#authentication-method-summary)
- [Contributing](#contributing)
- [License](#license)
- [Security](#security)
- [Community](#community)
- [Acknowledgments](#acknowledgments)

## What is MCP?

Model Context Protocol (MCP) is a standardized way for AI models to interact with external tools and services. It allows AI assistants to perform actions like searching the web, accessing databases, or using productivity tools—significantly expanding their capabilities beyond simple text generation.

## Overview

While many MCP server providers are closed source, and open-source alternatives typically only support local hosting through stdio, guMCP provides:

- A comprehensive collection of MCP servers that work both locally and remotely
- Support for both stdio and SSE (Server-Sent Events) transports
- A unified backend architecture for consistent implementation
- Full open-source access to encourage community contributions

## Getting Started

> **🎬 RECOMMENDED: Watch our quick setup video before getting started!** 
> 
> This under 5-minute walkthrough will save you time and help you understand the key concepts.
> 
> [![Watch the guMCP Getting Started Video](https://www.gumloop.com/_next/image?url=%2Fimages%2Fmcp%2FGuideVideo.png&w=1920&q=75)](https://vimeo.com/1070438737/8dea56e6a1)

### Prerequisites

- Python 3.11
- Git
- pip
- For Windows users: A bash-compatible shell is recommended (Git Bash, WSL, etc.)

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/gumloop/guMCP.git
   cd guMCP
   ```

2. **Set up a virtual environment**:

   This isolates the project dependencies from your system Python installation.

   ```bash
   # Create the virtual environment
   python -m venv venv
   
   # Activate it (choose the appropriate command for your OS)
   # On Unix/macOS:
   source venv/bin/activate
   
   # On Windows (Command Prompt):
   venv\Scripts\activate
   
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   
   # On Windows (Git Bash):
   source venv/Scripts/activate
   ```
   
   You'll know your virtual environment is active when you see `(venv)` at the beginning of your command prompt.

3. **Install dependencies**:

   ```bash
   # Install core dependencies
   pip install -r requirements.txt
   
   # Install development dependencies (for contributing)
   pip install -r requirements-dev.txt
   ```

4. **Configure environment variables**:

   ```bash
   # Create a local environment file from the template
   cp .env.example .env
   
   # Open the .env file in your preferred text editor and update values as needed
   # If you're using VS Code:
   code .env
   ```
   
   The `.env` file contains configuration for:
   - API keys for service integrations
   - Authentication settings
   - Server configuration options
   - Development environment settings

5. **Verify installation**:

   ```bash
   # Run a simple test to ensure everything is working
   python -m pytest tests/simple_verify.py
   ```

Now you're ready to start using guMCP! Continue to the Usage section below to learn how to run servers.

## Usage

### Running Stdio Servers

```bash
python src/servers/local.py --server=simple-tools-server
```

For convenience, we also provide a lightweight MCP Client to start and connect to stdio servers. Usage:

```bash
 python tests/clients/LocalMCPTestClient.py --server=simple-tools-server
```

### Running SSE Servers

An SSE server can be run locally. This will provide a single URL and host every server available.

To start the SSE development server, run:

```bash
./start_remote_dev_server.sh
```

For convenience, we also prove a lightweight MCP Client to connect to SSE servers. Usage:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/simple-tools-server/local
```

## What We're Building

guMCP aims to solve several key challenges in the MCP ecosystem:

- **Unified Transport Layer**: We provide a consistent way to run each server via stdio locally or SSE remotely. Unlike existing providers that force you to choose between their hosted SSE service or running stdio locally, guMCP makes it simple to do either with minimal configuration. We're creating an open alternative that's easy to self-host.

- **Standardized Authentication Framework**: We've developed a flexible and generic framework for integration auth across all MCP servers. Current authentication methods vary widely between servers, creating unnecessary complexity. Our unified mechanism uses a base 'AuthClient' across all servers, supporting any arbitrary implementation. For local use, we provide a LocalAuthClient that standardizes integrations and OAuth flows.

- **Flexible Authentication Options**: The GumloopAuthClient lets you use your existing Gumloop credentials *and* you can host servers with your own custom AuthClient or run locally with stdio and local auth as needed.

- **Ready-to-Deploy SSE**: The repository comes ready to deploy with ALL SSE servers accessible under a single URL. If you want to self-host, you can be up and running immediately without complex configuration.

- **Instant Deployment for Contributors**: Open source contributors don't need to worry about DevOps or infrastructure. Your server implementation will be deployed and hosted instantly, making it easier for everyone, regardless of technical background, to bring their ideas to life.

## Features

- **Dual Transport Support**: All servers support both:

  - Local hosting through stdio
  - Remote hosting through SSE

- **Unified Backend**: Consistent implementation patterns across all servers

- **Extensive Server Collection**: Including servers for:
  - File systems and databases
  - Development tools
  - Web and browser automation
  - Productivity and communication
  - AI and specialized tools

## Current MCP Landscape

The MCP ecosystem is evolving rapidly with varying levels of implementation:

- **MCP Client capabilities vary**: Different AI assistants have different MCP Client capabilities. Anthropic's Claude can use MCP servers through Claude Desktop, but not the web client. ChatGPT has announced support, but has not announced a timeline. Cursor has robust support for our remote servers.

- **Authentication Challenges**: Currently, authentication methods vary widely between services. Some use API keys, others require OAuth flows, and many have unique authentication requirements that make standardization difficult. We're looking to solve this using Gumloop's authentication layer, but this requires more work for a smooth experience on Claude Desktop.

- **Integration Complexity**: Some integrations use API keys, like Perplexity and are straightforward to implement, requiring simple API calls. Others, such as Google Drive or GitHub, require more complex OAuth authentication flows and permission handling.

## Client Compatibility

- **Cursor Integration**: Tools like Cursor can easily leverage Gumloop's remote authentication layers, allowing seamless connection to our MCP servers without additional setup. This client works exceptionally well with the integrations on https://www.gumloop.com/mcp

- **Claude Desktop**: For Claude Desktop users, we're developing an adapter that will enable connection to guMCP servers. This is currently in development and will be released soon. For now, intgrations vary in complexity from simple copy-pasting of API keys all the way through configuring new oauth connections in GCP. We aim to improve support here dramatically.

## Supported Servers and Authentication Methods

The following table provides an overview of the current servers implemented in guMCP, their authentication requirements, and relative ease of use with different authentication methods:

| Server | Auth Type | Remote Auth<br>(e.g., Cursor) | Local Auth<br>(e.g., Claude Desktop) | Documentation |
|--------|-----------|-------------------------------|--------------------------------------|---------------|
| **Google Services** | | | | |
| Google Sheets | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/gsheets) | ⚠️ Complex - Requires GCP project & OAuth setup | [GSheets Docs](/src/servers/gsheets/README.md) |
| Gmail | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/gmail) | ⚠️ Complex - Requires GCP project & OAuth setup | [Gmail Docs](/src/servers/gmail/README.md) |
| Google Docs | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/gdocs) | ⚠️ Complex - Requires GCP project & OAuth setup | [GDocs Docs](/src/servers/gdocs/README.md) |
| Google Drive | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/gdrive) | ⚠️ Complex - Requires GCP project & OAuth setup | [GDrive Docs](/src/servers/gdrive/README.md) |
| Google Calendar | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/gcalendar) | ⚠️ Complex - Requires GCP project & OAuth setup | [GCalendar Docs](/src/servers/gcalendar/README.md) |
| **Communication Tools** | | | | |
| Slack | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/slack) | ⚠️ Complex - Requires OAuth setup with HTTPS redirect | [Slack Docs](/src/servers/slack/README.md) |
| Outlook | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/outlook) | ⚠️ Complex - Requires Azure app registration | [Outlook Docs](/src/servers/outlook/README.md) |
| **Productivity Tools** | | | | |
| Airtable | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/airtable) | ⚠️ Complex - Requires Airtable OAuth application | [Airtable Docs](/src/servers/airtable/README.md) |
| Linear | OAuth 2.0 | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/linear) | ⚠️ Complex - Requires Linear developer setup | [Linear Docs](/src/servers/linear/README.md) |
| Attio | Mixed | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/attio) | ⚠️ Moderate - Depends on auth method used | [Attio Docs](/src/servers/attio/README.md) |
| **Search Tools** | | | | |
| Perplexity | API Key | [✅ Seamless with Gumloop auth](https://www.gumloop.com/mcp/perplexity) | ✅ Easy - Simple API key setup | [Perplexity Docs](/src/servers/perplexity/README.md) |

### Authentication Method Summary

- **Remote Auth** (used by clients like Cursor): 
  - Uses Gumloop's authentication layer
  - Works seamlessly with all servers
  - Requires minimal setup from users
  - Handles complex OAuth flows behind the scenes

- **Local Auth** (used by clients like Claude Desktop): 
  - API key-based services (like Perplexity) are simple to configure and use
  - OAuth-based services require significant local setup, including creating developer applications and configuring OAuth flows
  - We're developing an adapter to simplify Claude Desktop connections to guMCP servers


## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.MD) for guidelines.

Key areas for contribution:

- New server implementations
- Transport improvements
- Documentation
- Test coverage
- Bug fixes

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](LICENSE) file for details.

## Security

Security is the single highest priority for us.

That's why [Gumloop is SOC 2 Type II, GDPR, and HIPAA compliant](https://trust.gumloop.com/), and why for this OSS repo, we're actively rewarding those who responsibly disclose serious vulnerabilities and exploits to security@gumloop.com.

## Community

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and discussions
- [Forum](https://forum.gumloop.com/): Community discussions and support

## Acknowledgments

This project builds on the Model Context Protocol (MCP) specification and is inspired by the work of various MCP implementations in the community, especially those at Anthropic.

Thank you to all the contributors that have provided feedback, advice, and early servers for the repository.
