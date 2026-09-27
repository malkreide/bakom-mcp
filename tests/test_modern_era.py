"""Spec 2026-07-28 nativ: was der Server in der Envelope-Aera tatsaechlich tut.

`test_protocol_version.py` haelt fest, WELCHE Revisionen das SDK spricht. Das
sagt nichts darueber, ob dieser Server sie ohne Altlasten bedient — die
Zusicherungen hier fahren deshalb echte Verbindungen, keine Mocks. Ein
`AsyncMock` als `ctx` nimmt jeden Aufruf an, auch einen deprecated; genau so
blieb `ctx.info()` unbemerkt, dessen Zeile in der modernen Aera ohne Opt-in
still verschwand.
"""

from __future__ import annotations

import ast
import pathlib
import warnings
from typing import Any

import httpx
import pytest
from mcp import Client
from mcp.shared.exceptions import MCPDeprecationWarning
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
)

from bakom_mcp import __version__
from bakom_mcp.server import build_http_app, mcp

REPO = pathlib.Path(__file__).resolve().parents[1]
MODERN = "2026-07-28"

# Ausserhalb der Schweiz: das Werkzeug weist die Standorte selbst ab und
# beruehrt kein Netz, meldet aber fuer jeden Fortschritt.
_AUSSERHALB = {
    "params": {
        "locations": [
            {"name": "Nordpol", "latitude": 89.0, "longitude": 0.0},
            {"name": "Suedpol", "latitude": -89.0, "longitude": 0.0},
        ]
    }
}


@pytest.mark.parametrize("mode", ["legacy", MODERN])
async def test_der_fortschrittstext_erreicht_beide_aeren(mode: str) -> None:
    """Ohne `log_level`-Opt-in — so, wie ein Client ueblicherweise anfragt."""
    meldungen: list[str | None] = []

    async def mitschreiben(progress: float, total: float | None, message: str | None) -> None:
        meldungen.append(message)

    with warnings.catch_warnings(record=True) as gefangen:
        warnings.simplefilter("always")
        async with Client(mcp, mode=mode) as client:
            result = await client.call_tool(
                "bakom_multi_standort_konnektivitaet",
                _AUSSERHALB,
                progress_callback=mitschreiben,
            )

    assert not result.is_error
    assert len(meldungen) == 3, meldungen
    assert all(meldungen), f"Fortschritt ohne Text: {meldungen}"
    assert "Nordpol" in (meldungen[0] or "")
    veraltet = [str(w.message) for w in gefangen if issubclass(w.category, MCPDeprecationWarning)]
    assert not veraltet, f"deprecated seit Spec {MODERN}: {veraltet}"


# Die Kontext-Methoden, die SEP-2577 mit der Logging-Faehigkeit deprecated.
_LOGGING_METHODEN = {"log", "debug", "info", "warning", "error", "send_log_message"}


def test_kein_werkzeug_schreibt_ueber_den_logging_kanal() -> None:
    """Statisch, weil eine Deprecation-Warnung nur auf dem Pfad feuert, der lief.

    Geprueft wird jeder Aufruf `ctx.<methode>(…)` bzw. `….session.<methode>(…)`
    im ausgelieferten Code. Das Python-`logger` des Servers ist davon nicht
    betroffen — es heisst nicht `ctx` und schreibt nach stderr, nicht an den
    Client.
    """
    funde = []
    for pfad in sorted((REPO / "src").rglob("*.py")):
        for node in ast.walk(ast.parse(pfad.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            ziel = node.func.value
            name = ziel.id if isinstance(ziel, ast.Name) else getattr(ziel, "attr", "")
            if name in {"ctx", "session"} and node.func.attr in _LOGGING_METHODEN:
                funde.append(f"{pfad.relative_to(REPO)}:{node.lineno} {name}.{node.func.attr}")
    assert not funde, f"Logging ist ab Spec {MODERN} deprecated (SEP-2577): {funde}"


_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Host": "127.0.0.1:8050",
    "Mcp-Protocol-Version": MODERN,
}

_META = {
    PROTOCOL_VERSION_META_KEY: MODERN,
    CLIENT_INFO_META_KEY: {"name": "bakom-mcp-test", "version": "0"},
    CLIENT_CAPABILITIES_META_KEY: {},
}


async def _modern_post(
    method: str, params: dict[str, Any], name: str | None = None
) -> httpx.Response:
    """Eine einzelne 2026-07-28-Anfrage durch den zusammengebauten ASGI-Stack."""
    app = build_http_app("127.0.0.1", 8050)
    headers = {**_HEADERS, "Mcp-Method": method}
    if name is not None:
        headers["Mcp-Name"] = name
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {**params, "_meta": _META}}
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8050"
        ) as client:
            return await client.post("/mcp", json=body, headers=headers)


async def test_discover_nennt_die_paketversion() -> None:
    """Das SDK meldet ohne `version=` einen leeren String."""
    response = await _modern_post("server/discover", {})
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert MODERN in result["supportedVersions"]
    info = result["_meta"]["io.modelcontextprotocol/serverInfo"]
    assert info["version"] == __version__, info


async def test_der_handshake_nennt_dieselbe_paketversion() -> None:
    async with Client(mcp, mode="legacy") as client:
        info = client.session.server_info
    assert info is not None
    assert info.version == __version__


async def test_ein_werkzeugaufruf_braucht_keine_sitzung() -> None:
    """Die Envelope-Aera ist zustandslos: kein `initialize`, keine `Mcp-Session-Id`.

    `bakom_breitbandatlas_datensaetze` ist ein statischer Katalog und beruehrt
    kein Netz — die Antwort zeigt also nur, was der Transport tut.
    """
    response = await _modern_post(
        "tools/call",
        {"name": "bakom_breitbandatlas_datensaetze", "arguments": {"params": {}}},
        name="bakom_breitbandatlas_datensaetze",
    )
    assert response.status_code == 200, response.text
    assert "mcp-session-id" not in response.headers
    result = response.json()["result"]
    assert result.get("isError") is not True, result
    assert result["content"][0]["text"].strip()
