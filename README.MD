# Gumloop Unified Model Context Protocol (guMCP)

guMCP is an open-source collection of Model Context Protocol (MCP) servers that can be run both remotely and locally. The project aims to create the largest collection of MCP servers with a unified backend, fostering a community around AI integrations and the future of AGI.

## Overview

While many MCP server providers are closed source, and open-source alternatives typically only support local hosting through stdio, guMCP provides:

- A comprehensive collection of MCP servers that work both locally and remotely
- Support for both stdio and SSE (Server-Sent Events) transports
- A unified backend architecture for consistent implementation
- Full open-source access to encourage community contributions

## What We're Building

guMCP aims to solve several key challenges in the MCP ecosystem:

- **Unified Transport Layer**: We provide a consistent way to run each server via stdio locally or SSE remotely. Unlike existing providers that force you to choose between their hosted SSE service or running stdio locally, guMCP makes it simple to do either with minimal configuration. While options like Zapier's MCP are closed source, we're creating an open alternative that's easy to self-host.

- **Standardized Authentication Framework**: We've developed a flexible and generic framework for integration auth across all MCP servers. Current authentication methods vary widely between servers, creating unnecessary complexity. Our unified mechanism uses a base 'AuthClient' across all servers, supporting any arbitrary implementation. For local use, we provide a LocalAuthClient that standardizes integrations and OAuth flows.

- **Flexible Authentication Options**: The GumloopAuthClient lets you use your existing Gumloop credentials, similar to how Zapier or Composio handle MCP server authentication. The key difference is flexibility—you can host servers with your own custom AuthClient or run locally with stdio and local auth as needed.

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

## Getting Started

[![Watch the video](https://www.gumloop.com/_next/image?url=%2Fimages%2Fmcp%2FGuideVideo.png&w=1920&q=75)](https://vimeo.com/1070438737/8dea56e6a1)

### Prerequisites

- Python 3.11
- Git

### Installation

1. Clone the repository:

```bash
git clone https://github.com/gumloop/guMCP.git
cd guMCP
```

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
venv\Scripts\activate     # On Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Set up environment variables:

```bash
cp .env.example .env  # Then edit with your configuration
```

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
