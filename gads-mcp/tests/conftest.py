"""Make the ``src/`` layout importable without installing the package.

The Google Ads MCP runs straight from ``src/`` (no pyproject/editable install),
so these tests put ``src/`` on ``sys.path``. ``gads_mcp.client`` imports only the
stdlib at module load time (the ``google.ads`` imports are lazy, inside
functions), so the query-builder is importable without credentials or the
``google-ads`` package present.
"""

import os
import sys

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
