"""Pytest-Fixtures fuer bakom-mcp.

Die Live-Tests stehen in `test_live.py` und tragen dort `pytestmark =
pytest.mark.live`. Die CI ruft `pytest -m "not live"`,
`.github/workflows/live-tests.yml` ruft `pytest -m live`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bakom_mcp.server import lifespan, mcp  # noqa: E402


@pytest.fixture
async def live_ctx():
    """Context fuer einen Live-Test, aus dem echten `lifespan(mcp)`.

    Bewusst nicht handgeschrieben: Timeout, User-Agent und die
    Egress-Allowlist kommen so aus derselben Quelle wie im Betrieb. Der Client
    wird pro Test geoeffnet und wieder geschlossen.
    """
    async with lifespan(mcp) as app_ctx:
        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx
        ctx.info = AsyncMock()
        ctx.report_progress = AsyncMock()
        yield ctx
