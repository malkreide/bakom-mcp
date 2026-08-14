"""
Versions-Synchronität prüfen — und sicherstellen, dass in `src/` keine Version
von Hand gepflegt wird.

`pyproject.toml` ist die einzige Quelle der Wahrheit. Verglichen werden alle
Stellen, die dieselbe Nummer wiederholen:

  - `server.json` (MCP-Registry-Manifest): `version` und jedes
    `packages[*].version`
  - die Versions-Badges der READMEs

Hintergrund: `publish.yml` synchronisiert `server.json` beim Veröffentlichen
aus dem Tag-Namen — die *committete* Version wirkt also nie auf das
publizierte Artefakt und fällt deshalb nicht auf, wenn sie veraltet. Die
README-Badges erzwingt überhaupt nichts.

Zweiter Teil: die ruff-Version. Sie steht in beiden CI-Jobs, im
pre-commit-Hook und im dev-Extra — vier Stellen, die dieselbe Nummer
wiederholen und zwischen denen nichts vermittelt.

Dritter Teil: in `src/` darf keine Versionsnummer stehen. Der Laufzeit-Wert
kommt aus den Paket-Metadaten (`importlib.metadata.version()`); ein wieder
eingefügtes Literal wäre der Beginn derselben Drift, die im ganzen Portfolio
falsche User-Agents erzeugt hat.

Verwendung:
    python scripts/check_version_sync.py     # exit 1 bei Abweichung

Bewusst nur Standardbibliothek — der Check braucht keine Projekt-Installation
und läuft damit auch in schlanken CI-Jobs. Auf Python 3.10 (noch keine
`tomllib`) greift ein Minimal-Parser für die zwei benötigten Felder.
"""

import io
import json
import re
import sys
import tokenize
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 — tomllib kam erst mit 3.11
    tomllib = None

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
SERVER_JSON = ROOT / "server.json"
SRC = ROOT / "src"
WORKFLOWS = ROOT / ".github" / "workflows"
PRECOMMIT = ROOT / ".pre-commit-config.yaml"

# Shields.io-Badge: ![Version](https://img.shields.io/badge/version-X.Y.Z-blue)
_BADGE = re.compile(r"img\.shields\.io/badge/[Vv]ersion-([^-\s)]+)-")


def code_lines(text: str) -> list[str]:
    """Zeilen ohne Kommentare.

    Kommentare dokumentieren im Portfolio genau die Drift, die dieser Check
    verhindern soll — etwa «the User-Agent in server.py carried
    "bakom-mcp/1.0"». Sie zu melden wäre ein Fehlalarm, der die CI grundlos
    rot färbt. Ausgeschnitten wird per `tokenize`, nicht per `split("#")`:
    ein `#` in einem String-Literal darf die Zeile nicht abschneiden.
    """
    lines = text.splitlines()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                row, col = tok.start
                lines[row - 1] = lines[row - 1][:col]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Nicht parsebare Datei: lieber vollständig prüfen als still übergehen.
        return text.splitlines()
    return lines


def norm(token: str) -> str:
    """Kleingeschrieben und ohne Trennzeichen — zum Vergleich von Produkt-Token
    und Dist-Namen.

    Das Produkt-Token im User-Agent ist nicht immer der Dist-Name:
    `swisstopo-mcp` sendet `SwisstopoMCP/0.1`. Ein wörtlicher Vergleich liess
    dort ein hartkodiertes Literal als sauber durchgehen — genau das Versagen,
    gegen das dieser Check existiert.
    """
    return re.sub(r"[^a-z0-9]", "", token.lower())


# Irgendein Produkt-Token, gefolgt von einer gepunkteten Zahl. Welches davon
# uns gehört, entscheidet der normalisierte Vergleich mit dem Dist-Namen —
# fremde Token (`Mozilla/5.0`, `httpx/0.27`) fallen so heraus.
_UA = re.compile(r"""([A-Za-z][A-Za-z0-9_.+-]*)/(\d+\.\d[^\s"']*)""")


