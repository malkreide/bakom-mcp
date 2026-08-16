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

**ruff: eine Quelle.** Der Pin `0.16.1` steht in `pyproject.toml` und `.pre-
commit-config.yaml` — und **nicht** mehr als eigener Install-Schritt in der
CI.

Im `test`-Job lief der entfernte CI-Schritt nach dem Install der
Abhängigkeiten und überschrieb sie. Eine Abweichung im Pin konnte deshalb in
der CI gar nicht auffallen, sondern nur lokal — wo niemand sie erwartet. Ein
manuelles Nachinstallieren von ruff vor den Gates ist damit nicht mehr nötig
und wäre schädlich: Es würde eine spätere Anhebung hier stillschweigend
überstimmen.

Im `lint`-Job lag der Fall anders: Dort war der ruff-Pin die **einzige**
Installation. An seiner Stelle steht jetzt `pip install -e ".[dev]"`, und
dieser Schritt ist nicht redundant — ohne ihn hat der Job überhaupt kein ruff
(`ruff: command not found`). Er sieht nur so aus wie der Install im `test`-Job.

Lokal einmalig `pre-commit install`, dann läuft das Lint-Gate vor jedem
Commit mit exakt der Gate-Version (Scope `^(src|tests|scripts)/`).

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
Ereignis. Der Publish blieb still aus, ohne dass irgendwo etwas rot war. Ein
grünes «Release on Tag» ist kein Beleg dafür, dass das Paket veröffentlicht
wurde — das steht auf `pypi.org/pypi/bakom-mcp/json`.

**2.0.2 fehlt auf PyPI und bleibt dort fehlen.** Die Reihe ist 1.0.0, 2.0.0,
2.0.3, 2.0.4, 3.0.0. Zwei unabhängige Gründe, und der zweite fiel erst beim
Nachreichversuch am 14.8.2026 auf:

1. Der Workflow lief nie — der Trigger-Defekt oben.
2. Selbst gelaufen wäre er gescheitert. In `v2.0.2` steht
   `"mcp-name" = "io.github.malkreide/bakom-mcp"` unter `[project.urls]`, also
   der Registry-Name in einem Feld, das PyPI als URL validiert. Der Upload
   endet mit `400 … is not a valid url`. In `v2.0.3` ist der Eintrag weg.

Nachträglich hochladen hiesse, den getaggten Stand zu ändern und unter 2.0.2
ein Artefakt abzulegen, das nicht zu `v2.0.2` gehört. Bewusst unterlassen — wer
2.0.2 sucht, nimmt 2.0.3.

Die Lehre für neue Felder unter `[project.urls]`: PyPI validiert dort jeden
Wert als URL, auch selbst erfundene Schlüssel. Was kein URL ist, gehört nicht
dorthin.

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

Laufzeit als Plausibilitätsprüfung, aber **pro Umgebung**. Für dieselben 75
Tests am 14.8.2026 gemessen:

| Umgebung | Laufzeit |
|---|---|
| GitHub-Runner (`live-tests.yml`) | ~30 s |
| Entwicklungs-Sandbox hinter Proxy | ~90–130 s |

Der Faktor drei ist Netzabstand, kein Befund. Wer die Sandbox-Zahl als
Massstab an die CI legt, hält einen gesunden Lauf für verdächtig — der Runner
sitzt näher an `admin.ch`.

Was die Zahl trotzdem taugt: eine Suite, die in **unter 2 s** alles grün
meldet, hat keine Quelle erreicht. Bei Zweifeln nicht die Gesamtzeit lesen,
sondern die Einzelzeiten im Log (`-v`): echte Aufrufe liegen bei 0,3–1,0 s pro
Test, ein übersprungener Aufruf bei ~0.

Der geplante Lauf installiert das **Repo**, nicht das Paket. Ein Wheel, dem
eine Datei fehlt, bleibt für ihn unsichtbar. Nach einem Release einmal
`pip install bakom-mcp==<version>` in ein frisches venv und die Suite dagegen
fahren — vorher prüfen, dass der Import auf `site-packages` zeigt und nicht auf
`src/`, sonst misst man wieder das Repo:

```bash
python -c "from bakom_mcp import server; print(server.__file__)"
```

Gegenprobe bei Änderungen an der Suite — in `server.py` kurz umbiegen:

| Konstante | Erwartung |
|---|---|
| `OPENDATA_SWISS_API` | 28 von 75 fallen |
| `GEO_ADMIN_API` | 10 von 75 fallen |

Vorher prüfen, ob die umgebogene Konstante überhaupt gelesen wird — sonst
beweist die grüne Suite nichts. `GEO_ADMIN_IDENTIFY`, `GEO_ADMIN_FIND` und
`RTV_DB_API` waren solche Fälle und sind alle drei entfernt.

### Fixtures: aufgezeichnet

`tests/fixtures/` hält 17 echte Antworten. Nicht eine je Endpunkt, sondern **eine
je Abfrage**, die ein Werkzeug abschickt: vier Hosts, aber ein Dutzend
Abfrageformen — die Regel «eine Antwort je externem Endpunkt» wäre mit vier
Dateien erfüllt und trüge fast nichts. Herkunft, Datum, Auswahlregel und SHA-256
je Datei stehen in `tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`PYTHONPATH=src python scripts/record_fixtures.py`, geladen wird über
`tests/fixture_data.py`.

Der Recorder greift die Antwort über einen httpx-Response-Hook auf dem echten
Lifespan-Client ab, statt die Anfrage nachzubauen — so tragen Aufzeichnung und
Betrieb dieselben Header, dasselbe Timeout und dieselbe Egress-Allowlist.
Gekürzt wird nur die **Zahl** der Trefferzeilen, nie ein Feld; `count` bleibt
stehen, weil CKAN dort die Gesamtzahl meldet und `bakom_telekomstatistik_uebersicht`
genau die liest. Fehlerpfade bleiben handgeschrieben.

Die erste Aufzeichnung deckte auf, dass opendata.swiss die Beschreibung
`description` nennt und nicht `notes` wie der CKAN-Kern: vier Werkzeuge lieferten
zu jedem Datensatz einen leeren Text, und die Suite blieb grün, weil der
handgeschriebene Stub denselben Feldnamen annahm wie der Code. Erfolgs-Payloads
deshalb nicht mehr von Hand schreiben.

Zwei Aufzeichnungen sind zwischen zwei Läufen nicht bitgleich:
`medien_katalog.json` und `medien_auswertung_1.json` tragen aus `SAMPLE(?cube)`
eine beliebige Cube-Version in `any`. Der Server liest die Variable nicht — das
ist Rauschen, kein Drift.

`UP017` schlägt hier zu, `target-version = "py311"`: ruff **verlangt**
`datetime.UTC` und lehnt `timezone.utc` ab. In `lindas-mcp` (py310) ist es
umgekehrt — dort ist `datetime.UTC` ein Laufzeitfehler auf Python 3.10, und ruff
sagt dazu nichts. Recorder-Code nie zwischen den Repos kopieren, ohne die
`target-version` zu prüfen.

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
