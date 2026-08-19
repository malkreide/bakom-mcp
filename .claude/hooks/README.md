# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<Standard-Branch>` liegt. Liegt er nicht
zurück, sagt er nichts.

## Warum

Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Wer die Ursache im
eigenen Diff sucht, sucht in den falschen Dateien; im Diff steht sie nicht,
weil sie nicht dort liegt. Die Prüfung kostet eine Sekunde und ersetzt diese
Fehlersuche.

`CLAUDE.md` schreibt dieselbe Prüfung unter «Vor der Arbeit» vor. Dieser Hook
führt sie aus, statt sich darauf zu verlassen, dass jemand daran denkt.

## Verhalten

Ausgabe nur bei echtem Rückstand:

```
⚠️  Veralteter Klon: HEAD liegt 15 Commits hinter origin/main.
```

Bei 0 fehlenden Commits: keine Ausgabe.

## Die drei Regeln, nach denen er gebaut ist

**1. Er blockiert die Session nie.** Kein `set -e`, jeder Pfad endet mit
`exit 0`. Still durch gehen: kein Git-Repo, kein Remote `origin`, kein Netz,
flatterndes DNS, ein Auth- oder Host-Key-Prompt, detached HEAD, HEAD ohne
Commit, ein nicht ermittelbarer Standard-Branch. Ein Hook, der bei
Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal abgeschaltet und
schützt danach gar nichts — deshalb ist «nie blockieren» wichtiger als
«immer melden».

Die Prompts sind der unterschätzte Fall: `GIT_TERMINAL_PROMPT=0`,
`GIT_ASKPASS`, `SSH_ASKPASS_REQUIRE=never` und `BatchMode=yes` stehen im
Skript, weil ein Credential-Prompt ohne Terminal nicht scheitert, sondern
wartet — und ein Timeout auf dem Fetch hilft nicht gegen etwas, das vor dem
Fetch fragt.

**2. Kurzes Netz-Budget.** 5 Sekunden (`CLAUDE_STALENESS_TIMEOUT`
überschreibt), durchgesetzt über `timeout(1)`. Fehlt `timeout` — macOS ohne
coreutils —, greifen zusätzlich `http.lowSpeedLimit`/`http.lowSpeedTime` und
`ConnectTimeout` für SSH. Darüber liegt als letzte Sicherung `"timeout": 15`
in `settings.json`: was der Harness nach 15 s noch laufen sieht, killt er.

**3. Der Standard-Branch wird ermittelt, nicht angenommen.** Drei Server im
Portfolio (`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`) heissen ihren
Standard-Branch `master`. Ein fest verdrahtetes `origin/main` scheitert dort
mit «couldn't find remote ref main» — und weil dieser Hook still scheitert,
prüfte er dann nie etwas, ohne dass es auffiele. Genau diese Annahme hat
schon einmal einen Branch 15 Commits alt werden lassen.

Ermittelt wird zuerst lokal über `refs/remotes/origin/HEAD` (kostet kein
Netz), und nur wenn die Referenz fehlt, über
`git ls-remote --symref origin HEAD`.

## Gegenprobe

Der Hook lässt sich direkt aufrufen; das Verhalten ist dasselbe wie beim
Sessionstart:

```bash
.claude/hooks/session-start.sh                  # aktuell → keine Ausgabe
git checkout HEAD~3 && .claude/hooks/session-start.sh   # → meldet 3 Commits
CLAUDE_STALENESS_TIMEOUT=0 .claude/hooks/session-start.sh  # Netz tot → still, rc 0
```

Nach jedem Lauf `echo $?` mitlesen: alles ausser `0` wäre ein Fehler im Hook
selbst.
