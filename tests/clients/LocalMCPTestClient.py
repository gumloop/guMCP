import os

from asyncio import StreamReader, StreamWriter
from contextlib import AsyncExitStack

from typing import Optional, Dict, Any, List

from mcp.types import AnyUrl, ListResourcesResult, ReadResourceResult
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class LocalMCPTestClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.stdio: Optional[StreamReader] = None
        self.write: Optional[StreamWriter] = None

    async def connect_to_server_by_name(self, server_name: str):
        """Connect to an MCP server by name using local.py

        Args:
            server_name: Name of the server (e.g., simple-tools-server, slack)
        """
        current_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        local_script_path = os.path.join(current_dir, "src", "servers", "local.py")

        if not os.path.exists(local_script_path):
            raise ValueError(f"Could not find local.py at {local_script_path}")

        command = "python"
        args = [local_script_path, "--server", server_name]

        server_params = StdioServerParameters(command=command, args=args, env=None)

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def list_resources(self) -> ListResourcesResult:
        """List all available resources from the server"""
        if not self.session:
            raise ValueError("Session not initialized")

        try:
            return await self.session.list_resources()
        except Exception as e:
            print(f"Error listing resources: {e}")

    async def read_resource(self, uri: AnyUrl) -> ReadResourceResult:
        """Read a specific resource from the server

        Args:
            uri: URI of the resource to read
        """
        if not self.session:
            raise ValueError("Session not initialized")

        try:
            return await self.session.read_resource(uri)
        except Exception as e:
            print(f"Error reading resource: {e}")

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages: List[Dict[str, Any]] = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []
        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                assistant_message_content.append(content)
                messages.append(
                    {"role": "assistant", "content": assistant_message_content}
                )

                tool_result_content: Dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": content.id,
                    "content": result.content,
                }

                messages.append({"role": "user", "content": [tool_result_content]})

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools,
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        # TODO: Fix errors during cleanup when running test clients
        try:
            # Close the session first if it exists
            if self.session:
                # Create a detached task for session cleanup if needed
                if hasattr(self.session, "close"):
                    await self.session.close()
                self.session = None

            # Then close the exit stack
            if self.exit_stack:
                # Manually close each context in the stack to avoid task context issues
                while True:
                    try:
                        # Pop and close each context manager one by one
                        cm = self.exit_stack._exit_callbacks.pop()
                        await cm(None, None, None)
                    except IndexError:
                        # No more callbacks
                        break
                    except Exception as e:
                        print(f"\nError during cleanup: {e}")
        except Exception as e:
            print(f"Cleanup error: {e}")
