# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Hinzugefügt

- **Frischehinweise auf den auflistenden Methoden** (SEP-2549, Spec
  `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK setzt beides von
  sich aus auf «sofort veraltet, nie geteilt» — wer nichts übergibt, lässt jeden
  Client bei jeder Verbindung neu auflisten, für Verzeichnisse, die per
  Dekorator beim Import feststehen und nicht vom Aufrufer abhängen.

  `resources/read` und `prompts/get` bleiben ohne Hinweis: das wäre eine
  Zusicherung über den Inhalt statt über das Verzeichnis. Ein Test hält das an
  der Antwort fest, ein zweiter an der Konfiguration.

### Behoben / Fixed

- **Die Pruefsummen im Fixture-Nachweis waren Zierde.** `PROVENANCE.md` fuehrt
  je Datei einen SHA-256 — um genau einen Fall zu fangen: eine Aufzeichnung,
  die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort ist
  wieder eine erfundene, und von aussen ist ihr das nicht anzusehen.
  Nachgerechnet hat sie kein Test. `test_die_pruefsumme_im_nachweis_stimmt`
  tut es jetzt, ueber die Bytes auf der Platte statt ueber den Loader — genau
  die hat der Recorder gehasht.

- **Jede Datensatz-Beschreibung war leer.** `bakom_rtv_suche`,
  `bakom_medienstruktur_info`, `bakom_aktuell` und
  `bakom_telekomstatistik_uebersicht` lasen `notes` — den Feldnamen aus dem
  CKAN-Kern. opendata.swiss liefert das Feld unter `description`. In allen
  aufgezeichneten Antworten kommt `notes` kein einziges Mal vor. Vier Werkzeuge
  gaben also zu jedem Datensatz einen leeren Text aus, während die Suite grün
  blieb: der handgeschriebene Stub in `test_unit.py` nannte das Feld genauso wie
  der Code und bestätigte damit nur dessen Annahme. Gelesen wird jetzt über
  `_ckan_de()`, das auch den Sprach-Dict-Fall (`{"de": …, "fr": …}`) an einer
  Stelle behandelt statt an vier.

- **Die Feldbeschreibung von `thema` nannte tote Suchwörter.** Sie empfahl
  `'breitband', 'mobilfunk', 'festnetz', 'marktanteile', 'haushaltszugang'`;
  davon liefern `mobilfunk` und `haushaltszugang` null Datensätze und
  `breitband` genau einen von 121 (gemessen am 15.08.2026). Der Katalog zerlegt
  keine Komposita — `mobilfunkanlagen` und `5g` finden etwas, `mobilfunk`
  nicht. Das Modell bekam daraufhin ein glaubwürdiges «dazu gibt es nichts».
  Die Beschreibung nennt jetzt belegte Wörter mit ihrer Trefferzahl und die
  Eigenheit des Index. Der Live-Test dazu prüfte bisher nur `"datensaetze" in
  data` — wahr auch bei null Treffern; er liest die Wörter jetzt aus der
  Beschreibung und verlangt Treffer mit Text.

### Hinzugefügt / Added

- **Aufgezeichnete Fixtures** in `tests/fixtures/` — 17 echte Antworten, eine je
  Abfrage, die ein Werkzeug abschickt (nicht je Endpunkt: vier Hosts, aber ein
  Dutzend Abfrageformen). Herkunft, Datum, Auswahlregel und SHA-256 je Datei in
  `tests/fixtures/PROVENANCE.md`, neu aufzeichnen mit
  `scripts/record_fixtures.py`, geladen über `tests/fixture_data.py`. Gekürzt
  ist nur die Zahl der Trefferzeilen, nie ein Feld; `count` bleibt stehen, weil
  CKAN dort die Gesamtzahl meldet und der Server genau die liest.
  Portfolio-Konvention, gleich wie in `meteoswiss-mcp` und
  `swiss-statistics-mcp`.

- **`tests/test_recorded_fixtures.py`** — 38 Zusicherungen, die jedes Werkzeug
  aus seiner eigenen Aufzeichnung fahren. Darunter: die Beschreibung muss beim
  Modell ankommen, ein leerer WMS-Layer wird zu «nein» und nicht zu einem
  Fehler, und die Cube-Version geht als Zahl in die zweite SPARQL-Abfrage (die
  Quelle liefert sie als Zeichenkette, `schema:version "6"` träfe nichts).

## [3.0.0] - 2026-08-14

### Geändert / Changed — Breaking

- **`bakom_aktuell` liefert keine Highlights mehr, sondern Datensätze.** Der
  Antwortschlüssel `highlights` ist durch `datensaetze` ersetzt (`titel`,
  `aktualisiert`, `beschreibung`, `url`). Der alte Name versprach eine
  redaktionelle Auswahl, die es nie gab: die Einträge stammten aus einem im
  Quellcode gepflegten Block, dessen jüngster Eintrag auf März 2026 datierte.
  Geliefert werden jetzt BAKOM-Datensätze aus dem opendata.swiss-Katalog,
  sortiert nach letzter Änderung.

- **`bakom_rtv_suche` nennt opendata.swiss als Quelle.** Bisher trug jede
  Antwort `"datenquelle": "BAKOM RTV-Datenbank"`, obwohl die Daten aus dem
  CKAN-Katalog kamen. Der Schlüssel `rtv_datenbank` heisst jetzt
  `hinweis_senderdaten`, und `suchanfrage.filterung` sagt, dass `kanton` und
  `media_type` die Volltextsuche gewichten statt exakt zu filtern.

- **Entfernte Modul-Konstanten:** `RTV_DB_API`, `GEO_ADMIN_IDENTIFY` und
  `GEO_ADMIN_FIND`. Alle drei waren definiert und wurden nirgends gelesen.

- **Egress-Allowlist:** `rtvdb.ofcomnet.ch` entfernt, `lindas.admin.ch`
  aufgenommen.

### Hinzugefügt / Added

- **`bakom_medien_statistik`** — Marktanteile, Reichweiten, Programm- und
  Ertragsstruktur aus den BAKOM-Cubes auf LINDAS (SPARQL, Architektur A).
  Ohne `thema` listet das Tool die 73 veröffentlichten Auswertungen, bei
  mehrdeutigem Thema die Kandidaten, bei exaktem Titel die Beobachtungen.
  Die Abdeckungsgrenze steht in der Tool-Description: die Cubes decken die
  untersuchten Programme ab, nicht den Bestand.

- **Geplanter Live-Test-Workflow** (`live-tests.yml`, täglich 05:17 UTC).
  Ein Fehlschlag wird einmal wiederholt; bleibt es rot, öffnet der Workflow
  ein Issue mit Label `live-test-failure`.

- **`.pre-commit-config.yaml`** mit derselben gepinnten ruff-Version wie die
  CI, und `scripts/check_version_sync.py` erzwingt jetzt, dass alle vier
  ruff-Stellen übereinstimmen.

- **`CLAUDE.md`** mit den portfolio-weiten Konventionen und den
  repo-spezifischen Befunden.

### Behoben / Fixed

- **Antennen-Distanzen waren immer `null`.** geo.admin.ch liefert
  Punktgeometrien als `{"points": [[east, north]]}`; gelesen wurde die
  Esri-Kurzform `{"x": …, "y": …}`. Damit hatte die Sortierung nach Distanz
  nichts zu sortieren und die Markdown-Tabelle druckte für jede Anlage «–».

- **Die Live-Test-Suite konnte nicht rot werden.** Vier Module aus
  Skript-Zeiten fingen jede Exception ab und buchten sie auf einen
  modulweiten Akkumulator; 66 von 78 Aufrufen scheiterten seit dem
  Lifespan-Refactor an der Tool-Signatur, ohne dass pytest etwas sah. Die
  Suite ist zu `tests/test_live.py` konsolidiert, prüft Antworten auf
  Fehlertexte und erreicht die Quellen wieder.

- **`bakom_aktuell` verschluckte CKAN-Fehler** (`except Exception: pass`) und
  fiel bei unbekanntem Thema still auf die Medien-Einträge zurück — eine
  Antwort zu «quantenverschluesselung» enthielt die SRG-Initiative. Beides
  entfernt; Fehler laufen über `_raise_api_error`, ein unbekanntes Thema
  ergibt eine leere Liste mit Hinweis.

- **Streamable-HTTP wies unter jedem echten Hostnamen mit 421 ab (SEC-005).**
  Die App wurde mit `mcp.streamable_http_app()` ohne `host` gebaut. Unter mcp 2.x
  ist das kein neutraler Default: das SDK leitet daraus seine Host-Allow-List ab
  und aktiviert bei loopback-artigem Wert automatisch `127.0.0.1:*`. Da das
  Argument selbst auf `127.0.0.1` defaultet, traf das jeden Start mit
  `BAKOM_MCP_HOST=0.0.0.0`. Vor der Migration auf 2.x ging `host` an den
  `FastMCP`-Konstruktor, wo dieselbe Logik den echten Bind sah und den Schutz
  korrekt ausliess.

  Der Bind reist jetzt in die App, und eine echte Allow-List wird aus dem neuen
  `BAKOM_MCP_ALLOWED_HOSTS` gebaut. Ohne diese Variable bleibt der Schutz auf
  einem Nicht-Loopback-Bind bewusst aus und der Aufrufer warnt — eine geratene
  Liste wäre genau der 421-Fall.

- **App-Bau aus dem `__main__`-Block herausgezogen.** Er lag vollständig inline,
  weshalb kein Test die Transport-Verdrahtung sehen konnte — genau so blieb der
  fehlende `host`-Kwarg unbemerkt. `build_http_app()` und
  `build_transport_security()` sind jetzt normale Funktionen; die 13 neuen Tests
  prüfen die gebaute App, nicht nur ihre Bauteile.

  Darunter der tragende Fall „richtiger Hostname, falscher Port" — nur er
  unterscheidet eine portgenaue Allow-List von einer, die alles durchlässt.
  Mutationsgetestet: nimmt man den `host`-Kwarg wieder weg, reproduziert der
  Test das 421.

  Geprüft mit allen vier CI-Gates: 76 passed / 78 deselected, `ruff check src/`,
  `ruff format --check src/`, Versions-Sync OK.

## [2.0.4] - 2026-07-30

### Behoben / Fixed
- **User-Agent meldete eine ganze Major-Version zu wenig.** Das Literal in
  `server.py` las `bakom-mcp/1.0`, während das Paket bei **2.0.3** stand, und
  `__init__.__version__` stand auf 1.0.0. Jede Anfrage an die BAKOM-Endpoints
  trug den veralteten Wert. Die Version kommt jetzt aus den installierten
  Paket-Metadaten (`importlib.metadata`, aus `pyproject.toml` erzeugt), der
  User-Agent wird daraus abgeleitet. Abgesichert durch `tests/test_version.py`.

## [2.0.2] — nicht auf PyPI

Der Tag `v2.0.2` existiert, das Paket liegt aber nicht auf PyPI und wird auch
nicht nachgereicht. `pip install bakom-mcp==2.0.2` schlägt deshalb fehl;
2.0.3 enthält denselben Stand.

Zwei Ursachen, beide erst im August 2026 aufgeklärt: `publish.yml` hing damals
an `release: published` und wurde von einem per `git push` gesetzten Tag nie
gestartet — und der Upload wäre ohnehin abgewiesen worden, weil
`[project.urls]` mit `"mcp-name" = "io.github.malkreide/bakom-mcp"` einen
Nicht-URL-Wert in einem Feld führte, das PyPI als URL validiert. In 2.0.3 ist
der Eintrag entfernt.

## [2.0.0] - 2026-05-09

Audit-driven hardening release. After three full audit runs against
[`malkreide/mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) v1.0.0
(catalog v0.5.0, 68 checks), the server reaches **production-ready** status
with 0 findings, 34 of 36 applicable checks passing.

