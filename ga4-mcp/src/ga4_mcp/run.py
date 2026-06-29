"""ASGI entrypoint for the streamable-HTTP transport (the Mad-Minds stack).

    uvicorn ga4_mcp.run:app --host 0.0.0.0 --port 8000

If the repo fronts marketer connectors with a shared OAuth/auth middleware, pass it
via ``middleware=[...]`` here (the same place ``gads-mcp`` wires its gate). For
Claude Desktop use the stdio entrypoint instead: ``python -m ga4_mcp``.
"""
from ga4_mcp.server import mcp

app = mcp.http_app(path="/mcp")
