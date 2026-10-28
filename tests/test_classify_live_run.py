#!/usr/bin/env python3
"""Tests fuer scripts/classify_live_run.py — die drei Antworten eines Live-Laufs.

Die Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Genau deshalb
steht sie in einem Skript und nicht in einem `run:`-Block: So kann jemand sie
gegen die Faelle halten, aus denen sie entstanden ist.

Der wichtigste Fall ist `test_alle_uebersprungen_ist_nicht_gruen`. Gemessen am
7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY` ueberspringt die
Live-Suite alle sechs Tests und pytest endet mit 0. Ein Job, der das als gruen
bucht, schliesst ein offenes Issue mit einem Vergleich, den es nie gab.

Kein Netz. Die Faelle zur gestoerten Quelle (`EchtesJunitTest`) lassen pytest
selbst das XML schreiben, mit den Meldungen aus `_handle_api_error`: Ein von
Hand geschriebenes `<failure message=...>` kodierte nur die Annahme, wie pytest
die Meldung ablegt — und koennte sie nicht widerlegen.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import classify_live_run as clr  # noqa: E402


def write(tmp: Path, xml: str) -> Path:
    path = tmp / "live-report.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def suite(tests: int, failures: int = 0, errors: int = 0, skipped: int = 0) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest" tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}"></testsuite></testsuites>'
    )


def cli(*extra: str) -> tuple[str, str]:
    """Ruft `main` mit gesetztem $GITHUB_OUTPUT und liest zurueck, was ankam."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gh-output"
        out.write_text("", encoding="utf-8")
        os.environ["GITHUB_OUTPUT"] = str(out)
        try:
            clr.main([str(Path(tmp) / "live-report.xml"), *extra])
        finally:
            del os.environ["GITHUB_OUTPUT"]
        written = out.read_text(encoding="utf-8")
    werte = dict(line.split("=", 1) for line in written.splitlines() if line)
    return werte["state"], werte["reason"]


class ClassifyTest(unittest.TestCase):
    def _state(self, xml: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(write(Path(tmp), xml))

    def test_alles_gruen_ist_clear(self):
        state, reason = self._state(suite(tests=3))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("3 von 3", reason)

    def test_ein_fehlschlag_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_ein_fehler_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, errors=1))
        self.assertEqual(state, clr.FINDING)

    def test_alle_uebersprungen_ist_nicht_gruen(self):
        """swiss-transport-mcp ohne TRANSPORT_API_KEY: 6 von 6 uebersprungen."""
        state, reason = self._state(suite(tests=6, skipped=6))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("uebersprungen", reason)

    def test_teilweise_uebersprungen_ist_gruen(self):
        """Ein einzelner Skip ist eine Entscheidung im Test, kein Ausfall."""
        state, reason = self._state(suite(tests=6, skipped=5))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("1 von 6", reason)

    def test_null_tests_ist_kein_erfolg(self):
        """Die Marke umbenannt, die Dateien verschoben — pytest meldet trotzdem 0."""
        state, reason = self._state(suite(tests=0))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("null Tests", reason)

    def test_ein_fehlschlag_schlaegt_uebersprungene(self):
        state, _ = self._state(suite(tests=6, skipped=5, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_mehrere_testsuites_werden_summiert(self):
        xml = (
            "<testsuites>"
            '<testsuite tests="2" failures="0" errors="0" skipped="2"/>'
            '<testsuite tests="3" failures="0" errors="0" skipped="0"/>'
            "</testsuites>"
        )
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)

    def test_eine_einzelne_testsuite_ohne_huelle(self):
        xml = '<testsuite tests="2" failures="0" errors="0" skipped="0"/>'
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)


# Ein Probelauf mit echten Fehlschlaegen. Jeder Fall in `EchtesJunitTest` waehlt
# per `-k` die Tests aus, die in seinem Lauf fallen sollen; pytest schreibt das
# XML so, wie es der Live-Workflow liest.
PROBE = textwrap.dedent(
    """
    import httpx
    import pytest

    from bakom_mcp.server import _raise_api_error

    URL = "https://ckan.opendata.swiss/api/3/action/package_search"


    def status(code):
        req = httpx.Request("GET", URL)
        return httpx.HTTPStatusError(
            "x", request=req, response=httpx.Response(code, request=req)
        )


    def test_http_502():
        _raise_api_error(status(502))


    def test_http_504():
        _raise_api_error(status(504))


    def test_timeout():
        _raise_api_error(httpx.ReadTimeout("t", request=httpx.Request("GET", URL)))


    def test_http_400():
        _raise_api_error(status(400))


    def test_http_404():
        _raise_api_error(status(404))


    def test_zusicherung():
        assert "description" in {"notes": ""}


    def test_gruen():
        pass


    @pytest.fixture
    def quelle_weg():
        _raise_api_error(status(503))


    def test_setup_502(quelle_weg):
        pass
    """
)