### Added

- **MCP Prompts (3 templates)** — first-class `@mcp.prompt` discovery layer:
  - `schulhaus_konnektivitaet` (Anchor-Demo: Glasfaser+5G für Schulhäuser)
  - `rtv_kanton_uebersicht` (konzessionierte Sender pro Kanton)
  - `standort_konnektivitaet_vergleich` (generischer Standort-Vergleich)
- **Container deployment** — multi-stage `Dockerfile` (slim-bullseye, non-root UID 10001),
  `docker-compose.yml` with sandbox defaults (`read_only`, `cap_drop=ALL`,
  `no-new-privileges`, `mem_limit=256m`), `.dockerignore`, and CI build/smoke job.
- **Egress allow-list** — `ALLOWED_EGRESS_HOSTS` (frozenset) enforced via
  httpx event-hook on the lifespan client. Outbound calls to non-listed hosts
  raise `EgressNotAllowedError` before any TCP connect.
- **CC BY 4.0 attribution** — every Markdown tool output ends with a footer
  citing source (BAKOM via opendata.swiss / geo.admin.ch) and licence.
  README has dedicated "Data Licence" / "Datenlizenz" section.
- **README scope section** — explicit "What this server does / does not"
  (read-only, no filesystem access, no auth tokens, no caching, no `subprocess`).
