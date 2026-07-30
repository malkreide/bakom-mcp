"""Eingehende Host/Origin-Prüfung des Streamable-HTTP-Transports (SEC-005).

Auslöser war kein fehlender Schutz, sondern ein zu strenger an der falschen
Adresse. mcp 2.x aktiviert automatisch eine Allow-List auf ``127.0.0.1:*``, wenn
das ``host``-Argument der App loopback-artig aussieht — und
``streamable_http_app()`` defaultet genau darauf. Jeder Start mit
``BAKOM_MCP_HOST=0.0.0.0`` bekam damit auf jede Anfrage unter einem echten
Hostnamen HTTP 421.

Vor der Migration auf mcp 2.x erreichte ``host`` den ``FastMCP``-Konstruktor, wo
dieselbe Logik den echten Bind sah und den Schutz korrekt ausliess.

Die App-Konstruktion lag inline im ``__main__``-Block, weshalb kein Test die
Transport-Verdrahtung sehen konnte — genau so blieb der Fehler unbemerkt.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from bakom_mcp.server import build_http_app, build_transport_security

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("BAKOM_MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("BAKOM_MCP_CORS_ORIGINS", raising=False)
    yield


def test_loopback_bind_is_protected():
    sec = build_transport_security("127.0.0.1", 8050)
    assert sec is not None
    assert sec.enable_dns_rebinding_protection is True
    assert "127.0.0.1:8050" in sec.allowed_hosts


def test_wildcard_bind_without_allowlist_stays_off():
    """Der eigentliche Fix.

    Auf 0.0.0.0 ist der erreichbare Name hier unbekannt, und der
    SDK-Loopback-Default ist genau eine Vermutung — er reproduziert das 421.
    """
    assert build_transport_security("0.0.0.0", 8050) is None


def test_wildcard_bind_with_allowlist_is_protected(monkeypatch):
    monkeypatch.setenv("BAKOM_MCP_ALLOWED_HOSTS", "bakom.example.ch")
    sec = build_transport_security("0.0.0.0", 8050)
    assert sec is not None
    assert "bakom.example.ch" in sec.allowed_hosts
    # Loopback bleibt drin, sonst brechen Container-Health-Checks.
    assert "127.0.0.1:8050" in sec.allowed_hosts


def test_cors_origins_pass_the_transport_check(monkeypatch):
    """Sonst weist der Transport genau die Browser-Clients ab, die CORS erlaubt."""
    monkeypatch.setenv("BAKOM_MCP_CORS_ORIGINS", "https://claude.ai")
    sec = build_transport_security("127.0.0.1", 8050)
    assert "https://claude.ai" in sec.allowed_origins


def test_wildcard_cors_is_not_copied(monkeypatch):
    monkeypatch.setenv("BAKOM_MCP_CORS_ORIGINS", "*")
    sec = build_transport_security("127.0.0.1", 8050)
    assert "*" not in sec.allowed_origins


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_all_loopback_forms_count_as_local(host):
    assert build_transport_security(host, 8050) is not None


def _post(app, host_header: str) -> int:
    with TestClient(app) as client:
        return client.post(
            "/mcp", headers={"Host": host_header, **_HEADERS}, json=_INIT
        ).status_code


def test_a_public_bind_is_reachable_again():
    """Die Regression selbst, durch den echten ASGI-Stack.

    Ohne den ``host``-Kwarg ist das ein 421 — der Zustand, den dieser Commit
    behebt.
    """
    assert _post(build_http_app("0.0.0.0", 8050), "bakom.example.ch") == 200


def test_configured_host_is_served(monkeypatch):
    monkeypatch.setenv("BAKOM_MCP_ALLOWED_HOSTS", "bakom.example.ch")
    assert _post(build_http_app("0.0.0.0", 8050), "bakom.example.ch") == 200


def test_foreign_host_is_rejected(monkeypatch):
    monkeypatch.setenv("BAKOM_MCP_ALLOWED_HOSTS", "bakom.example.ch")
    assert _post(build_http_app("0.0.0.0", 8050), "evil.example.com") == 421


def test_right_host_wrong_port_is_rejected(monkeypatch):
    """Der tragende Fall.

    ``evil.example.com`` allein beweist wenig: ein zurückfallender
    Loopback-Default würde ihn ebenfalls abweisen. Nur „richtiger Hostname,
    falscher Port" unterscheidet eine portgenaue Allow-List von einer, die alles
    durchlässt.
    """
    monkeypatch.setenv("BAKOM_MCP_ALLOWED_HOSTS", "bakom.example.ch:8050")
    assert _post(build_http_app("0.0.0.0", 8050), "bakom.example.ch:9999") == 421


def test_allowed_hosts_is_parsed_as_csv(monkeypatch):
    from bakom_mcp.server import _allowed_hosts

    monkeypatch.setenv("BAKOM_MCP_ALLOWED_HOSTS", "a.example.ch, b.example.ch")
    assert _allowed_hosts() == ["a.example.ch", "b.example.ch"]
