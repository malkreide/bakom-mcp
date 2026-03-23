[🇬🇧 English Version](README.md)

> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 📡 bakom-mcp

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/malkreide/bakom-mcp/releases)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Auth](https://img.shields.io/badge/auth-nicht%20erforderlich-brightgreen)](https://www.bakom.admin.ch/bakom/de/home/digitale-schweiz-und-internet/open-data.html)
![CI](https://github.com/malkreide/bakom-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server für BAKOM Open Data – Breitband, Mobilfunk, Medien und Schweizer Telekommunikationsstatistiken.

---

## Übersicht

**bakom-mcp** verbindet KI-Assistenten wie Claude mit der Open-Data-Infrastruktur des Bundesamts für Kommunikation (BAKOM). Ermöglicht Abfragen in natürlicher Sprache zu Breitbandverfügbarkeit, 5G/4G-Abdeckung, Mobilfunkstandorten, konzessionierten Rundfunkveranstaltern (RTV-Datenbank) und Telekommunikationsstatistiken – ohne API-Schlüssel.

Alle Daten sind als Open Government Data (OGD) unter offenen Lizenzen (CC0) veröffentlicht.

**Anker-Demo-Abfrage:** *«Welche Schulhäuser im Schulkreis 7 haben noch kein Glasfaser?»*

> `bakom_multi_standort_konnektivitaet` liefert die Vergleichstabelle automatisch.

---

## Funktionen

- 📶 **Breitbandverfügbarkeit** – Festnetzabdeckung bei 30/100/300/500/1000 Mbit/s (250×250m-Raster)
- 🔌 **Glasfaserstatus** – FTTB/FTTH-Verfügbarkeit pro Standort
- 📍 **Multi-Standort-Vergleich** – Konnektivitätsprüfung für bis zu 20 Standorte gleichzeitig
- 📱 **Mobilfunkabdeckung** – 5G/4G/3G Outdoor-Abdeckung (100×100m-Raster)
- 📡 **Antennensuche** – Mobil- und Sendeanlagen im konfigurierbaren Radius
- 📺 **RTV-Datenbank** – Konzessionierte Radio- und TV-Sender nach Name, Typ, Kanton
- 🗞️ **Medienlandschaft** – BAKOM-Medienstrukturberichte und Datensätze
- 📊 **Telekommunikationsstatistik** – Festnetz, Mobilfunk, Breitband-Marktdaten via opendata.swiss
- 🗂️ **Breitbandatlas-Katalog** – Alle BAKOM-Datensatz-Layer mit direkten API-Links
- 🔓 **Keine Authentifizierung** – Alle Daten sind Open Government Data (OGD)

---

## Voraussetzungen

- Python 3.11+
- `uv` oder `pip` für die Installation
- Internetverbindung (Live-APIs: geo.admin.ch, opendata.swiss, rtvdb.ofcomnet.ch)

---

## Installation

```bash
# Empfohlen: uvx (keine dauerhafte Installation nötig)
uvx bakom-mcp

# Oder mit pip installieren
pip install bakom-mcp

# Entwicklungs-Installation
git clone https://github.com/malkreide/bakom-mcp
cd bakom-mcp
pip install -e ".[dev]"
```

---

## Quickstart

### Claude Desktop

In `claude_desktop_config.json` eintragen:

```json
{
  "mcpServers": {
    "bakom": {
      "command": "uvx",
      "args": ["bakom-mcp"]
    }
  }
}
```

**Pfad zur Konfigurationsdatei:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### Cloud / HTTP-Transport

```bash
python -m bakom_mcp.server --http
# Server läuft auf http://localhost:8050/mcp
```

### Cursor / VS Code / LibreChat

```json
{
  "bakom": {
    "command": "uvx",
    "args": ["bakom-mcp"],
    "transport": "stdio"
  }
}
```

> 💡 *«stdio für den Entwickler-Laptop, HTTP/SSE für den Browser.»*

---

## Verfügbare Tools (12)

### Breitband & Konnektivität

| Tool | Beschreibung |
|------|--------------|
| `bakom_broadband_coverage` | Festnetzabdeckung an einer Koordinate (30–1000 Mbit/s) |
| `bakom_glasfaser_verfuegbarkeit` | FTTB/FTTH-Glasfaserstatus |
| `bakom_multi_standort_konnektivitaet` | Konnektivitätsvergleich für bis zu 20 Standorte |

### Mobilfunk & Sendeanlagen

| Tool | Beschreibung |
|------|--------------|
| `bakom_mobilfunk_abdeckung` | 5G/4G/3G Outdoor-Abdeckung |
| `bakom_sendeanlagen_suche` | Mobilfunkanlagen im konfigurierbaren Radius |
| `bakom_frequenzdaten` | Radio-/TV-Sendeanlagen in der Nähe |

### Medien & RTV

| Tool | Beschreibung |
|------|--------------|
| `bakom_rtv_suche` | Konzessionierte Sender suchen (RTV-Datenbank) |
| `bakom_medienstruktur_info` | Schweizer Medienlandschaft – Datensätze |
| `bakom_aktuell` | Aktuelle BAKOM-Themen (5G, Medien, KI, Post) |

### Statistik & Katalog

| Tool | Beschreibung |
|------|--------------|
| `bakom_telekomstatistik_uebersicht` | Telekommunikationsstatistik von opendata.swiss |
| `bakom_breitbandatlas_datensaetze` | Vollständiger Katalog aller Breitbandatlas-Layer |
| `bakom_check_api_status` | 🔍 Systemstatus aller konfigurierten Datenquellen |

---

## Beispiel-Prompts

```
Wie ist die Breitbandversorgung beim Schulhaus Leutschenbach (47.4148, 8.5654)?

Vergleiche 5G und Glasfaserabdeckung für diese drei Schulhäuser: [Koordinaten]

Welche Radiosender sind im Kanton Zürich konzessioniert?

Was ist die aktuelle BAKOM-Haltung zur 5G-Frequenzvergabe?

Liste alle Breitbandatlas-Datensätze auf, die via geo.admin.ch verfügbar sind.
```

---

## Datenquellen

| Quelle | Daten | Authentifizierung |
|--------|-------|-------------------|
| [geo.admin.ch](https://api3.geo.admin.ch) | Breitbandatlas, Mobilfunkabdeckung, Antennenstandorte | Keine |
| [opendata.swiss](https://opendata.swiss) | BAKOM-Datensätze, Telekommunikationsstatistik | Keine |
| [rtvdb.ofcomnet.ch](https://rtvdb.ofcomnet.ch) | Konzessionierte Radio-/TV-Sender | Keine |

Alle Daten stehen unter offenen Lizenzen (CC0 / OGD).

---

## Synergien mit dem MCP-Portfolio

**bakom-mcp** lässt sich mit anderen Servern des Portfolios verketten:

```
zurich-opendata-mcp  →  Schulhausadressen
         +
    bakom-mcp         →  Glasfaser- und 5G-Status
         =
«Digitale Chancengerechtigkeit»-Dashboard für alle Schulkreise
```

Weitere Kombinationen:
- `srgssr-mcp` + `bakom-mcp` → Medienabdeckung und Sendernetz
- `swiss-statistics-mcp` + `bakom-mcp` → Telekom-Marktentwicklung
- `fedlex-mcp` + `bakom-mcp` → Regulierungskontext (RTVG, FMG)

---

## Projektstruktur

```
bakom-mcp/
├── src/bakom_mcp/
│   ├── __init__.py          # Paket
│   └── server.py            # MCP-Server (12 Tools, 2 Resources)
├── tests/
│   └── test_integration.py  # 18 Integrationstests (Live-APIs)
├── .github/workflows/
│   └── ci.yml               # GitHub Actions CI (Python 3.11–3.13)
├── pyproject.toml           # Build-Konfiguration (hatchling)
├── claude_desktop_config.json
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                # Englische Hauptversion
└── README.de.md             # Diese Datei (Deutsch)
```

---

## Tests

```bash
# Unit-Tests (kein Netzwerk erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Integrationstests (Live-APIs, Internetverbindung erforderlich)
PYTHONPATH=src pytest tests/ -m "live"
```

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Mitwirken

Beiträge sind willkommen! Hinweise zu Fehlerberichten, Feature-Vorschlägen und Pull Requests finden sich in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Lizenz

MIT-Lizenz – siehe [LICENSE](LICENSE)

---

## Autor

Hayal Oezkan · [github.com/malkreide](https://github.com/malkreide)

---

## Credits & Verwandte Projekte

- **Daten:** [BAKOM Open Data](https://www.bakom.admin.ch/bakom/de/home/digitale-schweiz-und-internet/open-data.html) – Bundesamt für Kommunikation (BAKOM)
- **Geodaten:** [geo.admin.ch](https://api3.geo.admin.ch) – swisstopo / Bundesinfrastruktur für Geodaten
- **Protokoll:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Verwandt:** [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) – MCP-Server für Zürcher Stadtdaten
- **Verwandt:** [swiss-transport-mcp](https://github.com/malkreide/swiss-transport-mcp) – MCP-Server für den Schweizer ÖV
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)

---

*Teil des Schweizer Open-Data-MCP-Portfolios — öffentliche Daten verdienen öffentliche Schnittstellen.*