- **Tool-call lifecycle logging** — decorator `_log_tool_call` emits structured
  records (`tool_call_start`, `tool_call_ok`, `tool_call_failed`) with
  `tool`, `duration_ms`, and `error_class` extras to stderr.
- **Progress reports** — `bakom_multi_standort_konnektivitaet` now calls
  `ctx.report_progress()` per location (visible spinner in Claude Desktop /
  MCP Inspector) plus `ctx.info()` at start.
- **Empty-result heuristics** — `bakom_sendeanlagen_suche` suggests doubling
  the radius (capped at 5000m); `bakom_rtv_suche` suggests targeted filter
  loosening (canton, media-type, query). LLM agents iterate instead of
  bouncing on "no results".
- **Secret-scan CI** — new `.github/workflows/secret-scan.yml` runs
  `gitleaks-action` on every push and pull request.
- **Env vars for HTTP transport** — `BAKOM_MCP_HOST` (default `127.0.0.1`),
  `BAKOM_MCP_PORT` (default `8050`), `BAKOM_MCP_CORS_ORIGINS`
  (comma-separated, default empty = CORS disabled). Explicit `0.0.0.0`-bind
  emits a stderr warning. `.env.example` documents the surface.
- **60 offline unit tests** — mock-based tests for inputs, error masking,
  lifespan, egress, logging, progress, prompts, heuristics, and attribution.
  Live tests now correctly tagged `@pytest.mark.live` and excluded from
  CI default (`pytest -m "not live"`).
