import os
import sys
import json
import re
import asyncio
import importlib.util
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_raw_response(result):
    """Extract raw text response from the tool result"""
    if hasattr(result, "content") and len(result.content) > 0:
        if hasattr(result.content[0], "text"):
            return result.content[0].text
    return str(result)


def load_test_module(server_name):
    """Load the test module for a specific server"""
    test_file = project_root / "tests" / "servers" / server_name / "tests.py"

    if not test_file.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        f"tests.servers.{server_name}.tests", test_file
    )
    if not (spec and spec.loader):
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def format_args(args_template, context):
    """Format args template with context values"""
    if not args_template:
        return {}

    args_str = args_template.format(**context)
    args_dict = {}

    # Handle complex JSON structures in args
    try:
        # Extract key-value pairs with proper JSON handling
        pattern = r'(\w+)=(?:"([^"]*)"|\{([^}]*)\}|\[([^\]]*)\]|([^,\s]*))'

        for match in re.finditer(pattern, args_str):
            key = match.group(1)
            value = next((g for g in match.groups()[1:] if g is not None), "")

            # Try to parse JSON for complex structures
            if value.startswith("{") and value.endswith("}"):
                try:
                    value = json.loads(value.replace("'", '"'))
                except json.JSONDecodeError:
                    pass
            elif value.startswith("[") and value.endswith("]"):
                try:
                    value = json.loads(value.replace("'", '"'))
                except json.JSONDecodeError:
                    pass
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)

            args_dict[key] = value
    except Exception as e:
        logger.error(f"Error parsing args: {e}")
        return {}

    return args_dict


async def run_test_configs(session, configs, context, tools_log, available_tools):
    """Run a set of test configurations"""
    if not configs:
        return

    # Sort by dependencies
    sorted_configs = sorted(configs, key=lambda x: len(x.get("depends_on", [])))

    for test_config in sorted_configs:
        tool_name = test_config["name"]

        if tool_name not in available_tools or test_config.get("skip", False):
            continue

        # Check dependencies
        if any(dep not in context for dep in test_config.get("depends_on", [])):
            continue

        # Setup context if needed
        if "setup" in test_config and callable(test_config["setup"]):
            setup_result = test_config["setup"](context)
            if isinstance(setup_result, dict):
                context.update(setup_result)

        # Get args
        args = {}
        if "args" in test_config:
            args = test_config["args"]
        elif "args_template" in test_config:
            try:
                args = format_args(test_config["args_template"], context)
            except Exception as e:
                logger.error(f"Error formatting args for {tool_name}: {e}")
                continue

        try:
            result = await session.call_tool(tool_name, args)
            raw_response = get_raw_response(result)
            tools_log.append({tool_name: raw_response})

            # Extract values using regex extractors
            if "regex_extractors" in test_config:
                for key, pattern in test_config["regex_extractors"].items():
                    match = re.search(pattern, raw_response, re.DOTALL | re.IGNORECASE)
                    if match and match.groups():
                        context[key] = match.group(1).strip()
        except Exception as e:
            tools_log.append({tool_name: {"error": str(e)}})
            logger.error(f"Error executing {tool_name}: {e}")


async def run_server_tools(server_name):
    """Run tools for a single server based on test configurations"""
    module = load_test_module(server_name)
    if not module:
        logger.error(f"No test module found for server: {server_name}")
        return

    tool_tests = getattr(module, "TOOL_TESTS", [])
    resource_tests = getattr(module, "RESOURCE_TESTS", [])

    if not tool_tests and not resource_tests:
        logger.error(f"No test configurations found for server: {server_name}")
        return

    local_script_path = project_root / "src" / "servers" / "local.py"
    if not local_script_path.exists():
        logger.error(f"Local script not found: {local_script_path}")
        return

    command = "python"
    args = [str(local_script_path), "--server", server_name]
    server_params = StdioServerParameters(command=command, args=args, env=None)

    tools_log = []
    context = {}

    logger.info(f"Running tests for server: {server_name}")

    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            await session.initialize()

            response = await session.list_tools()
            available_tools = {tool.name: tool for tool in response.tools}

            # Run resource tests first
            if resource_tests:
                logger.info(f"Running {len(resource_tests)} resource tests")
                await run_test_configs(
                    session, resource_tests, context, tools_log, available_tools
                )

            # Then run tool tests
            if tool_tests:
                logger.info(f"Running {len(tool_tests)} tool tests")
                await run_test_configs(
                    session, tool_tests, context, tools_log, available_tools
                )

    # Save results to file
    logs_dir = project_root / "scripts" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    output_file = logs_dir / f"{server_name}.json"
    with open(output_file, "w") as f:
        json.dump(tools_log, f, indent=2)

    logger.info(f"Test results saved to: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Tool Test Executor")
    parser.add_argument("server", help="Server name to test (e.g., word, excel)")

    args = parser.parse_args()
    asyncio.run(run_server_tools(args.server))
