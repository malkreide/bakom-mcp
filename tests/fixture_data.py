"""Zugriff auf die aufgezeichneten Antworten in `tests/fixtures/`.

Ein Loader statt `open()` an jeder Stelle: so gibt es genau einen Ort, der weiss,
wo die Aufzeichnungen liegen, und die Tests koennen ueber sie iterieren, statt
eine Liste von Hand zu pflegen, die zurueckbleibt.

Neu aufzeichnen mit `PYTHONPATH=src python scripts/record_fixtures.py`; Herkunft,
Datum, Auswahlregel und SHA-256 je Datei stehen in `tests/fixtures/PROVENANCE.md`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_text(name: str) -> str:
    """Die Aufzeichnung als Text — so, wie sie ueber die Leitung kaeme."""
    pfad = FIXTURES / name
    if not pfad.is_file():
        raise FileNotFoundError(f"keine Aufzeichnung {name} in {FIXTURES}")
    return pfad.read_text(encoding="utf-8")


def fixture_json(name: str) -> Any:
    """Die Aufzeichnung geparst."""
    return json.loads(fixture_text(name))


@lru_cache(maxsize=1)
def recorded_names() -> tuple[str, ...]:
    """Alle Aufzeichnungen im Ordner — nicht die, die ein Test erwartet.

    Der Unterschied ist der Punkt: eine Datei, die niemand erwartet, faellt
    sonst niemandem auf.
    """
    return tuple(sorted(p.name for p in FIXTURES.glob("*.json")))


def provenance() -> str:
    return (FIXTURES / "PROVENANCE.md").read_text(encoding="utf-8")
