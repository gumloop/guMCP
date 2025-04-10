import argparse
import traceback
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

from anthropic import Anthropic
from dotenv import load_dotenv

from mcp import ClientSession
from mcp.client.sse import sse_client

load_dotenv()


class RemoteMCPTestClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_server(self, sse_endpoint: str):
        """Connect to a remote MCP server via SSE

        Args:
            sse_endpoint: Full SSE endpoint URL (e.g., "http://localhost:8000/simple-tools-server")
        """
        print(f"Connecting to server at {sse_endpoint}")

        read_stream, write_stream = await self.exit_stack.enter_async_context(
            sse_client(sse_endpoint)
        )

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        print("Initializing Client Session...")
        await self.session.initialize()
        print("Session initialized!")

        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def list_resources(self) -> None:
        """List all available resources from the server"""
        if not self.session:
            raise ValueError("Session not initialized")

        try:
            return await self.session.list_resources()
        except Exception as e:
            print(f"Error listing resources: {e}")
            print(f"Stacktrace: {traceback.format_exc()}")

    async def read_resource(self, uri: str) -> None:
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

        if self.session is None:
            raise ValueError("Session not initialized")

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

                print(f"Tool Call Result: {result}")

                assistant_message_content.append(content)
                messages.append(
                    {"role": "assistant", "content": assistant_message_content}
                )
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content,
                            }
                        ],
                    }
                )

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools,
                )

                if (
                    response.content
                    and len(response.content) > 0
                    and hasattr(response.content[0], "text")
                ):
                    final_text.append(response.content[0].text)
                else:
                    for content_item in result.content:
                        if hasattr(content_item, "text"):
                            final_text.append(content_item.text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nRemote MCP Client Started!")
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


async def main():
    parser = argparse.ArgumentParser(description="Remote MCP Test Client")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/simple-tools-server/session_key",
        help="Endpoint URL for the MCP server",
    )

    args = parser.parse_args()

    client = RemoteMCPTestClient()
    try:
        await client.connect_to_server(args.endpoint)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
