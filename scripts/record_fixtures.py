#!/usr/bin/env python3
"""Zeichnet je eine echte Antwort pro Abfrageform auf.

Warum nicht von Hand geschrieben: eine handgeschriebene Erfolgs-Antwort stimmt
mit dem ueberein, was ihr Autor annahm, und kann die Quelle deshalb nicht
widerlegen. Aufgezeichnet wird darum an demselben Ort, an dem der Server die
Antwort entgegennimmt — ueber einen Response-Event-Hook auf dem echten
Lifespan-Client. Damit tragen Aufzeichnung und Betrieb dieselben Header, dasselbe
Timeout und dieselbe Egress-Allowlist; eine nachgebaute Anfrage taete das nicht.

Dieser Server spricht mit vier Hosts, aber in einem Dutzend Abfrageformen
(WMS-GetFeatureInfo je Layer, geo.admin-Identify je Layer, vier verschiedene
CKAN-Suchen, drei SPARQL-Abfragen). Die Portfolio-Regel «eine Antwort je
externem Endpunkt» waere mit vier Dateien erfuellt und truege fast nichts —
aufgezeichnet ist deshalb eine Antwort je Abfrage, die ein Werkzeug abschickt.

Gekuerzt wird nur die **Zahl** der Eintraege, nie ein Feld: aus einer
CKAN-Trefferliste bleiben die ersten Zeilen stehen, jede davon vollstaendig.
`count` bleibt unangetastet — CKAN meldet dort ohnehin die Gesamtzahl der
Treffer und nicht die Zahl der gelieferten Zeilen, und genau das liest der
Server aus. Welche Datei wie stark gekuerzt ist, steht in PROVENANCE.md.

Aufruf:

    PYTHONPATH=src python scripts/record_fixtures.py

Schreibt nach `tests/fixtures/` und erzeugt `tests/fixtures/PROVENANCE.md` neu.
Dateien, die kein Plan-Eintrag mehr erzeugt, werden geloescht — sonst waechst
der Ordner und der Nachweis bleibt zurueck.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

from bakom_mcp import server  # noqa: E402

FIXTURES = WURZEL / "tests" / "fixtures"

# Zuerich HB — dicht versorgt, deshalb als Standort mit Treffern gewaehlt.
ZUERICH = {"latitude": 47.3769, "longitude": 8.5417}
# Grimselgebiet — hoch, unbewohnt, deshalb als Gegenstueck. Ein Fixture-Satz,
# in dem jede Abfrage «ja» sagt, belegt die Nein-Seite nicht.
GRIMSEL = {"latitude": 46.5610, "longitude": 8.3370}

# Genau ein Cube-Titel auf LINDAS enthaelt dieses Wort — nur dann geht
# `bakom_medien_statistik` ueber den Katalog hinaus und schickt alle drei
# Abfragen ab. Mit einem mehrdeutigen Wort bliebe es bei der ersten.
CUBE_THEMA = "Meinungsmacht von Medienkonzernen"

VERSUCHE = 4


@dataclass(frozen=True)
class Aufnahme:
    """Ein Werkzeugaufruf und was er aufzeichnen soll."""

    name: str
    werkzeug: str
    klasse: str
    eingabe: dict[str, Any]
    # Erwartete Zahl Anfragen. Eine Zusicherung, keine Buchhaltung: mehrere
    # Werkzeuge hier fangen Fehler selbst ab und liefern trotzdem ein Ergebnis.
    # Bleibt eine Anfrage aus, faellt die Aufzeichnung — nicht erst der Test.
    anfragen: int = 1
    # Pfad zur Trefferliste und wie viele Zeilen davon bleiben. Leer = ungekuerzt.
    kuerzen: tuple[str, ...] = ()
    zeilen: int = 0
    notiz: str = ""

    def dateiname(self, i: int) -> str:
        return f"{self.name}.json" if self.anfragen == 1 else f"{self.name}_{i}.json"


PLAN: list[Aufnahme] = [
    Aufnahme(
        "breitband_100",
        "bakom_broadband_coverage",
        "BroadbandCoverageInput",
        {**ZUERICH, "min_speed_mbps": "100"},
    ),
    Aufnahme("glasfaser", "bakom_glasfaser_verfuegbarkeit", "CoordinateInput", dict(ZUERICH)),
    Aufnahme(
        "mobilfunk_5g",
        "bakom_mobilfunk_abdeckung",
        "MobileCoverageInput",
        {**ZUERICH, "generation": "5G"},
    ),
    Aufnahme(
        "multi_standort",
        "bakom_multi_standort_konnektivitaet",
        "MultiLocationInput",
        {"locations": [{"name": "Zürich HB", **ZUERICH}, {"name": "Grimsel", **GRIMSEL}]},
        anfragen=4,
        notiz="Zwei Standorte, je zwei Layer — Reihenfolge: ZH-5G, ZH-Glasfaser, "
        "Grimsel-5G, Grimsel-Glasfaser.",
    ),
    Aufnahme(
        "sendeanlagen",
        "bakom_sendeanlagen_suche",
        "AntennaSearchInput",
        {**ZUERICH, "radius_m": 1000},
        kuerzen=("results",),
        zeilen=5,
    ),
    Aufnahme(
        "frequenzdaten",
        "bakom_frequenzdaten",
        "CoordinateInput",
        dict(ZUERICH),
        kuerzen=("results",),
        zeilen=5,
    ),
    Aufnahme(
        "rtv_suche",
        "bakom_rtv_suche",
        "RTVSearchInput",
        {"query": "SRF", "limit": 5},
        kuerzen=("result", "results"),
        zeilen=3,
    ),
    Aufnahme(
        "medienstruktur",
        "bakom_medienstruktur_info",
        "TelekomStatInput",
        {"thema": "medien"},
        kuerzen=("result", "results"),
        zeilen=3,
    ),
    Aufnahme(
        "aktuell",
        "bakom_aktuell",
        "TelekomStatInput",
        {"thema": "medien"},
        kuerzen=("result", "results"),
        zeilen=3,
    ),
    Aufnahme(
        "telekomstatistik",
        "bakom_telekomstatistik_uebersicht",
        "TelekomStatInput",
        {"thema": "breitband"},
        kuerzen=("result", "results"),
        zeilen=3,
    ),
    Aufnahme(
        "medien_katalog",
        "bakom_medien_statistik",
        "MedienStatistikInput",
        {},
        notiz="Der Katalog aller veroeffentlichten BAKOM-Cubes. Ungekuerzt — der "
        "Server zaehlt die Titel, eine gekuerzte Liste zaehlte falsch.",
    ),
    Aufnahme(
        "medien_auswertung",
        "bakom_medien_statistik",
        "MedienStatistikInput",
        {"thema": CUBE_THEMA, "limit": 10},
        anfragen=3,
        notiz="Reihenfolge: Titelsuche, Dimensionen des Cubes, Beobachtungen.",
    ),
]


def _kontext(app_ctx: Any) -> MagicMock:
    """Baut den Context, den MCPServer sonst reicht — mit dem echten Client."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


