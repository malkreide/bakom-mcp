"""Zugriff auf den Context, den die Live-Tests an die Tools reichen.

Die Tools erwarten seit dem Lifespan-Refactor `(params, ctx)`. Den `ctx` baut
die Fixture `live_ctx` in `conftest.py` — aus dem echten `lifespan(mcp)`, damit
Timeout, User-Agent und Egress-Allowlist exakt der Produktion entsprechen und
nicht in einer handgeschriebenen Fixture nochmal behauptet werden.

Die Live-Tests sind einfache `async def`-Funktionen ohne Fixture-Parameter.
Statt 66 Signaturen umzuschreiben, hinterlegt die Fixture den Context hier und
die Tests holen ihn mit `ctx()`.
"""

from __future__ import annotations

from typing import Any

_current: Any | None = None


def set_ctx(ctx: Any | None) -> None:
    """Von der `live_ctx`-Fixture gesetzt — pro Test einer, danach None."""
    global _current
    _current = ctx


def ctx() -> Any:
    """Der Context des laufenden Live-Tests."""
    if _current is None:
        raise RuntimeError(
            "Kein Live-Context aktiv. ctx() ist nur in Tests der Live-Module "
            "nutzbar, denen conftest.py die Fixture `live_ctx` anhaengt."
        )
    return _current
