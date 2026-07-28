"""Guards against the version drift that made the User-Agent lie.

The literal in `server.py` read `bakom-mcp/1.0` while the package was at 2.0.3
— a full major version — and `__init__.__version__` said 1.0.0. Every request
to the BAKOM endpoints carried the stale value (`server.py:140`).

These tests fail if anyone reintroduces a literal.
"""

import tomllib
from pathlib import Path

import bakom_mcp
from bakom_mcp import server

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _pyproject_version() -> str:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


def test_version_matches_pyproject():
    assert bakom_mcp.__version__ == _pyproject_version()


def test_user_agent_carries_the_real_version():
    expected = f"bakom-mcp/{_pyproject_version()} (+https://github.com/malkreide/bakom-mcp)"
    assert server.HTTP_USER_AGENT == expected


def test_user_agent_is_not_a_source_checkout_marker():
    assert "+source" not in server.HTTP_USER_AGENT
