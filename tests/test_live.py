"""Live-Tests gegen die echten Quellen.

Loest test_integration.py, test_20_szenarien.py, test_20_neue_szenarien.py und
test_scenarios_20.py ab. Die vier Module stammten aus Skripten: jeder Testkoerper
fing `Exception` ab und buchte sie auf ein modulweites `TestResult`, das nur auf
stdout landete — pytest sah nichts und meldete gruen, egal was die Quelle
antwortete. Hier faellt ein Test, wenn er faellt.

Ausgeschlossen aus der CI per `-m "not live"`, gefahren von
`.github/workflows/live-tests.yml`. Der `live_ctx` kommt aus `conftest.py`, aus
dem echten `lifespan(mcp)`.

Reine Validierungs- und Katalog-Szenarien der Altmodule sind hier nicht mehr
drin: sie haben nie ein Netz beruehrt und laufen jetzt in `test_unit.py`, wo die
CI sie auch wirklich prueft.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bakom_mcp.server import (  # noqa: E402
    AntennaSearchInput,
    BroadbandCoverageInput,
    BroadbandSpeed,
    CoordinateInput,
    MediaType,
    MedienStatistikInput,
    MobileCoverageInput,
    MobilGenerations,
    MultiLocationInput,
    ResponseFormat,
    RTVSearchInput,
    TelekomStatInput,
    bakom_aktuell,
    bakom_broadband_coverage,
    bakom_frequenzdaten,
    bakom_glasfaser_verfuegbarkeit,
    bakom_medien_statistik,
    bakom_medienstruktur_info,
    bakom_mobilfunk_abdeckung,
    bakom_multi_standort_konnektivitaet,
    bakom_rtv_suche,
    bakom_sendeanlagen_suche,
    bakom_telekomstatistik_uebersicht,
)

pytestmark = pytest.mark.live


# ---------------------------------------------------------------------------
# Orte
# ---------------------------------------------------------------------------
LEUTSCHENBACH = (47.4148, 8.5654)
ZUERICH_HB = (47.3779, 8.5403)
BERN = (46.9467, 7.4444)
GENF = (46.2044, 6.1432)
BASEL = (47.5596, 7.5886)
LUGANO = (46.0037, 8.9511)
LAUSANNE = (46.5197, 6.6323)
LUZERN = (47.0502, 8.3093)
ST_GALLEN = (47.4245, 9.3767)
WAEDENSWIL = (47.2254, 8.6697)
WINTERTHUR = (47.4984, 8.7285)
APPENZELL = (47.3303, 9.4086)
CHUR = (46.8499, 9.5329)
DAVOS = (46.8027, 9.8360)
ZERMATT = (46.0207, 7.7491)
ST_MORITZ = (46.4908, 9.8355)
JUNGFRAUJOCH = (46.5472, 7.9853)
BIEL = (47.1368, 7.2467)
EMMENTAL = (46.9350, 7.7340)

# Randlagen des erlaubten Koordinatenbereichs
CHIASSO = (45.8300, 9.0300)  # Suedgrenze
SCHAFFHAUSEN = (47.8900, 8.6300)  # Nordgrenze
SW_ECKE = (45.8, 5.9)  # exakter Sued-West-Grenzwert
OST_RAND = (46.9, 10.55)
WEST_RAND = (46.5, 5.95)


# ---------------------------------------------------------------------------
# Helfer
# ---------------------------------------------------------------------------
def text(output: object) -> str:
    """Prueft, dass das Tool Inhalt und keine Fehlermeldung geliefert hat.

    Die Tools geben Fehler als Text zurueck statt zu werfen (OBS-002), immer
    beginnend mit «Fehler: ». Ein `len(output) > 30` — so stand es in den
    Altmodulen — ist auf jeder dieser Meldungen erfuellt und haette Drift
    nicht bemerkt.
    """
    assert isinstance(output, str), f"Kein String, sondern {type(output)!r}"
    assert not output.startswith("Fehler:"), f"Tool meldet Fehler: {output[:200]}"
    assert output.strip(), "Leere Antwort"
    return output


def daten(output: object) -> dict[str, Any]:
    """Wie `text`, gibt aber das geparste JSON zurueck."""
    parsed = json.loads(text(output))
    assert isinstance(parsed, dict), f"JSON ist kein Objekt: {type(parsed)!r}"
    return parsed


def standort_stimmt(data: dict[str, Any], ort: tuple[float, float]) -> None:
    """Die Antwort spiegelt die angefragten Koordinaten zurueck."""
    lat, lon = ort
    assert "standort" in data, "Feld 'standort' fehlt"
    assert abs(data["standort"]["lat"] - lat) < 0.01, data["standort"]
    assert abs(data["standort"]["lon"] - lon) < 0.01, data["standort"]


# ---------------------------------------------------------------------------
# Breitband
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("ort", "speed"),
    [
        (LEUTSCHENBACH, BroadbandSpeed.S100),
        (LUGANO, BroadbandSpeed.S30),
        (BASEL, BroadbandSpeed.S500),
        (BERN, BroadbandSpeed.S1000),
    ],
)
async def test_breitband_markdown(live_ctx, ort, speed):
    """Breitbandabdeckung als Markdown, verschiedene Orte und Stufen."""
    output = text(
        await bakom_broadband_coverage(
            BroadbandCoverageInput(latitude=ort[0], longitude=ort[1], min_speed_mbps=speed),
            live_ctx,
        )
    )
    assert "Breitbandversorgung" in output
    assert "Datenquelle" in output


@pytest.mark.parametrize("speed", list(BroadbandSpeed))
async def test_breitband_alle_geschwindigkeitsstufen(live_ctx, speed):
    """Jede angebotene Geschwindigkeitsstufe liefert Daten (Genf)."""
    data = daten(
        await bakom_broadband_coverage(
            BroadbandCoverageInput(
                latitude=GENF[0],
                longitude=GENF[1],
                min_speed_mbps=speed,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert data["geschwindigkeit_mbps"] == int(speed.value)
    standort_stimmt(data, GENF)


@pytest.mark.parametrize(
    "ort", [CHIASSO, SCHAFFHAUSEN, SW_ECKE, OST_RAND, WEST_RAND], ids=lambda o: f"{o[0]}_{o[1]}"
)
async def test_breitband_randkoordinaten(live_ctx, ort):
    """Die Randlagen des erlaubten Bereichs werden beantwortet, nicht abgelehnt."""
    data = daten(
        await bakom_broadband_coverage(
            BroadbandCoverageInput(
                latitude=ort[0],
                longitude=ort[1],
                min_speed_mbps=BroadbandSpeed.S100,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    standort_stimmt(data, ort)


# ---------------------------------------------------------------------------
# Glasfaser
# ---------------------------------------------------------------------------
async def test_glasfaser_markdown(live_ctx):
    """Glasfaserverfuegbarkeit als Markdown (Waedenswil)."""
    output = text(
        await bakom_glasfaser_verfuegbarkeit(
            CoordinateInput(latitude=WAEDENSWIL[0], longitude=WAEDENSWIL[1]), live_ctx
        )
    )
    assert "Glasfaser" in output or "FTTB" in output


@pytest.mark.parametrize(
    "ort", [APPENZELL, LUGANO, WINTERTHUR], ids=["appenzell", "lugano", "winterthur"]
)
async def test_glasfaser_json_struktur(live_ctx, ort):
    """Das JSON-Schema haelt an Stadt- wie Landstandorten."""
    data = daten(
        await bakom_glasfaser_verfuegbarkeit(
            CoordinateInput(latitude=ort[0], longitude=ort[1], response_format=ResponseFormat.JSON),
            live_ctx,
        )
    )
    standort_stimmt(data, ort)
    assert isinstance(data["glasfaser_verfuegbar"], bool), data["glasfaser_verfuegbar"]
    assert isinstance(data["standort"]["lat"], (int, float))
    assert isinstance(data["standort"]["lon"], (int, float))
    assert isinstance(data["datenquelle"], str) and len(data["datenquelle"]) > 5


# ---------------------------------------------------------------------------
# Multi-Standort
# ---------------------------------------------------------------------------
async def test_multi_standort_markdown(live_ctx):
    """Beide Standortnamen tauchen in der Markdown-Antwort auf."""
    output = text(
        await bakom_multi_standort_konnektivitaet(
            MultiLocationInput(
                locations=[
                    {
                        "name": "Schulhaus Leutschenbach",
                        "latitude": LEUTSCHENBACH[0],
                        "longitude": LEUTSCHENBACH[1],
                    },
                    {"name": "Bundeshaus Bern", "latitude": BERN[0], "longitude": BERN[1]},
                ]
            ),
            live_ctx,
        )
    )
    assert "Schulhaus Leutschenbach" in output
    assert "Bundeshaus Bern" in output


async def test_multi_standort_ein_einziger(live_ctx):
    """Ein einzelner Standort ist zulaessig (Untergrenze)."""
    output = text(
        await bakom_multi_standort_konnektivitaet(
            MultiLocationInput(
                locations=[
                    {"name": "Chiasso Grenzwert", "latitude": CHIASSO[0], "longitude": CHIASSO[1]}
                ]
            ),
            live_ctx,
        )
    )
    assert "Chiasso Grenzwert" in output


async def test_multi_standort_sprachregionen_json(live_ctx):
    """Alle Sprachregionen in einem Aufruf, Zusammenfassung zaehlt korrekt."""
    standorte = [
        {"name": "Zuerich (DE)", "latitude": ZUERICH_HB[0], "longitude": ZUERICH_HB[1]},
        {"name": "Genf (FR)", "latitude": GENF[0], "longitude": GENF[1]},
        {"name": "Lugano (IT)", "latitude": LUGANO[0], "longitude": LUGANO[1]},
        {"name": "Chur (GR)", "latitude": CHUR[0], "longitude": CHUR[1]},
        {"name": "St. Moritz (Engadin)", "latitude": ST_MORITZ[0], "longitude": ST_MORITZ[1]},
    ]
    data = daten(
        await bakom_multi_standort_konnektivitaet(
            MultiLocationInput(locations=standorte, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    assert data["zusammenfassung"]["total"] == 5
    assert len(data["standorte"]) == 5
    namen = [s["name"] for s in data["standorte"]]
    assert "Genf (FR)" in namen
    assert "Lugano (IT)" in namen


async def test_multi_standort_zehn_orte(live_ctx):
    """Zehn Standorte, jeder Name kommt in der Antwort vor."""
    orte = {
        "Zuerich": ZUERICH_HB,
        "Bern": BERN,
        "Genf": GENF,
        "Basel": BASEL,
        "Lugano": LUGANO,
        "Lausanne": LAUSANNE,
        "Luzern": LUZERN,
        "St. Gallen": ST_GALLEN,
        "Chur": CHUR,
        "Emmental": EMMENTAL,
    }
    output = text(
        await bakom_multi_standort_konnektivitaet(
            MultiLocationInput(
                locations=[
                    {"name": n, "latitude": o[0], "longitude": o[1]} for n, o in orte.items()
                ]
            ),
            live_ctx,
        )
    )
    for name in orte:
        assert name in output, f"{name} fehlt in der Antwort"


async def test_multi_standort_maximum_zwanzig(live_ctx):
    """Der Maximalwert von 20 Standorten wird vollstaendig verarbeitet."""
    standorte = [
        {"name": f"Standort {i:02d}", "latitude": 46.5 + i * 0.05, "longitude": 7.0 + i * 0.1}
        for i in range(20)
    ]
    data = daten(
        await bakom_multi_standort_konnektivitaet(
            MultiLocationInput(locations=standorte, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    assert data["zusammenfassung"]["total"] == 20
    assert len(data["standorte"]) == 20


async def test_multi_standort_sonderzeichen(live_ctx):
    """Umlaute, Akzente und Schraegstriche ueberleben den Roundtrip."""
    standorte = [
        {"name": "Zürich Oerlikon", "latitude": ZUERICH_HB[0], "longitude": ZUERICH_HB[1]},
        {"name": "Genève Aéroport", "latitude": GENF[0], "longitude": GENF[1]},
        {"name": "Biel/Bienne", "latitude": BIEL[0], "longitude": BIEL[1]},
    ]
    data = daten(
        await bakom_multi_standort_konnektivitaet(
            MultiLocationInput(locations=standorte, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    namen = [s["name"] for s in data["standorte"]]
    assert "Zürich Oerlikon" in namen, "Umlaut nicht erhalten"
    assert "Genève Aéroport" in namen, "Akzent nicht erhalten"
    assert "Biel/Bienne" in namen, "Schraegstrich nicht erhalten"


async def test_multi_standort_meldet_fehlerhafte_standorte(live_ctx):
    """Ein unbrauchbarer Standort wird einzeln als Fehler ausgewiesen."""
    data = daten(
        await bakom_multi_standort_konnektivitaet(
            MultiLocationInput(
                locations=[
                    {"name": "Gueltig", "latitude": ZUERICH_HB[0], "longitude": ZUERICH_HB[1]},
                    {"name": "Ausserhalb", "latitude": 52.5, "longitude": 13.4},
                ],
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert data["zusammenfassung"]["total"] == 2
    fehler = [s for s in data["standorte"] if s.get("fehler")]
    assert len(fehler) >= 1, "Standort ausserhalb der Schweiz wurde nicht als Fehler markiert"


# ---------------------------------------------------------------------------
# Mobilfunk
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("ort", "generation"),
    [
        (ZUERICH_HB, MobilGenerations.G5),
        (ZUERICH_HB, MobilGenerations.G4),
        (JUNGFRAUJOCH, MobilGenerations.G3),
        (JUNGFRAUJOCH, MobilGenerations.G5),
    ],
)
async def test_mobilfunk_json(live_ctx, ort, generation):
    """Abdeckung je Generation, Stadt wie Bergregion."""
    data = daten(
        await bakom_mobilfunk_abdeckung(
            MobileCoverageInput(
                latitude=ort[0],
                longitude=ort[1],
                generation=generation,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert data["generation"] == generation.value
    assert "abgedeckt" in data
    standort_stimmt(data, ort)


async def test_mobilfunk_markdown(live_ctx):
    """5G-Abdeckung als Markdown."""
    output = text(
        await bakom_mobilfunk_abdeckung(
            MobileCoverageInput(
                latitude=ZUERICH_HB[0], longitude=ZUERICH_HB[1], generation=MobilGenerations.G5
            ),
            live_ctx,
        )
    )
    assert "5G" in output


# ---------------------------------------------------------------------------
# Sendeanlagen
# ---------------------------------------------------------------------------
async def test_sendeanlagen_markdown(live_ctx):
    """Anlagensuche als Markdown (Zuerich HB)."""
    output = text(
        await bakom_sendeanlagen_suche(
            AntennaSearchInput(latitude=ZUERICH_HB[0], longitude=ZUERICH_HB[1], radius_m=1000),
            live_ctx,
        )
    )
    assert "Mobilfunkanlagen" in output


@pytest.mark.parametrize("radius", [100, 1000, 5000])
async def test_sendeanlagen_radius_wird_uebernommen(live_ctx, radius):
    """Der angefragte Radius steht in der Antwort und die Liste ist eine Liste."""
    data = daten(
        await bakom_sendeanlagen_suche(
            AntennaSearchInput(
                latitude=GENF[0],
                longitude=GENF[1],
                radius_m=radius,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert data["radius_m"] == radius
    assert isinstance(data["anlagen"], list)


async def test_sendeanlagen_default_radius(live_ctx):
    """Ohne Angabe gilt der Standardradius von 1000 m."""
    data = daten(
        await bakom_sendeanlagen_suche(
            AntennaSearchInput(
                latitude=LUZERN[0], longitude=LUZERN[1], response_format=ResponseFormat.JSON
            ),
            live_ctx,
        )
    )
    assert data["radius_m"] == 1000


async def test_sendeanlagen_nach_distanz_sortiert(live_ctx):
    """Die Anlagen kommen aufsteigend nach Distanz."""
    data = daten(
        await bakom_sendeanlagen_suche(
            AntennaSearchInput(
                latitude=ZUERICH_HB[0],
                longitude=ZUERICH_HB[1],
                radius_m=5000,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    distanzen = [a["distanz_m"] for a in data["anlagen"] if a.get("distanz_m") is not None]
    assert distanzen, "Keine Anlage mit Distanzangabe im 5-km-Radius um Zuerich HB"
    assert distanzen == sorted(distanzen), distanzen


async def test_sendeanlagen_grosser_radius_findet_mindestens_so_viel(live_ctx):
    """5000 m liefert nicht weniger Anlagen als 100 m am selben Ort."""
    klein = daten(
        await bakom_sendeanlagen_suche(
            AntennaSearchInput(
                latitude=GENF[0],
                longitude=GENF[1],
                radius_m=100,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    gross = daten(
        await bakom_sendeanlagen_suche(
            AntennaSearchInput(
                latitude=GENF[0],
                longitude=GENF[1],
                radius_m=5000,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert len(gross["anlagen"]) >= len(klein["anlagen"])


# ---------------------------------------------------------------------------
# Frequenzdaten (Radio/TV-Sender)
# ---------------------------------------------------------------------------
async def test_frequenzdaten_markdown(live_ctx):
    """Sender in der Naehe als Markdown."""
    output = text(
        await bakom_frequenzdaten(
            CoordinateInput(latitude=ZUERICH_HB[0], longitude=ZUERICH_HB[1]), live_ctx
        )
    )
    assert any(wort in output for wort in ("Sender", "Radio", "TV"))


@pytest.mark.parametrize("ort", [LUGANO, ZERMATT], ids=["lugano", "zermatt"])
async def test_frequenzdaten_json(live_ctx, ort):
    """JSON-Struktur haelt auch im abgelegenen Tal."""
    data = daten(
        await bakom_frequenzdaten(
            CoordinateInput(latitude=ort[0], longitude=ort[1], response_format=ResponseFormat.JSON),
            live_ctx,
        )
    )
    standort_stimmt(data, ort)
    assert isinstance(data["sender"], list)
    assert "suchradius_m" in data


# ---------------------------------------------------------------------------
# Radio-/TV-Datensaetze (opendata.swiss)
#
# Das Tool liefert Datensaetze des BAKOM-Katalogs, keine einzelnen Sender —
# die stehen nur in der RTV-Datenbank, einer SPA ohne Schnittstelle. `kanton`
# und `media_type` gehen als Suchwort in die Volltextsuche und gewichten die
# Treffer; ein Test darf hier keine exakte Filterung behaupten.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("query", "media_type"),
    [
        ("SRF", MediaType.TV),
        ("RTS", MediaType.TV),
        ("RSI", MediaType.RADIO),
        ("Tele Züri", MediaType.TV),
    ],
)
async def test_rtv_suche_nach_sender(live_ctx, query, media_type):
    """Suchbegriffe aus allen drei Sprachregionen liefern Datensaetze."""
    output = text(
        await bakom_rtv_suche(RTVSearchInput(query=query, media_type=media_type), live_ctx)
    )
    assert "opendata.swiss" in output


async def test_rtv_ohne_query(live_ctx):
    """Ohne Suchbegriff kommt die vollstaendige Liste des Medientyps."""
    data = daten(
        await bakom_rtv_suche(
            RTVSearchInput(media_type=MediaType.TV, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    assert isinstance(data["resultate"], list)


async def test_rtv_nennt_quelle_und_grenzen(live_ctx):
    """Die Antwort benennt opendata.swiss als Quelle und die Art der Filterung.

    Vorher stand hier `datenquelle: "BAKOM RTV-Datenbank"` — eine Quelle, aus
    der die Daten nicht stammten.
    """
    data = daten(
        await bakom_rtv_suche(
            RTVSearchInput(
                media_type=MediaType.RADIO, kanton="ZH", response_format=ResponseFormat.JSON
            ),
            live_ctx,
        )
    )
    assert "resultate" in data
    assert data["suchanfrage"]["typ"] == "radio"
    assert data["datenquelle"] == "opendata.swiss – Datensatzkatalog des BAKOM"
    assert "filtern nicht exakt" in data["suchanfrage"]["filterung"]


async def test_rtv_kanton_wird_normalisiert(live_ctx):
    """Kleingeschriebenes Kuerzel wird uebernommen und beantwortet."""
    params = RTVSearchInput(media_type=MediaType.RADIO, kanton="ge")
    assert params.kanton == "GE", f"Kanton nicht normalisiert: {params.kanton}"
    text(await bakom_rtv_suche(params, live_ctx))


async def test_rtv_alle_medientypen(live_ctx):
    """MediaType.ALLE liefert eine gemischte Trefferliste."""
    data = daten(
        await bakom_rtv_suche(
            RTVSearchInput(
                media_type=MediaType.ALLE, kanton="BE", response_format=ResponseFormat.JSON
            ),
            live_ctx,
        )
    )
    assert "resultate" in data
    assert data["suchanfrage"]["typ"] in ("alle", "radio,tv")


@pytest.mark.parametrize("limit", [1, 5, 50])
async def test_rtv_limit_wird_eingehalten(live_ctx, limit):
    """Das Limit begrenzt die Trefferzahl tatsaechlich."""
    data = daten(
        await bakom_rtv_suche(
            RTVSearchInput(
                media_type=MediaType.RADIO,
                kanton="ZH",
                limit=limit,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert len(data["resultate"]) <= limit


async def test_rtv_ohne_treffer_bleibt_hilfreich(live_ctx):
    """Ein Sender, den es nicht gibt, fuehrt zu einer brauchbaren Antwort."""
    data = daten(
        await bakom_rtv_suche(
            RTVSearchInput(
                query="ZZZ-Nichtexistierender-Sender-XYZ",
                media_type=MediaType.TV,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert any(key in data for key in ("resultate", "datensaetze", "hinweis")), list(data)


# ---------------------------------------------------------------------------
# Medienstruktur
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("thema", ["radio", "online", "presse", "tv"])
async def test_medienstruktur(live_ctx, thema):
    """Jedes Medienthema liefert Datensaetze und weiterfuehrende Links."""
    data = daten(
        await bakom_medienstruktur_info(
            TelekomStatInput(thema=thema, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    assert "datensaetze" in data
    assert "weiterfuehrende_links" in data


# ---------------------------------------------------------------------------
# BAKOM Aktuell
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("thema", ["medien", "radio", "fernsehen", "breitband"])
async def test_bakom_aktuell(live_ctx, thema):
    """Zuletzt geaenderte Datensaetze je Thema, absteigend nach Datum."""
    data = daten(
        await bakom_aktuell(
            TelekomStatInput(thema=thema, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    assert data["total"] >= 1
    assert data["datenquelle"] == "opendata.swiss – Datensatzkatalog des BAKOM"
    daten_reihe = [ds["aktualisiert"] for ds in data["datensaetze"] if ds["aktualisiert"]]
    assert daten_reihe == sorted(daten_reihe, reverse=True), daten_reihe


async def test_bakom_aktuell_unbekanntes_thema_erfindet_nichts(live_ctx):
    """Frueher fiel ein unbekanntes Thema still auf die Medien-Highlights zurueck.

    Die Antwort trug dann `thema: "quantenverschluesselung"` und darunter die
    SRG-Initiative — eine Vorlage zum Konfabulieren.
    """
    data = daten(
        await bakom_aktuell(
            TelekomStatInput(thema="quantenverschluesselung", response_format=ResponseFormat.JSON),
            live_ctx,
        )
    )
    assert data["total"] == 0
    assert data["datensaetze"] == []
    assert "bakom.admin.ch" in data["hinweis"]


async def test_bakom_aktuell_markdown(live_ctx):
    """Markdown nennt die Grenze: Datensaetze, keine Medienmitteilungen."""
    output = text(await bakom_aktuell(TelekomStatInput(thema="medien"), live_ctx))
    assert "Datensätze" in output
    assert "keine Medienmitteilungen" in output


# ---------------------------------------------------------------------------
# Telekomstatistik
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "thema", ["breitband", "mobilfunk", "festnetz", "marktanteile", "haushaltszugang"]
)
async def test_telekomstatistik_json(live_ctx, thema):
    """Jedes Thema liefert Datensaetze, Themen-Echo und Quellenangabe."""
    data = daten(
        await bakom_telekomstatistik_uebersicht(
            TelekomStatInput(thema=thema, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    assert data["thema"] == thema
    assert "datensaetze" in data
    assert "datenquelle" in data


async def test_telekomstatistik_markdown(live_ctx):
    """Markdown-Ausgabe zum Thema Breitband, mit Quellen- und Lizenzangabe."""
    output = text(
        await bakom_telekomstatistik_uebersicht(TelekomStatInput(thema="breitband"), live_ctx)
    )
    assert "Quelle:" in output
    assert "CC BY 4.0" in output


# ---------------------------------------------------------------------------
# Tools uebergreifend
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ort", [DAVOS, CHUR], ids=["davos", "chur"])
async def test_konnektivitaetsprofil_konsistent(live_ctx, ort):
    """Breitband, Mobilfunk und Glasfaser melden denselben Standort zurueck."""
    breitband = daten(
        await bakom_broadband_coverage(
            BroadbandCoverageInput(
                latitude=ort[0],
                longitude=ort[1],
                min_speed_mbps=BroadbandSpeed.S100,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    mobilfunk = daten(
        await bakom_mobilfunk_abdeckung(
            MobileCoverageInput(
                latitude=ort[0],
                longitude=ort[1],
                generation=MobilGenerations.G5,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    glasfaser = daten(
        await bakom_glasfaser_verfuegbarkeit(
            CoordinateInput(latitude=ort[0], longitude=ort[1], response_format=ResponseFormat.JSON),
            live_ctx,
        )
    )
    for data in (breitband, mobilfunk, glasfaser):
        standort_stimmt(data, ort)


# ---------------------------------------------------------------------------
# Medienstatistik (LINDAS)
#
# Recall-Canary: Untergrenzen deutlich unter dem Ist-Wert. Der Test soll einen
# Kollaps fangen (Graph umbenannt, Scope geschrumpft), nicht bei jeder
# Bestandspflege des BAKOM rot werden.
# ---------------------------------------------------------------------------
async def test_medien_statistik_katalog(live_ctx):
    """Der Katalog listet die veroeffentlichten Auswertungen (Ist 2026-08: 73)."""
    data = daten(
        await bakom_medien_statistik(
            MedienStatistikInput(limit=100, response_format=ResponseFormat.JSON), live_ctx
        )
    )
    assert data["total"] >= 50, f"nur {data['total']} Auswertungen — Scope geschrumpft?"
    assert any("Marktanteile" in t for t in data["auswertungen"])


async def test_medien_statistik_marktanteile_radio(live_ctx):
    """Anchor: Marktanteile im Radiomarkt nach Sendergruppe."""
    data = daten(
        await bakom_medien_statistik(
            MedienStatistikInput(
                thema="Marktanteile Radiomarkt nach Sendergruppe",
                jahr=2024,
                response_format=ResponseFormat.JSON,
            ),
            live_ctx,
        )
    )
    assert data["auswertung"] == "Marktanteile Radiomarkt nach Sendergruppe"
    assert data["total"] >= 4, f"nur {data['total']} Sendergruppen"
    gruppen = {b["Sendergruppe"]: float(b["Marktanteil"]) for b in data["beobachtungen"]}
    assert "Radio SRG SSR" in gruppen
    assert 0 < gruppen["Radio SRG SSR"] <= 100
    assert all(b["Jahr"] == "2024" for b in data["beobachtungen"])


async def test_medien_statistik_mehrdeutig_fuehrt_zur_auswahl(live_ctx):
    """Ein unspezifisches Thema liefert die Titelliste statt einer willkuerlichen Zahl."""
    data = daten(
        await bakom_medien_statistik(
            MedienStatistikInput(
                thema="Reichweite", limit=100, response_format=ResponseFormat.JSON
            ),
            live_ctx,
        )
    )
    assert data["total"] >= 2
    assert "hinweis" in data


async def test_medien_statistik_ohne_treffer_nennt_naechsten_schritt(live_ctx):
    """Leermenge traegt einen konkreten naechsten Versuch."""
    data = daten(
        await bakom_medien_statistik(
            MedienStatistikInput(thema="Zzz-gibt-es-nicht", response_format=ResponseFormat.JSON),
            live_ctx,
        )
    )
    assert data["total"] == 0
    assert "ohne `thema`" in data["hinweis"]


async def test_medien_statistik_markdown(live_ctx):
    """Markdown nennt Quelle und Abdeckungsgrenze."""
    output = text(
        await bakom_medien_statistik(
            MedienStatistikInput(thema="Marktanteile Radiomarkt nach Sendergruppe"), live_ctx
        )
    )
    assert "Sendergruppe" in output
    assert "Gesamtbestand" in output
    assert "CC BY 4.0" in output
