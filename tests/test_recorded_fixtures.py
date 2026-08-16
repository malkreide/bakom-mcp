"""Jede Abfrage, gefahren aus einer aufgezeichneten Antwort.

Die handgeschriebenen Stubs im Rest der Suite pruefen die *Fehler*-Pfade — ein
Timeout, ein 5xx, eine leere Trefferliste —, die sich nicht auf Zuruf
aufzeichnen lassen und als Erfindung in Ordnung sind. Was sie nicht koennen: die
Form einer Erfolgs-Antwort belegen. Sie stimmen mit dem ueberein, was ihr Autor
annahm.

Genau daran ist es hier gescheitert: `tests/test_unit.py` baute CKAN-Zeilen mit
`notes` — wie der Code sie las —, waehrend opendata.swiss das Feld
`description` nennt. Vier Werkzeuge lieferten produktiv zu jedem Datensatz eine
leere Beschreibung, und die Suite blieb gruen.

Dieser Server spricht mit vier Hosts, aber in einem Dutzend Abfrageformen.
Aufgezeichnet ist deshalb eine Antwort je Abfrage, die ein Werkzeug abschickt —
auch dann, wenn ein Werkzeug mehrere abschickt.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`PYTHONPATH=src python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fixture_data import fixture_json, fixture_text, provenance, recorded_names
from mcp.server.mcpserver.exceptions import ToolError

from bakom_mcp import server

# Werkzeug → (Eingabeklasse, Eingabe, Aufzeichnungen in der Reihenfolge der
# Anfragen). Bewusst hier noch einmal hingeschrieben und nicht aus dem Recorder
# importiert: die Tests sollen eine eigene Aussage machen. Dass beide Listen
# uebereinstimmen, prueft `test_der_recorder_kennt_dieselben_abfragen`.
WERKZEUGE: dict[str, tuple[str, dict[str, Any], list[str]]] = {
    "bakom_broadband_coverage": (
        "BroadbandCoverageInput",
        {"latitude": 47.3769, "longitude": 8.5417, "min_speed_mbps": "100"},
        ["breitband_100.json"],
    ),
    "bakom_glasfaser_verfuegbarkeit": (
        "CoordinateInput",
        {"latitude": 47.3769, "longitude": 8.5417},
        ["glasfaser.json"],
    ),
    "bakom_mobilfunk_abdeckung": (
        "MobileCoverageInput",
        {"latitude": 47.3769, "longitude": 8.5417, "generation": "5G"},
        ["mobilfunk_5g.json"],
    ),
    "bakom_multi_standort_konnektivitaet": (
        "MultiLocationInput",
        {
            "locations": [
                {"name": "Zürich HB", "latitude": 47.3769, "longitude": 8.5417},
                {"name": "Grimsel", "latitude": 46.5610, "longitude": 8.3370},
            ]
        },
        [
            "multi_standort_1.json",
            "multi_standort_2.json",
            "multi_standort_3.json",
            "multi_standort_4.json",
        ],
    ),
    "bakom_sendeanlagen_suche": (
        "AntennaSearchInput",
        {"latitude": 47.3769, "longitude": 8.5417, "radius_m": 1000},
        ["sendeanlagen.json"],
    ),
    "bakom_frequenzdaten": (
        "CoordinateInput",
        {"latitude": 47.3769, "longitude": 8.5417},
        ["frequenzdaten.json"],
    ),
    "bakom_rtv_suche": (
        "RTVSearchInput",
        {"query": "SRF", "limit": 5},
        ["rtv_suche.json"],
    ),
    "bakom_medienstruktur_info": ("TelekomStatInput", {"thema": "medien"}, ["medienstruktur.json"]),
    "bakom_aktuell": ("TelekomStatInput", {"thema": "medien"}, ["aktuell.json"]),
    "bakom_telekomstatistik_uebersicht": (
        "TelekomStatInput",
        {"thema": "breitband"},
        ["telekomstatistik.json"],
    ),
}

# `bakom_medien_statistik` steht ausserhalb der Tabelle: dasselbe Werkzeug
# schickt je nach Eingabe eine oder drei Abfragen ab, und beide Faelle sind
# aufgezeichnet.
MEDIEN_KATALOG = ["medien_katalog.json"]
MEDIEN_AUSWERTUNG = [
    "medien_auswertung_1.json",
    "medien_auswertung_2.json",
    "medien_auswertung_3.json",
]
CUBE_THEMA = "Meinungsmacht von Medienkonzernen"

# Die vier Werkzeuge, die aus dem opendata.swiss-Katalog lesen, und wo im
# Ergebnis die Beschreibung eines Datensatzes landet.
KATALOG_WERKZEUGE: dict[str, tuple[str, str]] = {
    "bakom_rtv_suche": ("resultate", "beschreibung"),
    "bakom_medienstruktur_info": ("datensaetze", "beschreibung"),
    "bakom_aktuell": ("datensaetze", "beschreibung"),
    "bakom_telekomstatistik_uebersicht": ("datensaetze", "beschreibung"),
}

ALLE_AUFZEICHNUNGEN = sorted(
    {n for _, _, namen in WERKZEUGE.values() for n in namen}
    | set(MEDIEN_KATALOG)
    | set(MEDIEN_AUSWERTUNG)
)


# --------------------------------------------------------------------------
# Ein Client, der die Aufzeichnungen ausliefert
# --------------------------------------------------------------------------
def _klient(*namen: str) -> tuple[AsyncMock, list[tuple[str, dict[str, Any]]]]:
    """Liefert die genannten Aufzeichnungen der Reihe nach aus.

    Gibt zusaetzlich das Protokoll der gestellten Anfragen zurueck — mehrere
    Zusicherungen unten lesen die tatsaechlich abgeschickte Abfrage und nicht
    nur das Ergebnis.
    """
    strom = iter(namen)
    protokoll: list[tuple[str, dict[str, Any]]] = []

    async def antwort(url: str, **kw: Any) -> httpx.Response:
        try:
            name = next(strom)
        except StopIteration:  # pragma: no cover — faellt als AssertionError auf
            raise AssertionError(f"mehr Anfragen als Aufzeichnungen: {url}") from None
        protokoll.append((str(url), kw))
        methode = "POST" if "data" in kw or "json" in kw else "GET"
        return httpx.Response(
            200,
            text=fixture_text(name),
            request=httpx.Request(methode, url, params=kw.get("params")),
        )

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=antwort)
    client.post = AsyncMock(side_effect=antwort)
    return client, protokoll


def _ctx(client: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = server.AppContext(http=client)
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


async def _fahre(werkzeug: str, klasse: str, eingabe: dict[str, Any], namen: list[str]) -> Any:
    """Ruft ein Werkzeug im JSON-Format und gibt das geparste Ergebnis zurueck."""
    client, _ = _klient(*namen)
    fn = getattr(server, werkzeug)
    params = getattr(server, klasse)(**eingabe, response_format="json")
    return json.loads(await fn(params, _ctx(client)))


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------
def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    treffer = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert treffer, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    wann = dt.date.fromisoformat(treffer.group(1))
    assert wann <= dt.datetime.now(dt.UTC).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jede_abfrage_hat_eine_aufzeichnung():
    """Bewacht die Regel selbst — hier je Abfrage statt je Endpunkt.

    Vier Hosts, ein Dutzend Abfrageformen: «eine Antwort je externem Endpunkt»
    waere mit vier Dateien erfuellt und truege fast nichts.
    """
    fehlend = sorted(set(ALLE_AUFZEICHNUNGEN) - set(recorded_names()))
    assert not fehlend, f"Abfragen ohne Aufzeichnung: {fehlend}"


def test_keine_aufzeichnung_liegt_unbenutzt_herum():
    """Die Gegenrichtung — eine Datei, die niemand liest, belegt nichts."""
    ueberzaehlig = sorted(set(recorded_names()) - set(ALLE_AUFZEICHNUNGEN))
    assert not ueberzaehlig, f"von keinem Test gelesen: {ueberzaehlig}"


def test_die_provenance_nennt_alle_vier_hosts():
    """Sonst belegt der Ordner nur einen Teil des Servers."""
    nachweis = provenance()
    fehlend = [h for h in server.ALLOWED_EGRESS_HOSTS if h not in nachweis]
    # geodesy.geo.admin.ch steht in der Allowlist, wird aber von keinem Werkzeug
    # gerufen — deshalb hier ausgenommen und nicht stillschweigend uebergangen.
    assert fehlend == ["geodesy.geo.admin.ch"] or not fehlend, f"Hosts ohne Aufzeichnung: {fehlend}"


def test_der_recorder_kennt_dieselben_abfragen():
    """Recorder und Tests duerfen nicht auseinanderlaufen.

    Laedt `scripts/record_fixtures.py` als Modul — `main()` wird nicht gerufen,
    es geht keine Anfrage raus. Damit ist zugleich geprueft, dass der Recorder
    ueberhaupt importierbar ist: ihn ruft im Betrieb niemand auf, und ruff
    kaeme einem Fehler darin nicht bei.
    """
    pfad = Path(__file__).resolve().parent.parent / "scripts" / "record_fixtures.py"
    name = "record_fixtures_probe"
    spec = importlib.util.spec_from_file_location(name, pfad)
    assert spec and spec.loader
    modul = importlib.util.module_from_spec(spec)
    # Vor dem Ausfuehren registrieren: `@dataclass` schlaegt das eigene Modul in
    # `sys.modules` nach, um Annotationen aufzuloesen, und faellt sonst um.
    sys.modules[name] = modul
    try:
        spec.loader.exec_module(modul)
    finally:
        del sys.modules[name]

    erwartet = {a.dateiname(i) for a in modul.PLAN for i in range(1, a.anfragen + 1)}
    assert erwartet == set(ALLE_AUFZEICHNUNGEN), (
        "Recorder und Testtabelle nennen verschiedene Aufzeichnungen"
    )


# --------------------------------------------------------------------------
# Der Fund: opendata.swiss nennt die Beschreibung `description`
# --------------------------------------------------------------------------
def _katalogzeilen(name: str) -> list[dict[str, Any]]:
    return fixture_json(name)["result"]["results"]


@pytest.mark.parametrize(
    "name",
    sorted(
        {n for _, _, ns in WERKZEUGE.values() for n in ns}
        & {"rtv_suche.json", "medienstruktur.json", "aktuell.json", "telekomstatistik.json"}
    ),
)
def test_der_katalog_nennt_die_beschreibung_description(name):
    """Der Fund, der diesen Ordner rechtfertigt.

    Der Code las `notes` — den Namen aus dem CKAN-Kern. opendata.swiss liefert
    das Feld unter `description`. Ergebnis: zu jedem Datensatz eine leere
    Beschreibung, in vier Werkzeugen, produktiv, bei gruener Suite.
    """
    zeilen = _katalogzeilen(name)
    assert zeilen, f"{name} traegt keine Trefferzeilen — neu aufzeichnen"
    for zeile in zeilen:
        assert "notes" not in zeile, "der Katalog kennt `notes` — Annahme neu pruefen"
        assert "description" in zeile, f"{zeile.get('name')} ohne `description`"


@pytest.mark.parametrize("werkzeug", sorted(KATALOG_WERKZEUGE))
async def test_die_beschreibung_kommt_im_ergebnis_an(werkzeug):
    """Und das ist die Zusicherung, die den Fund festhaelt.

    Sie faellt, sobald wieder ein Feldname geraten wird: aus der aufgezeichneten
    Antwort muss beim Modell eine nicht-leere Beschreibung ankommen.
    """
    klasse, eingabe, namen = WERKZEUGE[werkzeug]
    liste, feld = KATALOG_WERKZEUGE[werkzeug]
    daten = await _fahre(werkzeug, klasse, eingabe, namen)
    eintraege = daten[liste]
    assert eintraege, f"{werkzeug} liefert keine Eintraege aus der Aufzeichnung"
    leer = [e for e in eintraege if not (e.get(feld) or "").strip()]
    assert not leer, f"{werkzeug}: {len(leer)} von {len(eintraege)} ohne Beschreibung"


@pytest.mark.parametrize("werkzeug", sorted(KATALOG_WERKZEUGE))
async def test_der_titel_kommt_auf_deutsch_an(werkzeug):
    """Titel liegt als Sprach-Dict vor; ein `str()` darauf ergaebe `{'de': …}`."""
    klasse, eingabe, namen = WERKZEUGE[werkzeug]
    liste, _ = KATALOG_WERKZEUGE[werkzeug]
    daten = await _fahre(werkzeug, klasse, eingabe, namen)
    feld = "name" if werkzeug == "bakom_rtv_suche" else "titel"
    for eintrag in daten[liste]:
        titel = eintrag[feld]
        assert titel and not titel.startswith("{"), f"kein deutscher Titel: {titel!r}"


def test_titel_und_beschreibung_sind_sprach_dicts():
    """Der Grund, warum es `_ckan_de` gibt — und warum ein `str()` nicht reicht."""
    zeile = _katalogzeilen("rtv_suche.json")[0]
    for feld in ("title", "description"):
        assert isinstance(zeile[feld], dict), f"{feld} ist kein Sprach-Dict"
        assert "de" in zeile[feld], f"{feld} fuehrt kein Deutsch"


# --------------------------------------------------------------------------
# Die Werkzeuge, jedes an seiner eigenen Antwort
# --------------------------------------------------------------------------
@pytest.mark.parametrize("werkzeug", sorted(WERKZEUGE))
async def test_jedes_werkzeug_liest_seine_aufgezeichnete_antwort(werkzeug):
    """Der eigentliche Punkt: jede Abfrage bekommt *ihre* Antwort.

    Alle mit derselben zu bedienen hiesse, die Aufzeichnung gegen eine Abfrage
    zu halten, die sie nicht beantwortet — genau der Fehler, den eine Fixture je
    Abfrage verhindern soll. Der Client hier gibt sie deshalb der Reihe nach
    aus und faellt, wenn eine Anfrage zu viel kommt.
    """
    klasse, eingabe, namen = WERKZEUGE[werkzeug]
    daten = await _fahre(werkzeug, klasse, eingabe, namen)
    assert isinstance(daten, dict) and daten, f"{werkzeug} liefert nichts"


async def test_die_abdeckung_kennt_beide_richtungen():
    """Ein Fixture-Satz, in dem jede Abfrage «ja» sagt, belegt die Nein-Seite nicht.

    Aufgezeichnet sind Zuerich HB und das Grimselgebiet. Am Grimsel meldet der
    Glasfaser-Layer `features: []` — daraus muss ein «nein» werden und kein
    Fehler, sonst kann das Modell «dort gibt es keine Glasfaser» nicht von
    «die Abfrage ist gescheitert» unterscheiden.
    """
    assert fixture_json("multi_standort_4.json")["features"] == [], (
        "die Aufzeichnung fuer den Grimsel traegt Features — dann belegt sie das Nein nicht"
    )
    klasse, eingabe, namen = WERKZEUGE["bakom_multi_standort_konnektivitaet"]
    daten = await _fahre("bakom_multi_standort_konnektivitaet", klasse, eingabe, namen)

    nach_name = {s["name"]: s for s in daten["standorte"]}
    assert nach_name["Zürich HB"]["glasfaser_fttb"] is True
    assert nach_name["Grimsel"]["glasfaser_fttb"] is False
    assert nach_name["Grimsel"]["fehler"] is None, "ein leerer Layer ist kein Fehler"
    assert daten["zusammenfassung"]["mit_glasfaser"] == 1


async def test_die_sendeanlagen_tragen_koordinaten_und_distanz():
    """Ohne Koordinate im Feature bliebe `distanz_m` still `None` und die Liste unsortiert."""
    klasse, eingabe, namen = WERKZEUGE["bakom_sendeanlagen_suche"]
    daten = await _fahre("bakom_sendeanlagen_suche", klasse, eingabe, namen)
    anlagen = daten["anlagen"]
    assert anlagen, "die Aufzeichnung liefert keine Anlagen"
    distanzen = [a["distanz_m"] for a in anlagen]
    assert all(d is not None for d in distanzen), "eine Anlage ohne Distanz"
    assert distanzen == sorted(distanzen), "nach Distanz sortiert ist die Zusage"


# --------------------------------------------------------------------------
# LINDAS: eine Abfrage, die aus der Antwort der vorigen gebaut wird
# --------------------------------------------------------------------------
async def test_der_katalog_listet_die_auswertungen():
    daten = await _fahre("bakom_medien_statistik", "MedienStatistikInput", {}, MEDIEN_KATALOG)
    assert daten["total"] > 1
    assert CUBE_THEMA in daten["auswertungen"]


async def test_die_auswertung_faehrt_alle_drei_abfragen():
    """Titel → Dimensionen → Beobachtungen: die zweite und dritte Abfrage
    entstehen aus der Antwort der ersten. Eine gemeinsame Fixture fuer alle drei
    wuerde das nicht zeigen."""
    client, protokoll = _klient(*MEDIEN_AUSWERTUNG)
    params = server.MedienStatistikInput(thema=CUBE_THEMA, limit=10, response_format="json")
    daten = json.loads(await server.bakom_medien_statistik(params, _ctx(client)))

    assert len(protokoll) == 3, "das Werkzeug hat eine Abfrage verschluckt"
    assert daten["auswertung"] == CUBE_THEMA
    assert daten["beobachtungen"], "keine Beobachtungen aus der Aufzeichnung"


async def test_die_cube_version_geht_als_zahl_in_die_zweite_abfrage():
    """Die Quelle liefert die Version als Zeichenkette, SPARQL braucht eine Zahl.

    `schema:version "6"` traefe nichts — das Literal muss ohne Anfuehrungszeichen
    stehen. Diese Zusicherung liest die tatsaechlich abgeschickte Abfrage.
    """
    binding = fixture_json("medien_auswertung_1.json")["results"]["bindings"][0]
    version = binding["version"]["value"]
    assert isinstance(version, str), "die Quelle liefert die Version nicht mehr als Zeichenkette"

    client, protokoll = _klient(*MEDIEN_AUSWERTUNG)
    params = server.MedienStatistikInput(thema=CUBE_THEMA, limit=10, response_format="json")
    await server.bakom_medien_statistik(params, _ctx(client))

    zweite = protokoll[1][1]["data"]["query"]
    assert f"schema:version {int(version)}" in zweite
    assert f'schema:version "{version}"' not in zweite


def test_die_drei_sparql_antworten_tragen_verschiedene_variablen():
    """Der Grund, je Abfrage aufzuzeichnen: die Antwortformen sind nicht gleich."""
    formen = {n: frozenset(fixture_json(n)["head"]["vars"]) for n in MEDIEN_AUSWERTUNG}
    assert len(set(formen.values())) == 3, f"gleiche Variablen in mehreren Antworten: {formen}"
    for name, vars_ in formen.items():
        assert vars_, f"{name} nennt keine Variablen im Kopf"


def test_katalog_und_auswertung_meinen_denselben_cube():
    """Sonst belegen zwei Dateien zwei Dinge und niemandem faellt es auf."""
    katalog = {
        b["name"]["value"] for b in fixture_json("medien_katalog.json")["results"]["bindings"]
    }
    gewaehlt = fixture_json("medien_auswertung_1.json")["results"]["bindings"][0]["name"]["value"]
    assert gewaehlt == CUBE_THEMA
    assert gewaehlt in katalog, "die Auswertung zeigt einen Cube, den der Katalog nicht kennt"


# --------------------------------------------------------------------------
# Die Gegenrichtung
# --------------------------------------------------------------------------
async def test_eine_leere_trefferliste_bleibt_eine_leere_trefferliste():
    """`results: []` ist eine Aussage der Quelle: dazu gibt es nichts.

    Das darf nicht als Fehler herauskommen — sonst kann das Modell einen echten
    Negativtreffer nicht von einem Ausfall unterscheiden.
    """
    leer = json.dumps({"result": {"count": 0, "results": []}})
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(
        return_value=httpx.Response(
            200, text=leer, request=httpx.Request("GET", server.OPENDATA_SWISS_API)
        )
    )
    params = server.TelekomStatInput(thema="quantenverschluesselung", response_format="json")
    daten = json.loads(await server.bakom_aktuell(params, _ctx(client)))
    assert daten["datensaetze"] == []
    assert daten.get("hinweis"), "eine leere Suche soll einen Hinweis tragen, keinen Fehler"


async def test_ein_abbruch_bleibt_ein_fehler():
    """Und die andere Haelfte: ein Ausfall darf nicht als leeres Ergebnis erscheinen."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.TimeoutException("read timeout"))
    with pytest.raises(ToolError):
        await server.bakom_aktuell(server.TelekomStatInput(thema="medien"), _ctx(client))


