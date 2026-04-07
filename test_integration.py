"""
test_integration.py
===================
Tests d'intégration pour les deux dashboards (quefaire.be & site de la ville).

Plan de test :
  1. quefaire.be (port 5000) — 5 événements par ville, puis 2 événements toutes villes
  2. site de la ville (port 5001) — scraping par ville, puis toutes villes

Usage :
  python test_integration.py                  # lance tous les tests
  python test_integration.py --qf             # quefaire.be uniquement
  python test_integration.py --sv             # site de la ville uniquement
  python test_integration.py --skip-scrape    # ne teste que les API (pas de lancement de scraping)
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

# ── Configuration ────────────────────────────────────────────

QF_BASE = "http://localhost:5000"
SV_BASE = "http://localhost:5001"

QF_CITIES = ["charleroi", "la-louvière", "liège", "mons", "namur"]
SV_CITIES = ["charleroi", "lalouviere", "liege", "mons", "namur"]

POLL_INTERVAL = 3        # secondes entre chaque vérification de tâche
POLL_TIMEOUT  = 300      # timeout global par tâche (5 min)

# ── Helpers ──────────────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    events_count: int = 0

@dataclass
class TestSuite:
    results: list = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        icon = "✅" if result.passed else "❌"
        print(f"  {icon} [{status}] {result.name}", end="")
        if result.events_count:
            print(f" — {result.events_count} événement(s)")
        elif result.detail:
            print(f" — {result.detail}")
        else:
            print()

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        print(f"\n{'='*60}")
        print(f"Résultat : {passed}/{total} tests passés", end="")
        if failed:
            print(f"  ({failed} échec(s))")
        else:
            print("  🎉")
        print(f"{'='*60}\n")
        if failed:
            print("Tests échoués :")
            for r in self.results:
                if not r.passed:
                    print(f"  ❌ {r.name} — {r.detail}")
        return failed == 0


def _check_server(base_url: str, name: str) -> bool:
    """Vérifie qu'un serveur est accessible."""
    try:
        r = requests.get(f"{base_url}/api/cities", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        print(f"  ⚠️  Serveur {name} ({base_url}) inaccessible.")
        return False


def _poll_task(base_url: str, task_id: str) -> dict:
    """Attend la fin d'une tâche et retourne son statut final."""
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        try:
            r = requests.get(f"{base_url}/api/tasks/{task_id}", timeout=10)
            data = r.json()
            status = data.get("status", "unknown")
            if status in ("success", "error", "failed"):
                return data
        except (requests.RequestException, json.JSONDecodeError):
            pass
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    return {"status": "timeout", "output": [f"Timeout après {POLL_TIMEOUT}s"]}


def _poll_tasks(base_url: str, task_ids: list) -> list:
    """Attend la fin de plusieurs tâches."""
    results = []
    for tid in task_ids:
        results.append(_poll_task(base_url, tid))
    return results


def _get_city_events(base_url: str, city: str) -> tuple:
    """Récupère les événements d'une ville. Retourne (events_list, error_str | None)."""
    try:
        r = requests.get(f"{base_url}/api/city/{city}/events", timeout=10)
        if r.status_code != 200:
            return [], f"HTTP {r.status_code}"
        data = r.json()
        return data.get("events", []), None
    except requests.RequestException as e:
        return [], str(e)


# ── Tests quefaire.be ────────────────────────────────────────

def test_qf_server_alive(suite: TestSuite) -> bool:
    ok = _check_server(QF_BASE, "quefaire.be")
    suite.add(TestResult("QF: serveur accessible", ok, "" if ok else "Connexion refusée"))
    return ok


def test_qf_cities_endpoint(suite: TestSuite):
    try:
        r = requests.get(f"{QF_BASE}/api/cities", timeout=5)
        data = r.json()
        cities = [c.get("city", c.get("slug", c)) if isinstance(c, dict) else c for c in data]
        ok = all(c in cities for c in QF_CITIES)
        suite.add(TestResult("QF: /api/cities retourne les 5 villes", ok,
                             f"Reçu: {cities}" if not ok else ""))
    except Exception as e:
        suite.add(TestResult("QF: /api/cities", False, str(e)))


def test_qf_single_city_events(suite: TestSuite, city: str, max_events: int = 5):
    """Lance extract-details pour UNE ville avec max_events, attend la fin, vérifie les events."""
    test_name = f"QF: extract-details {city} (max {max_events})"
    try:
        r = requests.post(f"{QF_BASE}/api/run/extract-details",
                          json={"city": city, "max_events": max_events}, timeout=10)
        if r.status_code != 200:
            suite.add(TestResult(test_name, False, f"HTTP {r.status_code}: {r.text[:200]}"))
            return

        data = r.json()
        task_id = data.get("task_id")
        if not task_id:
            suite.add(TestResult(test_name, False, f"Pas de task_id: {data}"))
            return

        print(f"    ⏳ Tâche {task_id} lancée pour {city}…")
        result = _poll_task(QF_BASE, task_id)
        status = result.get("status")

        if status != "success":
            last_lines = result.get("output", [])[-5:]
            suite.add(TestResult(test_name, False,
                                 f"status={status}, dernières lignes: {last_lines}"))
            return

        # Vérifier qu'il y a des événements
        events, err = _get_city_events(QF_BASE, city)
        if err:
            suite.add(TestResult(test_name, False, f"events GET échoué: {err}"))
            return

        suite.add(TestResult(test_name, len(events) > 0,
                             "Aucun événement retourné" if not events else "",
                             events_count=len(events)))

    except Exception as e:
        suite.add(TestResult(test_name, False, str(e)))


def test_qf_batch_all_cities(suite: TestSuite, max_events: int = 2):
    """Lance extract-details pour TOUTES les villes en batch, attend la fin."""
    test_name = f"QF: batch toutes villes (max {max_events})"
    try:
        r = requests.post(f"{QF_BASE}/api/run/extract-details",
                          json={"cities": QF_CITIES, "max_events": max_events}, timeout=10)
        if r.status_code != 200:
            suite.add(TestResult(test_name, False, f"HTTP {r.status_code}: {r.text[:200]}"))
            return

        data = r.json()
        task_ids = data.get("task_ids", [])
        if not task_ids:
            suite.add(TestResult(test_name, False, f"Pas de task_ids: {data}"))
            return

        print(f"    ⏳ {len(task_ids)} tâche(s) lancées (batch)…")
        results = _poll_tasks(QF_BASE, task_ids)

        all_ok = all(r.get("status") == "success" for r in results)
        failed_cities = [r.get("city", "?") for r in results if r.get("status") != "success"]

        if not all_ok:
            suite.add(TestResult(test_name, False, f"Échec pour: {failed_cities}"))
            return

        # Vérifier les événements pour chaque ville
        total = 0
        for city in QF_CITIES:
            events, _ = _get_city_events(QF_BASE, city)
            total += len(events)

        suite.add(TestResult(test_name, total > 0,
                             "Aucun événement" if total == 0 else "",
                             events_count=total))

    except Exception as e:
        suite.add(TestResult(test_name, False, str(e)))


# ── Tests site de la ville ───────────────────────────────────

def test_sv_server_alive(suite: TestSuite) -> bool:
    ok = _check_server(SV_BASE, "site de la ville")
    suite.add(TestResult("SV: serveur accessible", ok, "" if ok else "Connexion refusée"))
    return ok


def test_sv_cities_endpoint(suite: TestSuite):
    try:
        r = requests.get(f"{SV_BASE}/api/cities", timeout=5)
        data = r.json()
        cities = [c.get("city", c.get("slug", c)) if isinstance(c, dict) else c for c in data]
        ok = all(c in cities for c in SV_CITIES)
        suite.add(TestResult("SV: /api/cities retourne les 5 villes", ok,
                             f"Reçu: {cities}" if not ok else ""))
    except Exception as e:
        suite.add(TestResult("SV: /api/cities", False, str(e)))


def test_sv_single_city_scrape(suite: TestSuite, city: str):
    """Lance extract-details pour UNE ville, attend la fin, vérifie les events."""
    test_name = f"SV: extract-details {city}"
    try:
        r = requests.post(f"{SV_BASE}/api/run/extract-details",
                          json={"city": city}, timeout=10)
        if r.status_code != 200:
            suite.add(TestResult(test_name, False, f"HTTP {r.status_code}: {r.text[:200]}"))
            return

        data = r.json()
        task_id = data.get("task_id")
        if not task_id:
            suite.add(TestResult(test_name, False, f"Pas de task_id: {data}"))
            return

        print(f"    ⏳ Tâche {task_id} lancée pour {city}…")
        result = _poll_task(SV_BASE, task_id)
        status = result.get("status")

        if status != "success":
            last_lines = result.get("output", [])[-5:]
            suite.add(TestResult(test_name, False,
                                 f"status={status}, dernières lignes: {last_lines}"))
            return

        events, err = _get_city_events(SV_BASE, city)
        if err:
            suite.add(TestResult(test_name, False, f"events GET échoué: {err}"))
            return

        suite.add(TestResult(test_name, len(events) > 0,
                             "Aucun événement retourné" if not events else "",
                             events_count=len(events)))

    except Exception as e:
        suite.add(TestResult(test_name, False, str(e)))


def test_sv_batch_all_cities(suite: TestSuite):
    """Lance extract-details pour TOUTES les villes en batch, attend la fin."""
    test_name = "SV: batch toutes villes"
    try:
        r = requests.post(f"{SV_BASE}/api/run/extract-details",
                          json={"cities": SV_CITIES}, timeout=10)
        if r.status_code != 200:
            suite.add(TestResult(test_name, False, f"HTTP {r.status_code}: {r.text[:200]}"))
            return

        data = r.json()
        task_ids = data.get("task_ids", [])
        if not task_ids:
            suite.add(TestResult(test_name, False, f"Pas de task_ids: {data}"))
            return

        print(f"    ⏳ {len(task_ids)} tâche(s) lancées (batch)…")
        results = _poll_tasks(SV_BASE, task_ids)

        all_ok = all(r.get("status") == "success" for r in results)
        failed_cities = [r.get("city", "?") for r in results if r.get("status") != "success"]

        if not all_ok:
            suite.add(TestResult(test_name, False, f"Échec pour: {failed_cities}"))
            return

        total = 0
        for city in SV_CITIES:
            events, _ = _get_city_events(SV_BASE, city)
            total += len(events)

        suite.add(TestResult(test_name, total > 0,
                             "Aucun événement" if total == 0 else "",
                             events_count=total))

    except Exception as e:
        suite.add(TestResult(test_name, False, str(e)))


# ── Tests rapides (sans scraping) ────────────────────────────

def test_qf_existing_events(suite: TestSuite):
    """Vérifie que les événements existants sont accessibles via l'API."""
    for city in QF_CITIES:
        events, err = _get_city_events(QF_BASE, city)
        name = f"QF: events existants {city}"
        if err:
            suite.add(TestResult(name, False, err))
        else:
            suite.add(TestResult(name, True, "", events_count=len(events)))


def test_sv_existing_events(suite: TestSuite):
    """Vérifie que les événements existants sont accessibles via l'API."""
    for city in SV_CITIES:
        events, err = _get_city_events(SV_BASE, city)
        name = f"SV: events existants {city}"
        if err:
            suite.add(TestResult(name, False, err))
        else:
            suite.add(TestResult(name, True, "", events_count=len(events)))


def test_qf_tasks_endpoint(suite: TestSuite):
    try:
        r = requests.get(f"{QF_BASE}/api/tasks", timeout=5)
        ok = r.status_code == 200 and isinstance(r.json(), list)
        suite.add(TestResult("QF: /api/tasks accessible", ok))
    except Exception as e:
        suite.add(TestResult("QF: /api/tasks accessible", False, str(e)))


def test_sv_tasks_endpoint(suite: TestSuite):
    try:
        r = requests.get(f"{SV_BASE}/api/tasks", timeout=5)
        ok = r.status_code == 200 and isinstance(r.json(), list)
        suite.add(TestResult("SV: /api/tasks accessible", ok))
    except Exception as e:
        suite.add(TestResult("SV: /api/tasks accessible", False, str(e)))


def test_qf_invalid_city(suite: TestSuite):
    """Vérifie que le serveur rejette une ville inconnue."""
    try:
        r = requests.post(f"{QF_BASE}/api/run/extract-details",
                          json={"city": "bruxelles"}, timeout=5)
        ok = r.status_code == 400
        suite.add(TestResult("QF: ville inconnue → 400", ok,
                             f"status={r.status_code}" if not ok else ""))
    except Exception as e:
        suite.add(TestResult("QF: ville inconnue → 400", False, str(e)))


def test_sv_invalid_city(suite: TestSuite):
    try:
        r = requests.post(f"{SV_BASE}/api/run/extract-details",
                          json={"city": "bruxelles"}, timeout=5)
        ok = r.status_code == 400
        suite.add(TestResult("SV: ville inconnue → 400", ok,
                             f"status={r.status_code}" if not ok else ""))
    except Exception as e:
        suite.add(TestResult("SV: ville inconnue → 400", False, str(e)))


# ── Orchestration ────────────────────────────────────────────

def run_quefaire_tests(suite: TestSuite, skip_scrape: bool = False):
    print("\n" + "="*60)
    print("  TESTS quefaire.be (port 5000)")
    print("="*60)

    if not test_qf_server_alive(suite):
        print("  ⛔ Serveur indisponible, tests quefaire.be ignorés.\n")
        return

    test_qf_cities_endpoint(suite)
    test_qf_tasks_endpoint(suite)
    test_qf_invalid_city(suite)
    test_qf_existing_events(suite)

    if skip_scrape:
        print("  ⏭️  Scraping ignoré (--skip-scrape)")
        return

    print("\n  --- Scraping individuel (2 events/ville) ---")
    for city in QF_CITIES:
        test_qf_single_city_events(suite, city, max_events=2)

    print("\n  --- Scraping batch (1 event/ville, toutes villes) ---")
    test_qf_batch_all_cities(suite, max_events=1)


def run_site_ville_tests(suite: TestSuite, skip_scrape: bool = False):
    print("\n" + "="*60)
    print("  TESTS site de la ville (port 5001)")
    print("="*60)

    if not test_sv_server_alive(suite):
        print("  ⛔ Serveur indisponible, tests site de la ville ignorés.\n")
        return

    test_sv_cities_endpoint(suite)
    test_sv_tasks_endpoint(suite)
    test_sv_invalid_city(suite)
    test_sv_existing_events(suite)

    if skip_scrape:
        print("  ⏭️  Scraping ignoré (--skip-scrape)")
        return

    print("\n  --- Scraping individuel (charleroi uniquement) ---")
    test_sv_single_city_scrape(suite, "charleroi")

    print("\n  --- Scraping batch (toutes villes) ---")
    test_sv_batch_all_cities(suite)


def main():
    parser = argparse.ArgumentParser(description="Tests d'intégration Scrapper-Urban")
    parser.add_argument("--qf", action="store_true", help="Tester uniquement quefaire.be")
    parser.add_argument("--sv", action="store_true", help="Tester uniquement site de la ville")
    parser.add_argument("--skip-scrape", action="store_true",
                        help="Ne pas lancer de scraping, tester seulement les API existantes")
    args = parser.parse_args()

    # Si aucun flag → tester les deux
    test_qf = args.qf or (not args.qf and not args.sv)
    test_sv = args.sv or (not args.qf and not args.sv)

    suite = TestSuite()

    print("\n🔬 Tests d'intégration Scrapper-Urban")
    print(f"   quefaire.be : {'OUI' if test_qf else 'NON'}")
    print(f"   site de la ville : {'OUI' if test_sv else 'NON'}")
    print(f"   scraping : {'NON' if args.skip_scrape else 'OUI'}")

    if test_qf:
        run_quefaire_tests(suite, skip_scrape=args.skip_scrape)

    if test_sv:
        run_site_ville_tests(suite, skip_scrape=args.skip_scrape)

    ok = suite.summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