- **Audit reports** — `audits/` directory with three full run outputs
  (`audit-report.md`, `summary.json`, `verification-results.json`, raw
  command outputs per check) for reproducible audit trails.

### Changed

- **FastMCP lifespan** — single `httpx.AsyncClient` shared across all tool
  calls (15 s timeout, `User-Agent: bakom-mcp/1.0`, HTTP-event-hook for
  egress). Previously: per-call client construction (TLS handshake on
  every tool invocation; for `bakom_multi_standort_konnektivitaet` with
  20 locations that meant up to 40 new connections per call).
- **Error semantics** — API errors now raise `ToolError` from
  `mcp.server.fastmcp.exceptions`. The wire response carries
  `CallToolResult(isError=True, …)` instead of a plain `"Fehler: …"`
  string with `isError=False`. MCP clients can distinguish data errors
  from successful results and apply retry logic.
- **Error masking** — generic exception catch no longer leaks the raw
  exception message (`f"Fehler: ({type(e).__name__}): {e}"` removed).
  Internal details go to `logger.exception`; the LLM sees
  `"Fehler: Unerwarteter interner Fehler. Bitte erneut versuchen."`
- **HTTP-mode entry point** — switched from `mcp.run(transport=…, port=…)`
  (which became invalid in mcp-SDK ≥ 1.10) to explicit
  `uvicorn.run(mcp.streamable_http_app(), host=…, port=…)` with optional
  CORS middleware. CORS is **off** by default and opt-in via
  `BAKOM_MCP_CORS_ORIGINS`; `expose_headers=["Mcp-Session-Id"]` for
  browser-client reconnect.
