#!/usr/bin/env bash
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# origin/<Standard-Branch> liegt.  Ausführliche Begründung: siehe README.md
# im selben Verzeichnis.
#
# OBERSTE REGEL: Dieser Hook blockiert die Session nie.  Kein `set -e`, jeder
# Pfad endet mit `exit 0`, alles was das Netz berührt hat ein Timeout.  Ein
# Hook, der bei Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal
# abgeschaltet und schützt danach gar nichts.
#
# Er schweigt in jedem dieser Fälle: kein Repo, kein Remote, kein Netz,
# hängendes DNS, Auth-Prompt, unbekannter Standard-Branch, leerer HEAD —
# und, der Normalfall, wenn nichts fehlt.

set -u

# Zeitbudget fürs Netz in Sekunden.  Überschreibbar, falls jemand hinter
# einem sehr langsamen Proxy sitzt.
FETCH_TIMEOUT="${CLAUDE_STALENESS_TIMEOUT:-5}"

# Git darf hier unter keinen Umständen interaktiv nachfragen: ein
# Credential- oder Host-Key-Prompt ohne Terminal wartet sonst endlos, und
# genau das wäre das Blockieren, das dieser Hook ausschliessen soll.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=true
export SSH_ASKPASS=true
export SSH_ASKPASS_REQUIRE=never
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes -o ConnectTimeout=$FETCH_TIMEOUT -o StrictHostKeyChecking=accept-new}"

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

git rev-parse --git-dir      >/dev/null 2>&1 || exit 0  # kein Git-Repo
git remote get-url origin    >/dev/null 2>&1 || exit 0  # kein Remote «origin»
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0  # HEAD ohne Commit

# `timeout` fehlt auf manchen Systemen (macOS ohne coreutils).  Fehlt es, wird
# gar nicht erst ins Netz gegangen: lieber keine Pruefung als eine haengende
# Session.  Die http.lowSpeed*-Optionen weiter unten reichen dafuer NICHT --
# sie greifen nur bei einer tröpfelnden Uebertragung, nicht wenn die Gegenstelle
# die Verbindung annimmt und dann schweigt.  Gemessen lief der Hook in genau
# diesem Fall unbegrenzt weiter (>25s, extern gekappt), und damit war die
# oberste Regel dieses Skripts verletzt.
if command -v timeout >/dev/null 2>&1; then
  run_limited() { timeout "$FETCH_TIMEOUT" "$@"; }
elif command -v gtimeout >/dev/null 2>&1; then
  run_limited() { gtimeout "$FETCH_TIMEOUT" "$@"; }
else
  run_limited() { return 1; }
fi

# Standard-Branch ERMITTELN, nicht «main» annehmen: drei Server im Portfolio
# heissen ihn `master`.  Wer das fest verdrahtet, prüft dort nie etwas und
# hält den stillen Fehlschlag für ein Netzproblem.
#
# Erst die lokale Notiz `origin/HEAD` — die kostet kein Netz.
default_branch=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
default_branch="${default_branch#origin/}"

# Fehlt sie (frischer Klon mit `--single-branch`, `--depth`, oder manuell
# gesetztes Remote), den Remote fragen — mit Timeout.
if [ -z "$default_branch" ]; then
  default_branch=$(run_limited git ls-remote --symref origin HEAD 2>/dev/null |
    sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' | head -n 1)
fi

# Nicht ermittelbar heisst schweigen, nicht raten.
[ -n "$default_branch" ] || exit 0

# Der einzige Netzzugriff, der wirklich Daten holt.  `--no-tags` hält ihn
# klein, die lowSpeed-Optionen brechen eine tröpfelnde Verbindung ab, auch
# wenn `timeout` fehlt.
run_limited git \
  -c "http.lowSpeedLimit=1000" \
  -c "http.lowSpeedTime=$FETCH_TIMEOUT" \
  fetch --quiet --no-tags origin "$default_branch" >/dev/null 2>&1 || exit 0

# Funktioniert auch bei detached HEAD — dort ist der Vergleich sogar
# besonders nützlich.
behind=$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)

# Alles, was keine reine Zahl ist, ist ein Fehlschlag: schweigen.
case "$behind" in
  '' | *[!0-9]*) exit 0 ;;
esac

# Bei 0 schweigt er.  Nur ein echter Rückstand ist eine Meldung wert.
[ "$behind" -gt 0 ] || exit 0

commit_wort="Commits"
[ "$behind" -eq 1 ] && commit_wort="Commit"

printf '⚠️  Veralteter Klon: HEAD liegt %s %s hinter origin/%s.\n' \
  "$behind" "$commit_wort" "$default_branch"
printf '    Vor der Arbeit aktualisieren, sonst entsteht eine rote CI, deren\n'
printf '    Ursache nicht im Diff steht:\n'
printf '        git merge origin/%s     # oder: git rebase origin/%s\n' \
  "$default_branch" "$default_branch"

exit 0
