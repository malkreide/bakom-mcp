# bakom-mcp

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Auth](https://img.shields.io/badge/auth-none%20required-brightgreen)

> MCP Server for BAKOM Open Data – broadband, mobile coverage, media and Swiss telecom statistics

[🇩🇪 Deutsche Version](README.de.md)

## Overview

`bakom-mcp` connects AI assistants to the Swiss Federal Office of Communications (BAKOM) open data infrastructure. It enables natural-language queries about broadband availability, 5G/4G coverage, mobile antenna locations, licensed broadcasters (RTV database), and telecommunications statistics — all without API keys.

A key use case: automatically checking broadband and 5G status for all school buildings in the city.

## Features

- **Broadband availability** – Fixed-line coverage at 30/100/300/500/1000 Mbit/s (250×250m grid)
- **Fibre status** – FTTB/FTTH availability per location
- **Multi-location comparison** – Connectivity check for up to 20 locations simultaneously
- **Mobile coverage** – 5G/4G/3G outdoor coverage (100×100m grid)
- **Antenna search** – Mobile and broadcast transmitters within a configurable radius
- **RTV database** – Search licensed radio and TV broadcasters by name, type, canton
- **Media landscape** – BAKOM media structure reports and datasets
- **Telecom statistics** – Fixed-line, mobile, broadband market data via opendata.swiss
- **Broadband Atlas catalogue** – All BAKOM dataset layers with direct API links
- **No authentication required** – All data is Open Government Data (OGD)

## Prerequisites

- Python 3.11+
- `uv` or `pip` for installation
- Internet connection (live APIs: geo.admin.ch, opendata.swiss, rtvdb.ofcomnet.ch)

## Installation

```bash
# Recommended: uvx (no install required)
uvx bakom-mcp

# Or install with pip
pip install bakom-mcp

# Development install
git clone https://github.com/malkreide/bakom-mcp
cd bakom-mcp
pip install -e ".[dev]"
```

## Usage / Quickstart

### Claude Desktop

Add to `claude_desktop_config.json`:

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

### Cloud / HTTP Transport

```bash
python -m bakom_mcp.server --http
# Server running at http://localhost:8050/mcp
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

## Tools (12)

### Broadband & Connectivity

| Tool | Description |
|------|-------------|
| `bakom_broadband_coverage` | Fixed-line coverage at a coordinate (30–1000 Mbit/s) |
| `bakom_glasfaser_verfuegbarkeit` | FTTB/FTTH fibre availability |
| `bakom_multi_standort_konnektivitaet` | Connectivity comparison for up to 20 locations |

### Mobile & Transmitters

| Tool | Description |
|------|-------------|
| `bakom_mobilfunk_abdeckung` | 5G/4G/3G outdoor coverage |
| `bakom_sendeanlagen_suche` | Mobile antennas within a configurable radius |
| `bakom_frequenzdaten` | Radio/TV transmitter sites near a location |

### Media & RTV

| Tool | Description |
|------|-------------|
| `bakom_rtv_suche` | Search licensed broadcasters (RTV database) |
| `bakom_medienstruktur_info` | Swiss media landscape datasets |
| `bakom_aktuell` | Current BAKOM topics (5G, media, AI, postal) |

### Statistics

| Tool | Description |
|------|-------------|
| `bakom_telekomstatistik_uebersicht` | Telecom statistics from opendata.swiss |
| `bakom_breitbandatlas_datensaetze` | Full catalogue of Broadband Atlas layers |

## Example Prompts

```
What is the broadband situation at Schulhaus Leutschenbach (47.4148, 8.5654)?

Compare 5G and fibre coverage for these three school buildings: [coordinates]

Which radio stations are licensed in canton Zurich?

Show me the current BAKOM position on 5G frequency allocation.

List all Broadband Atlas datasets available via geo.admin.ch.
```

## Data Sources

| Source | Data | Authentication |
|--------|------|---------------|
| [geo.admin.ch](https://api3.geo.admin.ch) | Broadband Atlas, mobile coverage, antenna locations | None |
| [opendata.swiss](https://opendata.swiss) | BAKOM datasets, telecom statistics | None |
| [rtvdb.ofcomnet.ch](https://rtvdb.ofcomnet.ch) | Licensed radio/TV broadcasters | None |

All data is published under open licences (CC0 / OGD).

## Project Structure

```
bakom-mcp/
├── src/bakom_mcp/
│   ├── __init__.py          # Package
│   └── server.py            # MCP Server (12 tools, 2 resources)
├── tests/
│   └── test_integration.py  # 18 integration tests (live APIs)
├── .github/workflows/
│   └── ci.yml               # GitHub Actions CI (Python 3.11–3.13)
├── pyproject.toml           # Build config (hatchling)
├── claude_desktop_config.json
├── README.md / README.de.md
├── CHANGELOG.md
└── LICENSE
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## License

MIT License — see [LICENSE](LICENSE)

## Author

malkreide · [GitHub](https://github.com/malkreide)

---

*Part of the Swiss Open Data MCP portfolio — public data deserves public interfaces.*