def own_ua_versions(line: str, dist: str) -> list[str]:
    """Versionen aus den User-Agents, deren Produkt-Token uns gehört.

    Eigene Funktion, damit die Zeile auch bei `line-length = 88` passt: im
    Portfolio stehen 88, 100 und 120 nebeneinander, und `ruff format` zieht
    einen Ausdruck zusammen, sobald er in die jeweilige Breite passt. Eine
    mehrzeilige Comprehension waere damit in der einen Haelfte der Repos
    formatgerecht und in der anderen nicht.
    """
    return [m.group(2) for m in _UA.finditer(line) if norm(m.group(1)) == norm(dist)]


def find_hardcoded(dist: str) -> list[tuple[str, int, str]]:
    """Manuell gepflegte Versionen in `src/`.

    Zwei Formen kommen im Portfolio vor: der User-Agent (`<token>/1.2.3`) und
    die `__version__`-Zuweisung. Die Projekt-URL trägt denselben Namen, aber
    keine Ziffer danach — deshalb verlangt das Muster eine gepunktete Zahl.

    Der Fallback im `except PackageNotFoundError`-Zweig (`0.0.0+source`) ist
    ausdrücklich **kein** Treffer: er behauptet gerade keine Version. Erkannt
    wird er am lokalen Segment nach `+`, nicht an der Zahl davor — `0.0.0`
    allein sieht wie eine echte Version aus.
    """
    hits: list[tuple[str, int, str]] = []
    if not SRC.is_dir():
        return hits

    dunder = re.compile(r"""__version__\s*=\s*["']([^"']+)["']""")

    for path in sorted(SRC.rglob("*.py")):
        for lineno, line in enumerate(code_lines(path.read_text(encoding="utf-8")), start=1):
            values = own_ua_versions(line, dist)
            for m in dunder.finditer(line):
                if re.match(r"\d+\.\d", m.group(1)):
                    values.append(m.group(1))
            if any("+" not in v for v in values):
                hits.append((str(path.relative_to(ROOT)), lineno, line.strip()))
    return hits


# `pip install ruff==0.16.1` in einem Workflow-Schritt.
_RUFF_PIN = re.compile(r"ruff==([0-9][0-9A-Za-z.+-]*)")
# Der Hook-Block: rev gehoert zum Repo darueber, deshalb beide zusammen matchen.
_RUFF_HOOK = re.compile(
    r"repo:\s*\S*ruff-pre-commit\s*\n\s*rev:\s*v?([0-9][0-9A-Za-z.+-]*)", re.MULTILINE
)
# Ein ruff-Requirement im dev-Extra, gepinnt oder nicht.
_RUFF_REQ = re.compile(r'"ruff(?P<spec>[^"]*)"')


def collect_ruff_pins() -> list[tuple[str, str]]:
    """Alle Stellen, die die ruff-Version festlegen — je (Bezeichnung, Wert).

    Die Version steht dreifach im Repo: in beiden CI-Jobs, im pre-commit-Hook
    und im dev-Extra. Laufen sie auseinander, meldet der lokale Lauf
    Abweichungen, die niemand verursacht hat — der teuerste Zeitfresser, weil
    der Diff nichts davon zeigt.

    Ein nicht gepinntes ruff im dev-Extra wird als eigener Wert gemeldet,
    nicht uebergangen: ein Bereich ist hier dieselbe Drift, nur langsamer.
    """
    found: list[tuple[str, str]] = []

    if WORKFLOWS.is_dir():
        for wf in sorted(WORKFLOWS.glob("*.yml")):
            for lineno, line in enumerate(wf.read_text(encoding="utf-8").splitlines(), start=1):
                for m in _RUFF_PIN.finditer(line):
                    found.append((f".github/workflows/{wf.name}:{lineno}", m.group(1)))

    if PRECOMMIT.exists():
        for m in _RUFF_HOOK.finditer(PRECOMMIT.read_text(encoding="utf-8")):
            found.append((f"{PRECOMMIT.name} → rev", m.group(1)))

    text = PYPROJECT.read_text(encoding="utf-8")
    section = re.search(r"^dev\s*=\s*\[(.*?)\]", text, re.MULTILINE | re.DOTALL)
    if section:
        for m in _RUFF_REQ.finditer(section.group(1)):
            spec = m.group("spec").strip()
            wert = spec[2:].strip() if spec.startswith("==") else f"nicht gepinnt ({spec})"
            found.append(("pyproject.toml → dev-Extra", wert))

    return found


