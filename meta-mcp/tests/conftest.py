"""Make the ``src/`` layout importable without installing the package.

The Meta Ads MCP runs straight from ``src/`` (no pyproject/editable install),
so these tests put ``src/`` on ``sys.path``. ``meta_mcp.client`` imports only the
stdlib + ``httpx`` at module load time (the FastMCP request-context import is
lazy, inside ``get_token``), so the date/window builder is importable without a
live server.
"""

import os
import sys

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
