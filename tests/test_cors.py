"""SDK-004: Die CORS-Freigabeliste nennt jetzt Header statt einer Wildcard.

`allow_headers` stand auf `["*"]`. Starlette schaltet damit intern auf
`allow_all_headers` und spiegelt im Preflight zurück, was der Browser
ankündigt — jeder erlaubte Origin durfte also jeden beliebigen Header senden.

Der Preis dafür ist nicht nur die zu weite Freigabe. Eine Wildcard kann auch
nicht falsch werden: fällt ein Header weg, den das Protokoll braucht, bleibt
alles grün. Genau das ist der Grund, warum die Portfolio-Server nacheinander
auf explizite Listen umgestellt wurden — die Liste ist prüfbar, die Wildcard
nicht.

Geprüft wird mit echten Anfragen gegen die zusammengebaute App, nicht durch
Nachsehen im Middleware-Stack: die Anwesenheit eines `CORSMiddleware`-Objekts
zu behaupten, wäre auch bei leerer Liste grün.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from bakom_mcp.server import CORS_ALLOW_HEADERS, CORS_ROUTING_HEADERS, build_http_app

ORIGIN = "https://client.example"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("BAKOM_MCP_CORS_ORIGINS", ORIGIN)
    return TestClient(build_http_app())


def preflight(client: TestClient, request_headers: str, method: str = "POST"):
    """Sende einen Preflight.

    `request_headers` ist, was der Browser anzukündigen vorgibt. Das muss auf
    der Anfrage reiten und nicht bloss von der Antwort abgelesen werden:
    Starlette beantwortet einen Preflight, der einen nicht freigegebenen Header
    nennt, mit **400 und ohne `Access-Control-Allow-Origin`**.
    """
    return client.options(
        "/mcp",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": request_headers,
        },
    )


@pytest.mark.parametrize("header", CORS_ALLOW_HEADERS)
def test_jeder_freigegebene_header_passiert_den_preflight(client: TestClient, header: str) -> None:
    """Einzeln parametrisiert, nicht alle in einer Anfrage: ein Sammelaufruf
    bliebe grün, wenn nur einer der Header freigegeben wäre und Starlette den
    Rest durchwinkte."""
    resp = preflight(client, header)
    assert resp.status_code == 200, f"Preflight mit {header} abgewiesen"
    assert header.lower() in resp.headers["access-control-allow-headers"].lower()


def test_die_header_zusammen(client: TestClient) -> None:
    """Was ein Browser tatsächlich schickt: alle auf derselben Anfrage."""
    resp = preflight(client, ", ".join(h.lower() for h in CORS_ALLOW_HEADERS))
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_ein_nicht_freigegebener_header_wird_abgewiesen(client: TestClient) -> None:
    """Die Gegenkontrolle — und der eigentliche Befund.

    Ohne sie wären die Tests darüber gegen die alte Wildcard genauso grün. Sie
    ist die einzige Zusicherung hier, die zwischen «Liste» und «alles erlaubt»
    unterscheidet.
    """
    resp = preflight(client, "x-beliebiger-header")
    assert resp.status_code == 400, "die Freigabeliste winkt weiterhin alles durch"


def test_die_liste_nennt_jeden_routing_header_den_das_sdk_liest() -> None:
    """Gegen die SDK-Konstanten gehalten, nicht gegen abgeschriebenen Spec-Text.

    `mcp.shared.inbound` ist das, womit der Server eine Anfrage tatsächlich
    einordnet. Eine Umbenennung dort fällt hier als roter Test auf statt als
    Browser-Client, der ohne sichtbaren Grund nicht mehr verbindet.
    """
    from mcp.shared.inbound import (
        MCP_METHOD_HEADER,
        MCP_NAME_HEADER,
        MCP_PROTOCOL_VERSION_HEADER,
    )

    erlaubt = {h.lower() for h in CORS_ALLOW_HEADERS}
    noetig = {MCP_METHOD_HEADER, MCP_NAME_HEADER, MCP_PROTOCOL_VERSION_HEADER}
    assert noetig <= erlaubt, f"nicht freigegeben: {sorted(noetig - erlaubt)}"
    assert {h.lower() for h in CORS_ROUTING_HEADERS} == noetig


def test_die_liste_nennt_den_wiederaufnahme_header() -> None:
    """`Last-Event-ID` setzt einen abgerissenen SSE-Strom fort.

    Fehlt er, bricht ausschliesslich die Wiederaufnahme nach Paketverlust —
    unter Last, in Produktion, ohne dass ein Test etwas dazu sagt.
    """
    from mcp.server.streamable_http import LAST_EVENT_ID_HEADER

    assert LAST_EVENT_ID_HEADER in {h.lower() for h in CORS_ALLOW_HEADERS}


def test_die_liste_nennt_den_session_header() -> None:
    from mcp.server.streamable_http import MCP_SESSION_ID_HEADER

    assert MCP_SESSION_ID_HEADER in {h.lower() for h in CORS_ALLOW_HEADERS}


def test_keine_wildcard_in_der_freigabeliste() -> None:
    """Die Regression, die diesen Test rechtfertigt, war genau ein Zeichen."""
    assert "*" not in CORS_ALLOW_HEADERS


async def test_kein_werkzeug_deklariert_einen_mcp_param_header() -> None:
    """`Mcp-Param-*` trägt ein Werkzeug-Argument als HTTP-Header, angemeldet
    über eine `x-mcp-header`-Annotation im Eingabeschema. CORS kennt kein
    Präfix-Wildcard, also muss das erste Werkzeug, das einen benutzt, genau
    diesen Header in `CORS_ALLOW_HEADERS` nennen — sonst brechen Browser-
    Clients daran. Hier benutzt noch keines einen; der Test ist die Erinnerung
    für den Tag, an dem sich das ändert.
    """
    from bakom_mcp.server import mcp

    treffer = [t.name for t in await mcp.list_tools() if "x-mcp-header" in str(t.input_schema)]
    assert not treffer, (
        f"{treffer} deklarieren einen Mcp-Param-Header — in CORS_ALLOW_HEADERS nennen"
    )


def test_die_antwort_gibt_den_session_header_frei(client: TestClient) -> None:
    """`expose_headers` ist die andere Hälfte: ohne sie darf ein Browser den
    Header zwar senden, aber nicht lesen."""
    resp = preflight(client, "content-type")
    assert resp.status_code == 200
    # Der Preflight nennt expose_headers nicht; die Konfiguration selbst prüfen.
    from starlette.middleware.cors import CORSMiddleware

    app = build_http_app()
    schichten = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert len(schichten) == 1
    assert schichten[0].kwargs["expose_headers"] == ["Mcp-Session-Id"]
