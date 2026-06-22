"""Make the ``src/`` layout importable without installing the package.

The Meta Ads MCP runs straight from ``src/`` (no pyproject/editable install),
so these tests put ``src/`` on ``sys.path``. ``meta_ads_mcp.client`` imports only
the stdlib at module load time (the ``facebook_business`` imports are lazy,
inside functions), so the time-range builder is importable without the
``facebook-business`` package present.
"""

import os
import sys

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