def junit_aus_pytest(tmp: Path, auswahl: str) -> Path:
    """Laesst pytest den Probelauf fahren und gibt den Pfad zum JUnit-XML zurueck."""
    (tmp / "test_probe.py").write_text(PROBE, encoding="utf-8")
    report = tmp / "live-report.xml"
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT / "src"), env.get("PYTHONPATH")) if p)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-k",
            auswahl,
            f"--junitxml={report}",
            "test_probe.py",
        ],
        cwd=tmp,
        env=env,
        capture_output=True,
        check=False,
    )
    if not report.is_file():
        raise AssertionError(f"pytest hat kein XML geschrieben (Auswahl {auswahl!r})")
    return report


class EchtesJunitTest(unittest.TestCase):
    """Stoerung der Quelle vs. Befund — am XML, das pytest wirklich schreibt.

    Ausgangsfall 14.10.2026, Lauf 38547729127: 6x HTTP 502, 1x
    Zeitueberschreitung, alle auf ckan.opendata.swiss, beim naechsten Lauf
    alles gruen. Eingeordnet als `finding`, behauptete das Issue, ein
    Netzwerk-Aussetzer sei ausgeschlossen.
    """

    def _classify(self, auswahl: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(junit_aus_pytest(Path(tmp), auswahl))

    def test_nur_5xx_und_zeitueberschreitung_ist_stoerung(self):
        state, reason = self._classify("http_502 or http_504 or timeout or gruen")
        self.assertEqual(state, clr.OUTAGE)
        self.assertIn("2x HTTP 5xx", reason)
        self.assertIn("1x Zeitueberschreitung", reason)
        self.assertIn("3 von 4", reason)

    def test_nur_zeitueberschreitung_ist_stoerung(self):
        state, _ = self._classify("timeout")
        self.assertEqual(state, clr.OUTAGE)

    def test_absage_im_fixture_setup_ist_stoerung(self):
        """pytest legt sie als <error> ab, eingebettet in `failed on setup with`."""
        state, reason = self._classify("setup_502")
        self.assertEqual(state, clr.OUTAGE)
        self.assertIn("1x HTTP 5xx", reason)

    def test_eine_zusicherung_neben_502_ist_ein_befund(self):
        state, _ = self._classify("http_502 or zusicherung")
        self.assertEqual(state, clr.FINDING)

    def test_400_ist_ein_befund(self):
        """Ein 4xx ist eine echte Antwort der Quelle (CLAUDE.md: «Ein 4xx ist kein Nein»)."""
        state, _ = self._classify("http_400")
        self.assertEqual(state, clr.FINDING)

    def test_404_neben_502_ist_ein_befund(self):
        state, _ = self._classify("http_502 or http_404")
        self.assertEqual(state, clr.FINDING)


class StoerungRandfaelleTest(unittest.TestCase):
    """Was pytest so nicht schreibt, aber ein anderer Reporter koennte."""

    def _state(self, xml: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(write(Path(tmp), xml))[0]

    def test_zaehler_ohne_testcases_beweist_keine_stoerung(self):
        """Die Suite meldet einen Fehlschlag, zeigt ihn aber nicht: nicht belegt."""
        self.assertEqual(self._state(suite(tests=3, failures=1)), clr.FINDING)

    def test_ein_ungesehener_fehlschlag_macht_den_befund(self):
        xml = (
            '<testsuite tests="3" failures="2" errors="0" skipped="0">'
            '<testcase name="a"><failure message="ToolError: Fehler: API-Server '
            'nicht erreichbar (HTTP 502)."/></testcase>'
            '<testcase name="b"/><testcase name="c"/>'
            "</testsuite>"
        )
        self.assertEqual(self._state(xml), clr.FINDING)

    def test_fehlschlag_ohne_meldung_ist_ein_befund(self):
        xml = (
            '<testsuite tests="1" failures="1" errors="0" skipped="0">'
            '<testcase name="a"><failure/></testcase>'
            "</testsuite>"
        )
        self.assertEqual(self._state(xml), clr.FINDING)


class ServerKopplungTest(unittest.TestCase):
    """Die Marker in classify_live_run.py sind Texte aus `_handle_api_error`.

    Wird dort eine Meldung umformuliert, ordnet der Live-Workflow eine
    Stoerung still wieder als Befund ein — und kein anderer Test faellt.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "src"))
        import httpx

        from bakom_mcp.server import _handle_api_error

        cls.httpx = httpx
        cls.handle = staticmethod(_handle_api_error)

    def _status(self, code: int) -> str:
        req = self.httpx.Request("GET", "https://ckan.opendata.swiss/")
        resp = self.httpx.Response(code, request=req)
        return self.handle(self.httpx.HTTPStatusError("x", request=req, response=resp))

    def _ist_stoerung(self, meldung: str) -> bool:
        return any(rx.search(meldung) for rx in clr.OUTAGE_MARKERS.values())

    def test_5xx_meldungen_sind_stoerungen(self):
        for code in (500, 502, 503, 504):
            with self.subTest(code=code):
                self.assertTrue(self._ist_stoerung(self._status(code)))

    def test_zeitueberschreitung_ist_eine_stoerung(self):
        meldung = self.handle(self.httpx.ReadTimeout("t"))
        self.assertTrue(self._ist_stoerung(meldung))

    def test_echte_antworten_sind_keine_stoerung(self):
        for code in (400, 403, 404, 429):
            with self.subTest(code=code):
                self.assertFalse(self._ist_stoerung(self._status(code)))

    def test_wms_absage_ist_keine_stoerung(self):
        # Ein umbenannter Layer ist Drift, kein Aussetzer: `finding`, nicht `outage`.
        from bakom_mcp.server import WmsAbsageError

        self.assertFalse(self._ist_stoerung(self.handle(WmsAbsageError("LayerNotDefined"))))


class MissingReportTest(unittest.TestCase):
    """Kein Report heisst: pytest kam nicht bis zum Schreiben. Nie clear."""

    def test_fehlender_report_ist_unknown(self):
        state, reason = clr.classify(Path("/nonexistent/live-report.xml"), pytest_exit=4)
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("Exit 4", reason)

    def test_kaputtes_xml_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<testsuite tests=")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)

    def test_xml_ohne_testsuite_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<irgendwas/>")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)


class NotStartedTest(unittest.TestCase):
    """pytest nie aufgerufen: Der Grund kommt vom Aufrufer, nicht vom Exit-Code.

    Beobachtet am 24.8.2026 in `swiss-ip-mcp`: Ohne Zugangsdaten meldete der
    Workflow `--pytest-exit 127`, und daraus wurde «pytest ist nicht bis zum
    Schreiben gekommen (Exit 127)». 127 heisst «command not found» — der Satz
    behauptete einen gescheiterten pytest-Aufruf, den es nie gab.
    """

    def test_grund_wird_woertlich_durchgereicht(self):
        state, reason = clr.classify(
            Path("/nonexistent/live-report.xml"),
            not_started="Secret ist nicht gesetzt",
        )
        self.assertEqual(state, clr.UNKNOWN)
        self.assertEqual(reason, "Secret ist nicht gesetzt")

    def test_kein_erfundener_pytest_lauf_in_der_begruendung(self):
        _, reason = clr.classify(
            Path("/nonexistent/live-report.xml"),
            not_started="Secret ist nicht gesetzt",
        )
        self.assertNotIn("pytest ist nicht bis zum Schreiben gekommen", reason)
        self.assertNotIn("Exit", reason)

    def test_ein_liegengebliebener_report_belegt_nichts(self):
        """Gruenes XML aus einem frueheren Schritt macht einen Nicht-Lauf nicht gruen."""
        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=3))
            state, reason = clr.classify(report, not_started="gar nicht gestartet")
        self.assertEqual(state, clr.UNKNOWN)
        self.assertEqual(reason, "gar nicht gestartet")

    def test_leerer_grund_ist_kein_grund(self):
        """Der Workflow reicht `--not-started` nur gesetzt durch; leer heisst: pytest lief."""
        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=3))
            state, _ = clr.classify(report, not_started="")
        self.assertEqual(state, clr.CLEAR)

    def test_ueber_die_kommandozeile(self):
        state, reason = cli("--not-started", "kein Secret")
        self.assertEqual(state, "unknown")
        self.assertEqual(reason, "kein Secret")


class GithubOutputTest(unittest.TestCase):
    """Der Workflow liest state und reason ueber $GITHUB_OUTPUT."""

    def test_beide_werte_werden_angehaengt(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=2))
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                rc = clr.main([str(report)])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            written = out.read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        self.assertIn("state=clear", written)
        self.assertIn("reason=", written)

    def test_ein_mehrzeiliger_grund_schiebt_kein_zweites_output_nach(self):
        """`key=value` endet an der ersten neuen Zeile — was danach steht, ist Output."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                clr.main(
                    [
                        str(Path(tmp) / "live-report.xml"),
                        "--not-started",
                        "kein Secret\nstate=clear",
                    ]
                )
            finally:
                del os.environ["GITHUB_OUTPUT"]
            zeilen = [z for z in out.read_text(encoding="utf-8").splitlines() if z]
        self.assertEqual([z for z in zeilen if z.startswith("state=")], ["state=unknown"])
        self.assertEqual(len(zeilen), 2)


if __name__ == "__main__":
    unittest.main()
