"""bakom-mcp: MCP Server für BAKOM Open Data (Bundesamt für Kommunikation)."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

try:
    # Read the version from the installed distribution metadata, which is built
    # from pyproject.toml. The hand-maintained literal here said 1.0.0 while the
    # package had moved on to 2.0.3 — a full major version — and the User-Agent
    # in server.py carried "bakom-mcp/1.0" to the BAKOM endpoints all the while.
    # A value nobody has to remember to bump cannot go stale.
    __version__ = _distribution_version("bakom-mcp")
except PackageNotFoundError:
    # Source tree without an install. Deliberately not a plausible-looking
    # number: an obviously non-release marker beats a wrong version on the wire.
    __version__ = "0.0.0+source"
__author__ = "malkreide"
__license__ = "MIT"
