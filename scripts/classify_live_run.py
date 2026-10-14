#!/usr/bin/env python3
"""Was hat der geplante Live-Lauf festgestellt — clear, finding, outage oder unknown?

WARUM DAS EIN SKRIPT IST UND KEIN YAML-BLOCK
--------------------------------------------
`if: failure()` kennt zwei Antworten: rot und nicht rot. Ein Live-Lauf hat
vier, und die letzten beiden sind die, die zaehlen:

  clear    Die Suite ist gelaufen und war gruen.
  finding  Die Suite ist gelaufen und etwas ist gefallen.
  outage   Die Suite ist gelaufen, und JEDER Fehlschlag ist eine Absage der
           Quelle (HTTP 5xx oder Zeitueberschreitung) — ueber den Vertrag
           sagt der Lauf nichts.
  unknown  Die Suite ist NICHT gelaufen — und niemand weiss, ob der Vertrag
           mit der Quelle noch haelt.

Ein gescheitertes `pip install`, ein Timeout, eine umbenannte Marke: alles
`unknown`, alles sieht unter `if: failure()` aus wie ein gebrochener Vertrag.
Und ein Lauf, in dem jeder Test uebersprungen wurde, sieht unter jedem
Exit-Code-Check aus wie Erfolg.

Diese Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Sie in einen
`run:`-Block zu schreiben hiesse, den einzigen Teil des Workflows, der etwas
behauptet, an die einzige Stelle zu legen, an der ihn niemand testen kann.
Deshalb steht sie hier, neben ihrem Test.

DER UEBERSPRUNGENE LAUF
-----------------------
Gemessen am 7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY`
ueberspringt die Live-Suite alle sechs Tests, und pytest endet mit 0. Ein
woechentlicher Job haette gemeldet: gruen. Geprueft haette er nichts — und ein
offenes Issue haette er zugemacht, mit einem Vergleich, den es nie gab.

`tests - skipped == 0` ist deshalb `unknown` und nicht `clear`. Ein Secret, das
niemand gesetzt hat, ist kein gruener Vertrag mit der Quelle; es ist gar keiner.

DIE QUELLE IST DAS JUNIT-XML, NICHT DER EXIT-CODE
-------------------------------------------------
Der Exit-Code von pytest sagt 0 fuer «alles gruen» und fuer «alles
uebersprungen» dasselbe. Das XML zaehlt Tests, Fehler, Fehlschlaege und
Uebersprungene getrennt, also wird es gelesen. Fehlt es, ist pytest gar nicht
bis zum Schreiben gekommen — auch das ist `unknown`, und zwar mit Grund.

WENN PYTEST NIE GESTARTET WURDE, IST DER EXIT-CODE EINE ERFINDUNG
-----------------------------------------------------------------
Bricht der Workflow ab, bevor er pytest aufruft — etwa weil ein Secret fehlt —,
dann hat er keinen Exit-Code zu melden. Wer an dieser Stelle einen erfindet,
schickt den Leser hinter einer Ursache her, die es nicht gibt: In
`swiss-ip-mcp` stand dort `--pytest-exit 127`, und diese Einordnung machte
daraus «pytest ist nicht bis zum Schreiben gekommen (Exit 127)» — 127 heisst
«command not found», also die Suche nach einem fehlenden Binary, wo in
Wahrheit nie ein Aufruf stattgefunden hatte.

Deshalb `--not-started`: Wer pytest nicht startet, sagt selbst warum, und diese
Einordnung reicht den Grund durch, statt einen zu konstruieren. Sie sieht dann
auch nicht ins XML — ein liegengebliebener Report aus einem frueheren Schritt
belegt nichts ueber einen Lauf, der nicht stattgefunden hat.

DIE GESTOERTE QUELLE IST KEIN BEFUND
------------------------------------
Gemessen am 14.10.2026 (Lauf 38547729127, Issue #106): Der erste Durchgang
verlor 2 Tests, die Wiederholung 60 s spaeter 7 — fast alle andere, sechsmal
HTTP 502, einmal Zeitueberschreitung, alle auf `ckan.opendata.swiss`. Eine
Stunde spaeter war alles gruen, ohne Aenderung am Code. Als `finding`
eingeordnet, hiess es im Issue, ein Netzwerk-Aussetzer sei «ausgeschlossen»:
die Wiederholung trennt einen Aussetzer von Drift nur, wenn die Stoerung
kuerzer ist als die Wartezeit.

Drift faellt an denselben Tests mit Zusicherungen; eine Stoerung an
wechselnden Tests mit einer Absage der Quelle. Deshalb `outage`, wenn jeder
einzelne Fehlschlag die Absage-Meldung aus `_handle_api_error` in `server.py`
traegt. Ein einziger anderer Fehlschlag — Zusicherung, 4xx, KeyError — macht
den Lauf zum `finding`: Ein 4xx ist eine echte Antwort, keine Stoerung.

Geprueft wird pro `<testcase>`, nicht pro Suite: Stimmt die Zahl der
gefundenen `<failure>`/`<error>` nicht mit den Zaehlern der Suite ueberein,
ist die Stoerung nicht belegt, und es bleibt `finding`.

Aufruf:
    python scripts/classify_live_run.py live-report.xml
    python scripts/classify_live_run.py live-report.xml --pytest-exit 1
    python scripts/classify_live_run.py live-report.xml --not-started "kein Secret"

Gibt `state=...` und `reason=...` auf stdout aus und haengt beides an
`$GITHUB_OUTPUT` an, wenn die Variable gesetzt ist. Der Exit-Code ist immer 0:
Ueber rot oder gruen entscheidet der Workflow, nicht dieser Reporter.
"""

