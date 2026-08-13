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

### Live-Tests — Befund DRIFT-005

Es gibt **keinen** geplanten Live-Test-Workflow: kein `schedule:`/cron-Trigger
in `.github/workflows/`. Live-Tests werden ausschliesslich per `-m "not live"`
ausgeschlossen (Marker wird in `tests/conftest.py` automatisch auf
`test_integration.py`, `test_20_szenarien.py`, `test_20_neue_szenarien.py` und
`test_scenarios_20.py` gesetzt). Damit verletzt dieses
Repo **DRIFT-005** des Audit-Katalogs — Drift der externen Quelle bleibt
unbemerkt, bis er produktiv auffällt. Bis zur Behebung: vor jedem Release
manuell `PYTHONPATH=src pytest tests/ -m live` fahren.
