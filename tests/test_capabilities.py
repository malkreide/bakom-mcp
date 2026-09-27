"""Was der Server ankündigt, muss er auch halten.

Zwei Zusicherungen, beide aus portfolioweiten Befunden vom 27.9.2026:

* **Änderungsmeldungen.** Unter Spec `2026-07-28` leitet das SDK
  `resources.subscribe` und die drei `listChanged` allein daraus ab, ob
  `subscriptions/listen` registriert ist — `MCPServer` registriert es immer.
  Dieser Server ändert zur Laufzeit keine Liste, also muss er `false` melden
  und `subscriptions/listen` ablehnen.
* **Ausgabeschema.** Aus `-> str` leitet das SDK `outputSchema
  {"result": string}` ab. Die Tools liefern Text (Markdown oder JSON-Text), das
  Schema verspräche eine Struktur, die es nicht gibt.

Je eine Negativkontrolle mit einem nackten `MCPServer` hält fest, dass das SDK
den Default noch hat. Fällt sie, ist der Eingriff hier überflüssig geworden und
gehört zurückgebaut — nicht die Zusicherung gelockert.
"""

from __future__ import annotations

from typing import Any

import anyio
import httpx
import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
)

from bakom_mcp.server import build_http_app, mcp

MODERN = "2026-07-28"


async def _capabilities(server: MCPServer, mode: str) -> dict[str, Any]:
    async with Client(server, mode=mode) as client:
        await client.list_tools()
        caps = client.session.server_capabilities
    assert caps is not None
    return caps.model_dump(exclude_none=True, by_alias=True)


def _aenderungsflags(caps: dict[str, Any]) -> dict[str, bool]:
    return {
        "tools.listChanged": caps["tools"]["listChanged"],
        "prompts.listChanged": caps["prompts"]["listChanged"],
        "resources.listChanged": caps["resources"]["listChanged"],
        "resources.subscribe": caps["resources"]["subscribe"],
    }


# `auto` fragt `server/discover` ab und landet in der Envelope-Ära; ein
# Versions-Pin würde das Discover-Ergebnis nur synthetisieren und damit die
# Fähigkeiten des Clients messen statt die des Servers.
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_der_server_kuendigt_keine_aenderungsmeldungen_an(mode: str) -> None:
    caps = await _capabilities(mcp, mode)
    flags = _aenderungsflags(caps)
    assert not any(flags.values()), f"{mode}: {flags}"


async def test_negativkontrolle_das_sdk_meldet_sie_von_sich_aus() -> None:
    caps = await _capabilities(MCPServer("kontrolle", tools=[]), "auto")
    # Ein Server ohne Ressourcen/Prompts meldet nur `tools`.
    assert caps["tools"]["listChanged"] is True, caps


_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Host": "127.0.0.1:8050",
    "Mcp-Protocol-Version": MODERN,
    "Mcp-Method": "subscriptions/listen",
}

_META = {
    PROTOCOL_VERSION_META_KEY: MODERN,
    CLIENT_INFO_META_KEY: {"name": "bakom-mcp-test", "version": "0"},
    CLIENT_CAPABILITIES_META_KEY: {},
}


async def test_subscriptions_listen_wird_abgelehnt() -> None:
    """Durch die zusammengebaute ASGI-App: kein offener Strom ohne Ereignisse."""
    app = build_http_app("127.0.0.1", 8050)
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "subscriptions/listen",
        "params": {"_meta": _META, "notifications": {"toolsListChanged": True}},
    }
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8050"
        ) as client:
            # Mit registriertem Handler öffnet die Anfrage einen SSE-Strom, der
            # nie endet — ohne Schranke hinge der Test, statt zu fallen.
            with anyio.fail_after(5):
                response = await client.post("/mcp", json=body, headers=_HEADERS)
    assert "text/event-stream" not in response.headers.get("content-type", "")
    assert response.json()["error"]["code"] == -32601, response.text


async def test_kein_tool_meldet_ein_ausgabeschema() -> None:
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
    assert len(tools) == 12
    mit_schema = {t.name: t.output_schema for t in tools if t.output_schema}
    assert not mit_schema, mit_schema


async def test_ein_werkzeugaufruf_liefert_nur_text() -> None:
    """`bakom_breitbandatlas_datensaetze` ist statisch und berührt kein Netz."""
    async with Client(mcp) as client:
        result = await client.call_tool("bakom_breitbandatlas_datensaetze", {"params": {}})
    assert not result.is_error
    assert result.structured_content is None
    assert result.content[0].text.strip()


async def test_negativkontrolle_str_bekommt_sonst_ein_schema() -> None:
    kontrolle = MCPServer("kontrolle")

    @kontrolle.tool()
    async def echo(text: str) -> str:
        return text

    async with Client(kontrolle) as client:
        tool = (await client.list_tools()).tools[0]
    assert tool.output_schema is not None
    assert "result" in tool.output_schema["properties"]
