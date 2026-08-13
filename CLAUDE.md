# CLAUDE.md

## Teil 1 — Portfolio-weite Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen: `git fetch origin main && git rev-list --count HEAD..origin/main`
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Teil 2 — Repo-spezifisch (bakom-mcp)

### ruff

Gepinnt in `.github/workflows/ci.yml`: **`ruff==0.16.1`** (beide Jobs, `test` und `lint`).
Dieselbe Version in `.pre-commit-config.yaml` (`rev: v0.16.1`, Scope
`^(src|tests|scripts)/`). Lokal einmalig `pre-commit install`, dann läuft das
Lint-Gate vor jedem Commit mit exakt der CI-Version. Wer die Hooks nicht nutzt:
`pip install ruff==0.16.1`.

Beide Stellen müssen zusammen gebumpt werden — Workflow und `rev`.

Befund:

- `pyproject.toml` `[project.optional-dependencies].dev` deklariert
  `ruff>=0.4.0,<1.0`. Ein `uv pip install -e ".[dev]"` zieht also eine andere
  Version als das Gate; die CI überschreibt sie danach explizit mit `0.16.1`.

### Gate-Befehle (wörtlich aus `ci.yml`)

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/bakom_mcp/server.py
python -c "from bakom_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live"
python scripts/check_version_sync.py
```

Matrix: Python 3.11 / 3.12 / 3.13. Weitere Workflows: `docker.yml`
(Build + Non-root-/Smoke-Test), `secret-scan.yml` (gitleaks), `release.yml`,
`publish.yml`.

### Live-Tests

`.github/workflows/live-tests.yml` fährt `pytest tests/ -m live` täglich
(05:17 UTC) und per `workflow_dispatch`. Ein Fehlschlag wird einmal wiederholt
— bleibt es rot, öffnet der Workflow ein Issue mit Label `live-test-failure`
(oder kommentiert das offene). Die CI selbst schliesst diese Tests weiter per
`-m "not live"` aus; der Marker wird in `tests/conftest.py` automatisch auf
`test_integration.py`, `test_20_szenarien.py`, `test_20_neue_szenarien.py` und
`test_scenarios_20.py` gesetzt.

**Offener Befund: die Live-Suite kann nicht rot werden — bzw. konnte es nicht.**
Die vier Module stammen aus Skripten: jeder Testkörper fängt `Exception` ab und
bucht sie auf ein modulweites `TestResult`, das nur auf stdout landet. `pytest
-m live` meldete 78 passed in 1,4 s — ohne dass ein einziger Aufruf die Quelle
erreichte. 66 der 78 Tests rufen die Tools seit dem Lifespan-Refactor mit
falscher Signatur auf (`missing 1 required positional argument: 'ctx'`).

`pytest_runtest_call` in `tests/conftest.py` vergleicht jetzt `results.errors`
vor und nach jedem Test und lässt den Test fallen, sobald ein Eintrag dazukommt.
Damit ist der Fehler sichtbar — behoben ist er nicht: die 66 Aufrufstellen
brauchen ein echtes `ctx`. Bis dahin ist der Cron-Lauf rot, und zwar zu Recht.