@dataclass
class Antwort:
    """Eine gesehene Antwort samt der Anfrage, die sie ausgeloest hat."""

    url: str
    rumpf: str
    text: str
    original_bytes: int = 0
    gekuerzt_von: int = 0
    behalten: int = 0


def _kuerze(daten: Any, pfad: tuple[str, ...], zeilen: int) -> tuple[int, int]:
    """Kuerzt die Liste unter `pfad` auf `zeilen`; gibt (vorher, nachher)."""
    ziel = daten
    for schluessel in pfad[:-1]:
        ziel = ziel[schluessel]
    liste = ziel[pfad[-1]]
    vorher = len(liste)
    ziel[pfad[-1]] = liste[:zeilen]
    return vorher, len(ziel[pfad[-1]])


def _hook_fuer(gesehen: list[Antwort]) -> Callable[[httpx.Response], Awaitable[None]]:
    """Baut den Response-Hook fuer einen Versuch.

    Eigene Funktion, damit die Liste als Argument gebunden ist und nicht als
    Schleifenvariable aus dem umgebenden Namensraum (ruff B023).
    """

    async def hook(response: httpx.Response) -> None:
        await response.aread()
        # Bei POST steht die Abfrage im Rumpf, nicht in der URL — ohne ihn
        # sehen drei SPARQL-Aufzeichnungen im Nachweis gleich aus.
        rumpf = response.request.content.decode("utf-8", "replace")
        gesehen.append(Antwort(url=str(response.request.url), rumpf=rumpf, text=response.text))

    return hook


async def _fahre(a: Aufnahme, app_ctx: Any) -> list[Antwort]:
    """Ruft ein Werkzeug und gibt die dabei gesehenen Antworten zurueck."""
    fn = getattr(server, a.werkzeug)
    eingabe = getattr(server, a.klasse)(**a.eingabe)
    letzter: Exception | None = None

    for versuch in range(VERSUCHE):
        if versuch:
            await asyncio.sleep(2**versuch)
        gesehen: list[Antwort] = []

        hook = _hook_fuer(gesehen)
        hooks = app_ctx.http.event_hooks
        hooks.setdefault("response", []).append(hook)
        try:
            await fn(eingabe, _kontext(app_ctx))
        except Exception as e:  # noqa: BLE001 — jeder Fehler ist hier ein Retry-Grund
            letzter = e
            continue
        finally:
            hooks["response"].remove(hook)

        if len(gesehen) != a.anfragen:
            letzter = RuntimeError(
                f"{a.name}: {len(gesehen)} Antworten statt {a.anfragen} — "
                "das Werkzeug hat eine Anfrage verschluckt"
            )
            continue

        try:
            for antwort in gesehen:
                daten = json.loads(antwort.text)
                antwort.original_bytes = len(antwort.text.encode("utf-8"))
                if a.kuerzen:
                    antwort.gekuerzt_von, antwort.behalten = _kuerze(daten, a.kuerzen, a.zeilen)
                # Neu eingerueckt geschrieben: eine Zeile JSON waere kleiner,
                # aber im Diff nicht lesbar, und ein Fixture will gelesen werden.
                antwort.text = json.dumps(daten, indent=2, ensure_ascii=False) + "\n"
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            letzter = RuntimeError(f"{a.name}: Antwort nicht wie erwartet aufgebaut ({e!r})")
            continue

        return gesehen

    raise RuntimeError(f"{a.name} nach {VERSUCHE} Versuchen nicht aufgezeichnet: {letzter}")


