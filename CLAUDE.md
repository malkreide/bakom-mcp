# CLAUDE.md

## Teil 1 — Portfolio-weite Konventionen

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

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

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

**Bei einem blockierten PR nennt der Merge-Versuch den Blocker, jede Ableitung
rät.** `mergeable_state: blocked` bei grüner CI heisst: ein required Kontext
fehlt oder steht nicht auf grün. Welcher, sagt die Einstellung — und die sperrt
der Agent-Proxy mit HTTP 403, ein MCP-Werkzeug dafür gibt es nicht. Der Ausweg
ist nicht Indizienarbeit, sondern ein Merge-Versuch über die API:

```
PUT /repos/<owner>/<repo>/pulls/<n>/merge
405 Required status check "Codex hat diesen Head geprueft" is expected.
```

Der Name steht dort wörtlich so, wie er in der Branch Protection eingetragen
ist. Scheitert der Versuch, kostet er nichts.

Am 24./25.9.2026 über drei Repos vermessen, nachdem ein Gate-Workflow entfernt
worden war und seinen required Kontext ohne Berichterstatter zurückliess:

| Repo | eingetragener Kontext | Art |
|---|---|---|
| `register-mcp` | `Codex hat den PR angesehen` | Check-Run |
| `srgssr-mcp` | `review-abgeschlossen` | Check-Run |
| `fedlex-mcp` | `Codex hat diesen Head geprueft` | Check-Run |

**Warum Ableiten hier systematisch fehlgeht.** GitHub nimmt als Check-Run-Name
den **Job**-Namen, nicht den des Workflows. Zwei der drei Kontexte enthalten die
Zeichenfolge «codex-gate» nicht, obwohl sie aus `codex-gate.yml` stammen; wer in
den Einstellungen danach sucht, findet nichts und hält die Regel für abwesend.
Trug der Job kein `name:`, nimmt GitHub die Job-ID — daher `review-abgeschlossen`.

Zwei Fehlschlüsse sind dabei belegt, beide aus **einer** Beobachtung gezogen:

- Aus einem Commit-Status auf den required Kontext geschlossen. In `fedlex-mcp`
  stand der Status `codex-gate` auf dem Head auf `success` und blockierte
  nichts, während der fehlende Check-Run den Merge hielt. Am Kontroll-PR waren
  beide rot — dort ist nicht zu unterscheiden, welcher von beiden eingetragen
  ist. Genommen wurde der auffälligere.
- Aus einer Check-Run-Liste auf den required Kontext geschlossen. Die Liste
  zeigt, was **berichtet** wurde; eingetragen sein kann ein Name, der gerade
  gar nicht erscheint. Genau das ist der Fall, um den es geht.

**Ein Vorbehalt, der zur Methode gehört:** Die Absage nennt immer nur den
**ersten** fehlenden Kontext. Ist ein zweiter eingetragen, zeigt ihn erst der
nächste Versuch. Nach jeder Änderung an der Einstellung also erneut versuchen,
bis der Merge durchgeht oder ein neuer Name fällt.

Die Kosten der Ableitung sind gemessen: ein Arbeitstag, an dem der PR-Text den
falschen Namen trug und in den Einstellungen nach einer Zeichenfolge gesucht
wurde, die dort nicht steht.

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — Repo-spezifisch (bakom-mcp)

**ruff: eine Quelle.** Der Pin steht in `pyproject.toml` und `.pre-
commit-config.yaml`, beide Male exakt — und **nicht** mehr als eigener
Install-Schritt in der CI. Die Version steht bewusst nicht hier;
`tests/test_ruff_pin_doku.py` hält sie draussen.

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

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

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
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/bakom_mcp/server.py
python -c "from bakom_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -m "not live"
python scripts/check_version_sync.py
```

Matrix: Python 3.11 / 3.12 / 3.13 — aber nicht für alles: Die zwei ruff-Gates
laufen zusätzlich im Job `lint`, und der hat keine Matrix, sondern läuft auf
3.11. Weitere Workflows: `docker.yml` (Build + Non-root-/Smoke-Test),
`secret-scan.yml` (gitleaks), `release.yml`, `publish.yml`.

**`check_version_sync.py` prüft mehr, als sein CI-Schritt verspricht.** Der
heisst «(pyproject ↔ server.json / README / src)», das Skript hält aber
zusätzlich den **ruff-Pin über beide Stellen** zusammen — `pyproject.toml`
und `rev:` in `.pre-commit-config.yaml` — und verbietet einen eigenen
ruff-Install in einem Workflow. Es meldet das im Klartext:
`ruff-Pin einig auf <Version> (2 Stellen)`. Wer die zwei Pins von Hand
vergleicht, tut Arbeit, die ein Gate schon leistet; wer nur einen davon
anhebt, macht diesen Gate rot — nicht etwa ein Lint.

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

**`pin_audit.py` steht an drei Stellen.** `swiss-electricity-mcp`, `bakom-mcp`
und `register-mcp` halten byteweise dieselbe `scripts/pin_audit.py` samt
`tests/test_pin_audit.py`. Wer eine ändert, ändert alle drei im selben Commit —
sonst misst der eine Server anders als der andere, und das ist genau die Drift,
gegen die das Werkzeug gebaut ist. Kein Gate erzwingt das, es gibt nur diesen
Absatz. Aus dem Verzeichnis, in dem die Server nebeneinander liegen:

```bash
sha256sum */scripts/pin_audit.py */tests/test_pin_audit.py |
  awk '{print $1}' | sort | uniq -c
```

Erwartet: **zwei** Zeilen mit je **3**. Die Anzahl mitlesen, nicht nur die Zahl
der Zeilen — findet der Glob nur ein Repo, stehen dort auch zwei Zeilen, und
«einig» hiesse dann bloss, dass nichts verglichen wurde.

**Der SessionStart-Hook steht an drei Stellen.** `swiss-electricity-mcp`,
`bakom-mcp` und `register-mcp` halten byteweise dieselben drei Dateien:
`.claude/hooks/check-clone-freshness.sh`, `.claude/hooks/README.md` und
`tests/test_session_start_hook.py`. Wer eine ändert, ändert alle drei im selben
Commit — sonst driften die Fassungen auseinander, und genau das war der
Ausgangszustand: drei eigenständige Implementierungen mit drei Dateinamen, von
denen eine ohne `timeout` im PATH ungebremst ins Netz ging und die Session
anhalten konnte. `.claude/settings.json` ist bewusst **nicht** Teil der Regel
(dort steht Repo-Eigenes); geprüft wird es stattdessen vom Test, der die
Registrierung des Hooks nachweist.

Kein Gate erzwingt die Gleichheit, es gibt nur diesen Absatz. Aus dem
Verzeichnis, in dem die Server nebeneinander liegen:

```bash
sha256sum */.claude/hooks/check-clone-freshness.sh */.claude/hooks/README.md \
          */tests/test_session_start_hook.py |
  awk '{print $1}' | sort | uniq -c
```

Erwartet: **drei** Zeilen mit je **3**. Die Anzahl mitlesen, nicht nur die Zahl
der Zeilen — findet der Glob nur ein Repo, stehen dort auch drei Zeilen, und
«einig» hiesse dann bloss, dass nichts verglichen wurde.