# --------------------------------------------------------------------------
# Der Nachweis, nachgerechnet
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(n for n in recorded_names() if n != "PROVENANCE.md"))
def test_die_pruefsumme_im_nachweis_stimmt(name):
    """Eine Pruefsumme, die niemand nachrechnet, ist Zierde.

    Sie steht im Nachweis, um genau einen Fall zu fangen: eine Aufzeichnung,
    die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort
    ist wieder eine erfundene — und von aussen ist ihr das nicht anzusehen.
    Ohne diesen Test faengt die Summe nichts.

    Gerechnet wird ueber die Bytes auf der Platte, nicht ueber den Loader:
    genau die hat der Recorder gehasht, und ein Loader, der unterwegs dekodiert
    oder normalisiert, wuerde die Pruefung gegen sich selbst fuehren.
    """
    import hashlib
    import re
    from pathlib import Path

    teile = provenance().split(f"## `{name}`", 1)
    assert len(teile) == 2, f"{name} hat keinen Block in PROVENANCE.md"
    treffer = re.search(r"\*\*SHA-256:\*\*\s*`([0-9a-f]{64})`", teile[1].split("## ", 1)[0])
    assert treffer, f"{name} steht ohne Pruefsumme im Nachweis"
    roh = (Path(__file__).resolve().parent / "fixtures" / name).read_bytes()
    assert hashlib.sha256(roh).hexdigest() == treffer.group(1), (
        f"{name} weicht vom Nachweis ab — von Hand nachgebessert? Neu aufzeichnen."
    )
