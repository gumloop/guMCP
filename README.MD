# Gumloop Unified Model Context Protocol (guMCP)

guMCP is an open-source collection of Model Context Protocol (MCP) servers that can be run both remotely and locally. The project aims to create the largest collection of MCP servers with a unified backend, fostering a community around AI integrations and the future of AGI.

## Overview

While many MCP server providers are closed source, and open-source alternatives typically only support local hosting through stdio, guMCP provides:

- A comprehensive collection of MCP servers that work both locally and remotely
- Support for both stdio and SSE (Server-Sent Events) transports
- A unified backend architecture for consistent implementation
- Full open-source access to encourage community contributions

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

### Running Servers Locally (stdio)

```bash
python tests/servers/test_runner.py --server=simple-tools-server
```

### Running Servers Remotely (SSE)

1. Start the remote development server:

```bash
./start_remote_dev_server.sh
```

2. Run tests:

```bash
python tests/servers/test_runner.py --server=simple-tools-server --remote
```

### Testing with Hosted Servers

```bash
python tests/servers/test_runner.py --server=simple-tools-server --remote --endpoint=https://mcp.gumloop.com/gdrive/{user_id}%3A{api_key}
```

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Key areas for contribution:

- New server implementations
- Transport improvements
- Documentation
- Test coverage
- Bug fixes

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](LICENSE) file for details.

## Security

Security is the single highest priority for us. That's why [Gumloop is SOC 2 Type II and HIPAA compliant](https://trust.gumloop.com/), and why for this OSS repo, we've actively reward those who quitely disclose serious vulnerabilities and exploits to security@gumloop.com.

## Community

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and discussions
- [Forum](https://forum.gumloop.com/): Community discussions and support

## Acknowledgments

This project builds on the Model Context Protocol (MCP) specification and is inspired by the work of various MCP implementations in the community, especially those at Anthropic.

Thank you to all the contributors that have provided feedback, advice, and early servers for the repository.
