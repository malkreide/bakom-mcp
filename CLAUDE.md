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

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

### Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Daraus folgt eine Untergrenze von gut **25 Stunden** — so weit liegen erste und
letzte Limit-Meldung auseinander. Die längste mit den Beobachtungen verträgliche
Sperre reicht dagegen vom letzten Erfolg um 08:41 bis zur abweichenden Meldung
um 08:22, also **47 h 41 min**. Wer stattdessen ab der ersten Limit-Meldung
rechnet, unterschlägt die 67 Minuten, in denen das Kontingent schon weg gewesen
sein kann, und nennt die Spanne zwischen zwei Beobachtungen eine Obergrenze.

Und die Untergrenze belegt keine *ununterbrochene* Sperre. Zwischen zwei
Limit-Meldungen kann sich ein Fenster geöffnet und durch neue Auslöser wieder
geschlossen haben. Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor
der abweichenden Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand
gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann reagiert er mit 👍 und schreibt nichts.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

  Von den vieren ist dieser der unzuverlässigste: Die Meldung kann auch
  neben einem gelaufenen Review stehen — siehe unten.

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Nur trägt der vierte Grund nicht so weit, wie die Liste ihn stellt: Die
Environment-Meldung schliesst einen Review nicht aus. In `swiss-culture-mcp`
bekam PR #25 am 16.8. um 11:44:33 ein Review-Objekt **mit** Befund — und um
12:06:59, elf Sekunden nach einem Kommentar, der mit `@codex` begann, zusätzlich
die Environment-Meldung. Beides echt, 22 Minuten auseinander, auf demselben PR.

Der Hinweistext im Review-Objekt nennt selbst zwei Wege. Ein **Review** wird
ausgelöst, wenn ein PR zum Review geöffnet wird, ein Draft auf ready springt
oder jemand «@codex review» schreibt. Daneben kann Codex «answer questions or
update the PR» — und dieser zweite Weg braucht die Environment, der erste
offenbar nicht. Die Zahlen passen dazu: `swiss-culture-mcp` hat drei PRs mit
Review-Objekt (#17, #25, #48), `swiss-public-data-mcp` keinen einzigen — und
beide haben die Environment-Meldung gesehen.

Was damit **nicht** erklärt ist: In `swiss-public-data-mcp` kam die Meldung auf
#56 ohne jede `@codex`-Erwähnung, zwölf Sekunden nach dem Anlegen, und der PR
war zu dem Zeitpunkt ein Draft. Sie trifft dort also weder den Mention-Weg noch
die Draft-Regel. Der Auslöser ist offen und wird hier nicht geraten.

Für die Praxis bleibt: «Environment fehlt» belegt nicht, dass in diesem Repo
keine Reviews laufen. Ob geprüft wurde, sagt weiterhin nur die Form der
Antwort.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** die 👍-Reaktion. Wer nur das Objekt gelten lässt, zählt
jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm ein,
den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe), ein Review **ohne** Befund eine
👍-Reaktion, und die beiden Ausfallmeldungen — Kontingent wie Environment —
sind gewöhnliche Issue-Kommentare. Beim Draft gibt es überhaupt nichts, weil
Codex nicht anläuft; ein kommentarloser Draft ist deshalb kein Beleg, sondern
ein nicht durchgeführter Test.

Das sind verschiedene Abfragen — `get_reviews` gegen `get_comments`, und für
die Reaktion keine von beiden; wer nur eine nimmt, übersieht den Rest. Genau so
ist die Limit-Meldung zuerst durchgerutscht.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Kontingent- **oder** die Environment-Meldung sein. Den Text lesen, nicht die
Zahl. Und einen unbekannten dritten Text wörtlich zitieren, statt ihn in eine
der bekannten Schubladen zu zwingen — dieser Abschnitt musste schon einmal von
drei auf vier Gründe wachsen.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Die Gegenprobe fragt nach Review-Objekten statt nach Kommentaren:

```
search_pull_requests: user:malkreide type:pr reviewed-by:chatgpt-codex-connector[bot]
```

Am 23.8.2026 über die 41 Server-Repos: **25** mit mindestens einem
Review-Objekt, 16 ohne eines. Belastbar ist davon nur die 25 — die 16 nicht.
Ein befundloser Review hinterlässt bloss die 👍-Reaktion, und die findet diese
Abfrage nicht. «Kein Review-Objekt» heisst also «kein Befund gemeldet», nicht
«nicht geprüft»; die Zahl ist eine Untergrenze für Geprüftes, keine Aufteilung
in geprüft und ungeprüft. Und sie gilt für den Abfragetag: Ein Review vom 16.8.
sagt über den heutigen Stand nichts.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die 25 Stunden
oben schliessen das Fünf-Stunden-Fenster nicht aus: Es kann sich
zwischendurch geöffnet und durch neue Auslöser wieder erschöpft haben. Das
auszuschliessen bräuchte den Nachweis, dass in der ganzen Spanne kein einziger
Review durchlief — den gibt es nicht, weil nur Fehlschläge beobachtet wurden.
Eine lange Sperre belegt eine lange Sperre, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

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

**ruff: eine Quelle.** Der Pin `0.16.3` steht in `pyproject.toml` und `.pre-
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
`ruff-Pin einig auf 0.16.3 (2 Stellen)`. Wer die zwei Pins von Hand
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
