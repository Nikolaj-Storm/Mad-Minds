"""stdio entrypoint for Claude Desktop:  python -m ga4_mcp

Claude Desktop launches MCP servers over stdio. Register this in
claude_desktop_config.json (see README) with the marketer's Google OAuth env vars.
"""
from ga4_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()  # default stdio transport