@dataclass
class Eintrag:
    """Eine geschriebene Datei und was ueber sie im Nachweis steht."""

    name: str
    aufnahme: Aufnahme
    antwort: Antwort
    sha256: str = ""
    bytes: int = 0
    zusatz: list[str] = field(default_factory=list)


async def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    heute = datetime.now(UTC).date().isoformat()
    eintraege: list[Eintrag] = []

    async with server.lifespan(server.mcp) as app_ctx:
        for a in PLAN:
            print(f"… {a.werkzeug} ({a.name})", file=sys.stderr)
            for i, antwort in enumerate(await _fahre(a, app_ctx), start=1):
                datei = a.dateiname(i)
                (FIXTURES / datei).write_text(antwort.text, encoding="utf-8")
                roh = (FIXTURES / datei).read_bytes()
                eintraege.append(
                    Eintrag(
                        name=datei,
                        aufnahme=a,
                        antwort=antwort,
                        sha256=hashlib.sha256(roh).hexdigest(),
                        bytes=len(roh),
                    )
                )

    _schreibe_provenance(eintraege, heute)

    # Aufraeumen: was kein Plan-Eintrag mehr erzeugt, hat auch keinen Nachweis.
    geschrieben = {e.name for e in eintraege} | {"PROVENANCE.md"}
    for pfad in sorted(FIXTURES.iterdir()):
        if pfad.name not in geschrieben:
            print(f"– entferne veraltet: {pfad.name}", file=sys.stderr)
            pfad.unlink()

    print(f"{len(eintraege)} Aufzeichnungen in {FIXTURES}", file=sys.stderr)
    return 0


def _schreibe_provenance(eintraege: list[Eintrag], heute: str) -> None:
    zeilen = [
        "# Herkunft der Fixtures",
        "",
        f"Aufgezeichnet am **{heute}** mit `PYTHONPATH=src python scripts/record_fixtures.py`.",
        "",
        "Eine Antwort je **Abfrage**, nicht je Endpunkt: dieser Server spricht mit vier",
        "Hosts, aber in einem Dutzend Abfrageformen. Vier Dateien wuerden die",
        "Portfolio-Regel erfuellen und fast nichts belegen.",
        "",
        "Die Antworten stammen aus dem echten Lifespan-Client (gleicher User-Agent,",
        "gleiches Timeout, gleiche Egress-Allowlist wie im Betrieb), abgegriffen ueber",
        "einen httpx-Response-Hook. Neu gesetzt ist die Einrueckung; gekuerzt ist, wo",
        "unten vermerkt, allein die **Zahl** der Trefferzeilen. Kein Feld einer",
        "behaltenen Zeile ist angetastet, und `count` steht wie geliefert — CKAN meldet",
        "dort die Gesamtzahl der Treffer, nicht die Zahl der gelieferten Zeilen.",
        "",
        "Die Fehlerpfade — Timeout, 5xx, leere Trefferliste — bleiben handgeschrieben.",
        "Sie lassen sich nicht auf Zuruf aufzeichnen und sind als Erfindung in Ordnung.",
        "",
        "Zwei Dateien fallen bei jedem Lauf leicht anders aus: `medien_katalog.json` und",
        "`medien_auswertung_1.json` tragen aus `SAMPLE(?cube)` eine beliebige",
        "Cube-Version in der Variablen `any`. Der Server liest sie nicht — er nimmt",
        "`name` und `version` —, die Abweichung ist also Rauschen und kein Drift.",
        "",
    ]
    for e in eintraege:
        zeilen += [
            f"## `{e.name}`",
            "",
            f"- **Werkzeug:** `{e.aufnahme.werkzeug}`",
            f"- **Eingabe:** `{e.aufnahme.eingabe}`",
            f"- **URL:** `{e.antwort.url}`",
        ]
        if e.antwort.rumpf:
            rumpf = " ".join(e.antwort.rumpf.split())
            zeilen.append(f"- **Rumpf:** `{rumpf}`")
        if e.aufnahme.kuerzen:
            pfad = ".".join(e.aufnahme.kuerzen)
            zeilen.append(
                f"- **Auswahl:** die ersten {e.antwort.behalten} von "
                f"{e.antwort.gekuerzt_von} Zeilen in `{pfad}`, "
                f"aus {e.antwort.original_bytes} Bytes Rohantwort"
            )
        else:
            zeilen.append("- **Auswahl:** ungekuerzt")
        if e.aufnahme.notiz:
            zeilen.append(f"- **Hinweis:** {e.aufnahme.notiz}")
        zeilen += [
            f"- **Groesse:** {e.bytes} Bytes",
            f"- **SHA-256:** `{e.sha256}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(zeilen), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
