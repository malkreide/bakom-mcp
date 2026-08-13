"""Pytest fixtures and collection hooks for bakom-mcp.

Markiert alle bestehenden Tests in test_integration.py / test_20_*.py /
test_scenarios_20.py automatisch als `live`, weil sie gegen Live-APIs
(geo.admin.ch, opendata.swiss, rtvdb.ofcomnet.ch) laufen.

CI ruft `pytest -m "not live"`, lokal optional `pytest -m live` fuer
Integrationschecks gegen die echten APIs.
"""

from __future__ import annotations

import pytest

# Test-Module, deren Funktionen alle Live-APIs ansprechen.
# Werden in CI standardmaessig uebersprungen (pytest -m "not live").
_LIVE_TEST_MODULES: frozenset[str] = frozenset(
    {
        "tests/test_integration.py",
        "tests/test_20_szenarien.py",
        "tests/test_20_neue_szenarien.py",
        "tests/test_scenarios_20.py",
    }
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-applies the `live` marker to tests in known live-API modules."""
    rootpath = config.rootpath
    live_marker = pytest.mark.live
    for item in items:
        try:
            relative = item.path.relative_to(rootpath).as_posix()
        except ValueError:
            continue
        if relative in _LIVE_TEST_MODULES:
            item.add_marker(live_marker)


def _swallowed_errors(item: pytest.Item) -> list[str] | None:
    """Die `results.errors`-Liste des Test-Moduls, falls es eine fuehrt."""
    results = getattr(getattr(item, "module", None), "results", None)
    errors = getattr(results, "errors", None)
    return errors if isinstance(errors, list) else None


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """Meldet verschluckte Fehler der Live-Module an pytest weiter.

    Die Live-Module stammen aus Skripten: jeder Testkoerper faengt `Exception`
    ab und bucht den Fehler auf ein modulweites `TestResult`, das nur auf
    stdout landet. pytest sah davon nichts — die Suite blieb gruen, egal was
    die Quelle antwortete oder ob der Aufruf ueberhaupt zustande kam.

    Hier wird `results.errors` vor und nach dem Testkoerper verglichen; kam ein
    Eintrag dazu, faellt der Test. Module ohne `results` (die echten
    pytest-Tests) sind nicht betroffen.
    """
    errors = _swallowed_errors(item)
    before = len(errors) if errors is not None else 0

    result = yield

    if errors is not None:
        swallowed = errors[before:]
        if swallowed:
            raise AssertionError(
                "Der Testkoerper hat den Fehler abgefangen statt ihn zu melden:\n"
                + "\n".join(f"  - {entry}" for entry in swallowed)
            )
    return result