from __future__ import annotations

import argparse
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

CLEAR = "clear"
FINDING = "finding"
OUTAGE = "outage"
UNKNOWN = "unknown"

# Woertlich aus `_handle_api_error` in src/bakom_mcp/server.py. Aendert sich
# dort ein Text, faellt `test_classify_live_run.ServerKopplungTest`. Gesucht
# statt am Anfang verglichen: pytest bettet die Meldung bei einem
# Fixture-Fehler in `failed on setup with "..."` ein. «nicht erreichbar» steht
# dort nur bei Status >= 500; eine Statuszahl im Muster pruefte nichts dazu.
OUTAGE_MARKERS: dict[str, re.Pattern[str]] = {
    "HTTP 5xx": re.compile(r"API-Server nicht erreichbar"),
    "Zeitueberschreitung": re.compile(r"Zeitüberschreitung\. API antwortet nicht"),
}


def _outage_kinds(suites: list[ET.Element], expected: int) -> dict[str, int] | None:
    """Zaehlt die Absagen der Quelle je Art — oder None, wenn das nicht alles ist.

    `expected` ist failures + errors laut Suite. Jeder `<failure>`/`<error>`
    muss eine Absage-Meldung tragen, und es muessen genau so viele sein: Sonst
    gibt es einen Fehlschlag, den diese Pruefung nicht gesehen hat.
    """
    kinds: dict[str, int] = {}
    seen = 0
    for suite in suites:
        for case in suite.iter("testcase"):
            for result in case:
                if result.tag not in ("failure", "error"):
                    continue
                seen += 1
                message = result.get("message") or ""
                kind = next(
                    (k for k, rx in OUTAGE_MARKERS.items() if rx.search(message)),
                    None,
                )
                if kind is None:
                    return None
                kinds[kind] = kinds.get(kind, 0) + 1
    if seen != expected:
        return None
    return kinds


def classify(
    report: Path,
    pytest_exit: int | None = None,
    not_started: str | None = None,
) -> tuple[str, str]:
    """(state, reason) aus einem JUnit-XML und optional dem pytest-Exit-Code.

    `not_started` schlaegt alles andere: Wurde pytest nie aufgerufen, sagt
    weder der Report noch ein Exit-Code etwas ueber den Lauf.
    """
    if not_started:
        return UNKNOWN, not_started
    if not report.is_file():
        return (
            UNKNOWN,
            f"kein Report unter {report} — pytest ist nicht bis zum Schreiben "
            "gekommen" + (f" (Exit {pytest_exit})" if pytest_exit is not None else ""),
        )
    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, OSError) as exc:
        return UNKNOWN, f"{report} ist nicht lesbar: {exc}"

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return UNKNOWN, f"{report} enthaelt keine testsuite"

    def total(attr: str) -> int:
        return sum(int(s.get(attr) or 0) for s in suites)

    tests, failures, errors, skipped = (
        total("tests"),
        total("failures"),
        total("errors"),
        total("skipped"),
    )

    if failures or errors:
        kinds = _outage_kinds(suites, failures + errors)
        if kinds is not None:
            detail = ", ".join(f"{n}x {k}" for k, n in sorted(kinds.items()))
            return (
                OUTAGE,
                f"{failures + errors} von {tests} Test(s) an einer Absage der Quelle "
                f"gescheitert ({detail}), kein anderer Fehlschlag — Stoerung, kein "
                "Befund ueber den Vertrag",
            )
        return (
            FINDING,
            f"{failures} Fehlschlag/Fehlschlaege und {errors} Fehler von {tests} Test(s)",
        )
    if tests == 0:
        return (
            UNKNOWN,
            "null Tests eingesammelt — die Marke oder die Dateien haben sich "
            "bewegt, und ein Erfolg ohne Test ist kein Erfolg",
        )
    if tests - skipped == 0:
        return (
            UNKNOWN,
            f"alle {tests} Test(s) uebersprungen — meist ein fehlendes Secret oder "
            "eine nicht erfuellte Vorbedingung. Geprueft wurde nichts",
        )
    return CLEAR, f"{tests - skipped} von {tests} Test(s) ausgefuehrt, alle gruen"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="classify_live_run")
    ap.add_argument("report", type=Path, help="Pfad zum JUnit-XML von pytest")
    ap.add_argument("--pytest-exit", type=int, default=None)
    ap.add_argument(
        "--not-started",
        default=None,
        help="Grund, warum pytest gar nicht erst aufgerufen wurde. Setzt `unknown`.",
    )
    args = ap.parse_args(argv)

    state, reason = classify(args.report, args.pytest_exit, args.not_started)
    print(f"state={state}")
    print(f"reason={reason}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Zeilenumbruch raus, bevor der Grund in `$GITHUB_OUTPUT` geht: Die
        # `key=value`-Form endet an der ersten neuen Zeile, und was danach
        # steht, liest der Runner als naechstes Output. Ein Grund aus einer
        # Parser-Meldung oder aus `--not-started` koennte so ein `state=clear`
        # nachschieben und den roten Lauf gruen faerben.
        flat = " ".join(reason.split())
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\n")
            fh.write(f"reason={flat}\n")
    # Immer 0: Ueber rot oder gruen entscheidet der Workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
