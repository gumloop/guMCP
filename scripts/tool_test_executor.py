import os
import sys
import json
import re
import asyncio
import importlib.util
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def get_raw_response(result):
    """Extract raw text response from the tool result"""
    if hasattr(result, 'content') and len(result.content) > 0:
        if hasattr(result.content[0], 'text'):
            return result.content[0].text
    return str(result)


def get_test_configs(server_name):
    """Get test configs for a specific server"""
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
    
    return getattr(module, "TOOL_TESTS", None)


def format_args(args_template, context):
    """Format args template with context values"""
    if not args_template:
        return {}
        
    args_str = args_template.format(**context)
    args_dict = {}
    pattern = r'(\w+)=(?:"([^"]*)"|\{([^}]*)\}|([^,\s]*))'
    
    for match in re.finditer(pattern, args_str):
        key = match.group(1)
        value = next((g for g in match.groups()[1:] if g is not None), "")
        
        if value.lower() == "true":
            args_dict[key] = True
        elif value.lower() == "false":
            args_dict[key] = False
        elif value.isdigit():
            args_dict[key] = int(value)
        else:
            args_dict[key] = value
                
    return args_dict


async def run_server_tools(server_name):
    """Run tools for a single server based on test configurations"""
    test_configs = get_test_configs(server_name)
    if not test_configs:
        return
    
    local_script_path = os.path.join(project_root, "src", "servers", "local.py")
    if not os.path.exists(local_script_path):
        return
    
    command = "python"
    args = [local_script_path, "--server", server_name]
    server_params = StdioServerParameters(command=command, args=args, env=None)
    
    tools_log = []
    context = {}
    
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            await session.initialize()
            
            response = await session.list_tools()
            available_tools = {tool.name: tool for tool in response.tools}
            
            # Sort by dependencies
            sorted_configs = sorted(test_configs, 
                                   key=lambda x: len(x.get("depends_on", [])))
            
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
                if "args" in test_config:
                    args = test_config["args"]
                elif "args_template" in test_config:
                    try:
                        args = format_args(test_config["args_template"], context)
                    except Exception:
                        continue
                else:
                    args = {}
                
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
    
    # Save results to file
    logs_dir = os.path.join(project_root, "./scripts/logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    output_file = os.path.join(logs_dir, f"{server_name}.json")
    with open(output_file, "w") as f:
        json.dump(tools_log, f, indent=2)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Auto Tool Response Generator")
    parser.add_argument(
        "server", help="Server name to test (e.g., word)"
    )
    
    args = parser.parse_args()
    asyncio.run(run_server_tools(args.server))
