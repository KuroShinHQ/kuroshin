#!/usr/bin/env python3
"""
🔱 KUROSHIN ECHO MCP SERVER
Model Context Protocol server that provides a simple echo functionality
for testing Kuroshin Empire's MCP integration.
"""

import asyncio
import logging
from typing import Any, Sequence

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.server.stdio
import mcp.types as types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kuroshin-echo")

# Create a MCP server instance
server = Server("kuroshin-echo")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for the Kuroshin Empire."""
    return [
        types.Tool(
            name="echo",
            description="🔱 Kuroshin Empire Echo Tool - Returns the message with imperial prefix",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to echo back with Kuroshin prefix"
                    }
                },
                "required": ["message"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Handle tool execution requests."""
    if name != "echo":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments or "message" not in arguments:
        raise ValueError("Missing required 'message' argument")
    
    message = arguments["message"]
    
    # Add Kuroshin Empire prefix
    echo_response = f"🔱 [KUROSHIN_ECHO]: {message}"
    
    logger.info(f"Echo tool called with message: {message}")
    
    return [
        types.TextContent(
            type="text", 
            text=echo_response
        )
    ]

async def main():
    """Main entry point for the Kuroshin Echo MCP server."""
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="kuroshin-echo",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())