- **Status banner** — startup print in `--http` mode now goes to
  `sys.stderr` (was: `stdout`). Enforces stdio discipline so future
  additions cannot accidentally corrupt the JSON-RPC stream.
- **Dependency upper bounds** — `mcp[cli]>=1.10.0,<2.0`,
  `httpx>=0.27.0,<1.0`, `pydantic>=2.7.0,<3.0`. Prevents silent
  acceptance of major-version breaking changes.
- **README** — bilingual updates (EN + DE) with Docker section,
  env-var table, scope section, and data-licence section.

### Fixed

- Latent `TypeError` in `--http` startup path on mcp-SDK ≥ 1.10
  (the previous `mcp.run(port=…)` call was rejected by the new
  signature). The new `uvicorn.run(...)` flow is verified end-to-end
  via the new docker smoke-test CI job.
- Doubled CC BY 4.0 attribution footer in eight tool outputs
  (regression introduced and corrected within v2.0.0 development).

### Security

- **Container hardening** — non-root user, read-only filesystem,
  dropped capabilities, no privilege escalation, resource limits
  (256 MB RAM, 0.5 CPU, 64 PIDs).
- **Code-layer egress allow-list** — every outbound HTTP request is
  validated against a frozenset of six known data-source hosts before
  TCP connect.
- **Secrets hygiene** — `.gitignore` covers `.env`, `.env.*`,
  `*.secrets`, `credentials.json`. CI runs gitleaks on every PR.
- **Default localhost bind** — HTTP server defaults to `127.0.0.1`;
  `0.0.0.0` requires explicit env var and emits a stderr warning.

### Notes

- Two follow-up issues remain open as **conditional TODOs** that only
  become actionable when the deployment profile changes:
  - [#29](https://github.com/malkreide/bakom-mcp/issues/29) — SCALE-002
    Stateful LB for Streamable-HTTP (when `is_cloud_deployed=true`)
  - [#30](https://github.com/malkreide/bakom-mcp/issues/30) — SEC-009
    Session-ID Cryptographic Binding (when `auth_model != "none"`)

## [1.0.0] - 2026-03-13

### Added
- Initial release
- 12 tools in 4 categories: broadband, mobile, media/RTV, statistics
- `bakom_broadband_coverage` – Fixed-line coverage at 30–1000 Mbit/s (geo.admin.ch)
- `bakom_glasfaser_verfuegbarkeit` – FTTB/FTTH fibre availability
- `bakom_multi_standort_konnektivitaet` – Multi-location connectivity comparison (up to 20 locations)
- `bakom_mobilfunk_abdeckung` – 5G/4G/3G outdoor coverage
- `bakom_sendeanlagen_suche` – Mobile antenna search by radius
- `bakom_frequenzdaten` – Radio/TV transmitter sites
- `bakom_rtv_suche` – Licensed broadcaster search (RTV database)
- `bakom_medienstruktur_info` – Swiss media landscape datasets
- `bakom_aktuell` – Current BAKOM topics with opendata.swiss enrichment
- `bakom_telekomstatistik_uebersicht` – Telecom statistics via CKAN API
- `bakom_breitbandatlas_datensaetze` – Full Broadband Atlas layer catalogue
- 2 MCP resources: `bakom://info`, `bakom://demo-standorte`
- 18 integration tests against live APIs
- GitHub Actions CI (Python 3.11–3.13)
- Bilingual documentation (EN/DE, Swiss spelling)
- Dual transport: stdio (Claude Desktop) + Streamable HTTP (cloud)
- WGS84 → LV95 coordinate conversion (swisstopo approximation)