def check_ruff_pins() -> str:
    """Prueft, dass alle ruff-Pins uebereinstimmen. Bei Abweichung: exit 1."""
    pins = collect_ruff_pins()
    if len(pins) < 2:
        return "ruff-Pin: zu wenige Stellen zum Vergleichen"

    werte = {wert for _, wert in pins}
    if len(werte) > 1:
        print("DRIFT: die ruff-Version weicht zwischen den Stellen ab:", file=sys.stderr)
        for where, wert in pins:
            print(f"  {where} = {wert!r}", file=sys.stderr)
        print(
            "\nAlle Stellen im selben Commit bumpen. Eine andere Version als das "
            "Gate meldet lokal Abweichungen, die niemand verursacht hat.",
            file=sys.stderr,
        )
        sys.exit(1)

    return f"ruff-Pin einheitlich ({pins[0][1]}, {len(pins)} Stellen)"


def collect_declared(expected: str) -> list[tuple[str, str]]:
    """Alle Stellen, die die Version wiederholen — je (Bezeichnung, Wert)."""
    found: list[tuple[str, str]] = []

    if SERVER_JSON.exists():
        server = json.loads(SERVER_JSON.read_text(encoding="utf-8"))
        found.append(("server.json → version", server.get("version", "")))
        for i, pkg in enumerate(server.get("packages", [])):
            found.append((f"server.json → packages[{i}].version", pkg.get("version", "")))

    for readme in sorted(ROOT.glob("README*.md")):
        for match in _BADGE.finditer(readme.read_text(encoding="utf-8")):
            found.append((f"{readme.name} → Versions-Badge", match.group(1)))

    return found


def read_project() -> dict:
    """`[project]`-Tabelle aus pyproject.toml.

    Ohne `tomllib` (Python 3.10) genügt hier ein Minimal-Parser: gebraucht
    werden nur `name` und `version`, beides einfache Strings direkt unter
    `[project]`. Eine Abhängigkeit auf `tomli` einzuführen, nur damit ein
    Check laufen kann, wäre unverhältnismässig.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(text)["project"]

    section = re.search(r"^\[project\]\s*$(.*?)(?=^\[)", text, re.MULTILINE | re.DOTALL)
    body = section.group(1) if section else text
    out = {}
    for key in ("name", "version"):
        m = re.search(rf'^{key}\s*=\s*"([^"]+)"', body, re.MULTILINE)
        if m:
            out[key] = m.group(1)
    return out


def main() -> None:
    project = read_project()
    dist = project["name"]
    version = project.get("version")

    if version is None:
        # `dynamic = ["version"]`: die Version entsteht beim Bauen, ein
        # Literal in src/ ist dort die Quelle und kein Fehler.
        print("Versions-Sync übersprungen: pyproject.toml nutzt eine dynamische Version.")
        return

    found = collect_declared(version)
    mismatches = [(where, value) for where, value in found if value != version]
    if mismatches:
        print(
            f"DRIFT: pyproject.toml steht auf {version!r}, folgende Stellen weichen ab:",
            file=sys.stderr,
        )
        for where, value in mismatches:
            print(f"  {where} = {value!r}", file=sys.stderr)
        print(
            "\nAlle Stellen im selben Commit bumpen. Hinweis: publish.yml "
            "überschreibt server.json beim Veröffentlichen ohnehin aus dem Tag — "
            "die committete Version bleibt trotzdem die, die Menschen lesen.",
            file=sys.stderr,
        )
        sys.exit(1)

    hardcoded = find_hardcoded(dist)
    if hardcoded:
        print("HARDCODED: Versionsnummer in src/ gefunden:", file=sys.stderr)
        for path, lineno, line in hardcoded:
            print(f"  {path}:{lineno}: {line}", file=sys.stderr)
        print(
            "\nDie Laufzeit-Version kommt aus den Paket-Metadaten "
            "(`__version__`, gespeist aus importlib.metadata). Statt eines "
            "Literals von dort lesen — sonst beginnt dieselbe Drift von vorn.",
            file=sys.stderr,
        )
        sys.exit(1)

    ruff_status = check_ruff_pins()

    checked = ", ".join(where for where, _ in found) or "keine weiteren Stellen"
    print(f"Versions-Sync OK ({version}; geprüft: {checked}; keine hartkodierte Version in src/)")
    print(ruff_status)


if __name__ == "__main__":
    main()
