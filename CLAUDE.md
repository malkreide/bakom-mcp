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

Dieselbe Version ein drittes Mal in `pyproject.toml`
(`[project.optional-dependencies].dev`, `ruff==0.16.1`), damit
`uv pip install -e ".[dev]"` nicht eine andere Version zieht als das Gate.

**Alle Stellen zusammen bumpen** — beide Workflow-Jobs, `rev` und dev-Extra.
`scripts/check_version_sync.py` erzwingt das: der Check vergleicht alle vier
und fällt mit Datei und Zeilennummer, sobald eine abweicht oder das dev-Extra
wieder einen Bereich statt eines Pins deklariert.

### Release

Ein Release entsteht aus dem Tag-Push, in dieser Reihenfolge: Version an allen
vier Stellen bumpen und CHANGELOG-Abschnitt `## [X.Y.Z] - JJJJ-MM-TT` schreiben,
das über einen PR nach `main` bringen, **danach** taggen. Ein Tag auf einem
Commit, der die alte Version trägt, lässt sich nicht mehr geradeziehen: PyPI
gibt eine Versionsnummer nicht wieder her.

Vor dem Push prüfen, worauf der Tag zeigt — `git tag -a vX.Y.Z origin/main`
nach einem frischen `git fetch origin main` nimmt den Server-Stand und ist
gegen einen veralteten lokalen Klon immun.

`release.yml` schneidet den Release-Text mit `awk` aus dem CHANGELOG. Findet es
den Abschnitt nicht, schreibt es kommentarlos «No CHANGELOG entry found» ins
Release. Vorher lokal gegenprüfen:

```bash
awk "/^## \[3.0.0\] -/{flag=1; next} /^## \[/{flag=0} flag" CHANGELOG.md | wc -l
```

**`publish.yml` hängt am Tag-Push, nicht am Release.** Bis August 2026 lief es
auf `release: published`. Beim Anlegen im Browser entsteht der Tag mit, beide
Ereignisse feuern, alles lief — bei einem per `git push` gesetzten Tag erzeugt
`release.yml` das Release aber mit `GITHUB_TOKEN`, und daraus entsteht kein
Ereignis. Der Publish blieb still aus: **2.0.2 fehlt deshalb bis heute auf
PyPI**, ohne dass irgendwo etwas rot war. Ein grünes «Release on Tag» ist kein
Beleg dafür, dass das Paket veröffentlicht wurde — das steht auf
`pypi.org/pypi/bakom-mcp/json`.

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
`-m "not live"` aus; alle Live-Tests stehen in `tests/test_live.py` und tragen
dort `pytestmark = pytest.mark.live`.

Zwei Regeln für diese Datei:

- Antworten über die Helfer `text()` / `daten()` prüfen. Die Tools geben Fehler
  als Text zurück (`"Fehler: …"`), statt zu werfen. Ein `len(output) > 30` — so
  stand es in den Vorgängermodulen — ist auf jeder Fehlermeldung erfüllt.
- Den `ctx` als Fixture `live_ctx` nehmen. Sie kommt aus dem echten
  `lifespan(mcp)`, damit Timeout, User-Agent und Egress-Allowlist aus derselben
  Quelle stammen wie im Betrieb.

Was nie ein Netz berührt, gehört nicht hierher, sondern in `test_unit.py` — nur
dort prüft es die CI. `bakom_breitbandatlas_datensaetze` etwa ist ein statischer
Katalog ohne API-Aufruf.

Laufzeit als Plausibilitätsprüfung: `pytest -m live` braucht ~90–130 s für 75
Tests. Meldet die Suite alles grün in unter 2 s, hat kein Aufruf die Quelle
erreicht.

Gegenprobe bei Änderungen an der Suite — in `server.py` kurz umbiegen:

| Konstante | Erwartung |
|---|---|
| `OPENDATA_SWISS_API` | 28 von 75 fallen |
| `GEO_ADMIN_API` | 10 von 75 fallen |

Vorher prüfen, ob die umgebogene Konstante überhaupt gelesen wird — sonst
beweist die grüne Suite nichts. `GEO_ADMIN_IDENTIFY`, `GEO_ADMIN_FIND` und
`RTV_DB_API` waren solche Fälle und sind alle drei entfernt.

### Was `bakom_rtv_suche` liefert

Datensätze aus dem BAKOM-Katalog auf opendata.swiss, **keine einzelnen Sender**.
`rtvdb.ofcomnet.ch` ist eine Meteor-SPA: jeder Pfad antwortet mit HTTP 200 und
derselben HTML-Hülle, der einzige JSON-Endpunkt ist der DDP-Handshake
`/sockjs/info`. Der frühere Erstaufruf gegen `/api/broadcasters` konnte deshalb
nie Daten liefern — er scheiterte an `r.json()` und fiel still auf CKAN zurück,
während die Antwort weiter «BAKOM RTV-Datenbank» als Quelle nannte.

`kanton` und `media_type` gehen als Suchwort in die Volltextsuche; der Katalog
hat für beides keine Facette. Ein Test darf hier keine exakte Filterung
behaupten — er würde grün bleiben, egal was die Parameter tun.

### Was `bakom_aktuell` liefert

Zuletzt geänderte BAKOM-Datensätze aus dem Katalog, **keine Medienmitteilungen**.
Bis August 2026 lieferte das Tool einen im Quellcode gepflegten Highlights-Block
als «aktuell», fiel bei unbekanntem Thema still auf die Medien-Einträge zurück
und verschluckte CKAN-Fehler per `except Exception: pass` — deshalb überlebte es
die Drift-Probe. Alles drei ist entfernt.

Für die Nachrichtenlage gibt es keine bekannte maschinenlesbare Quelle:
`news.admin.ch` und `admin.ch` antworten aus der CI mit 403, was kein Beleg für
Abwesenheit ist. Ohne Verifikation von einem normalen Anschluss aus wird darauf
nichts gebaut.

### LINDAS (`bakom_medien_statistik`)

Endpunkt `https://lindas.admin.ch/query` — **nicht** `/sparql`, das gibt 404.
OFCOM-Cubes liegen im Named Graph `https://lindas.admin.ch/ofcom/cube`; ohne
`FROM` trifft die Query den Default-Graph mit 2010 Cubes aller Ämter statt 540.

Ein **unbekannter Graph antwortet mit HTTP 200 und null Zeilen**. Eine
Leermenge ist hier also kein Beleg für Abwesenheit — deshalb trägt jedes leere
Resultat ein `hinweis`-Feld mit dem nächsten Versuch.

Je Titel gibt es mehrere `schema:version`; ohne Filter auf die höchste
veröffentlichte Version erscheint jede Beobachtung so oft, wie es Versionen
gibt.

Gegenprobe: `LINDAS_OFCOM_GRAPH` umbiegen → 4 der 5 Statistik-Tests fallen. Der
fünfte prüft die Leermenge und kann Graph-Drift nicht sehen.

Fundstücke der Live-Probe (13.08.2026):

- Die `Programm`-Dimension führt 128 Labels, LINDAS' eigener Zähl-Cube nennt für
  2020 aber 199+39+17 Radioprogramme. Die Statistik deckt die untersuchten
  Programme ab, nicht den Bestand.
- Derselbe Sender erscheint mehrfach (`Energy BE` / `Energy Bern`), `Durchschnitt`
  ist ein Aggregat in der Senderdimension, ein Label beginnt mit Leerzeichen.
- Die Dimension heisst in 18 Cubes `Konzessionierungsart` und in 13 weiteren
  `Konzessonierungsart` — Tippfehler in der Quelle.
