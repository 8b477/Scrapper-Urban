import requests
from datetime import datetime, timezone
import json
import time
import os

BASE_URL = "https://www.lalouviere.be/agenda"
API_URL = "https://www.lalouviere.be/agenda/@results"
BASE_DOMAIN = "https://www.lalouviere.be"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}
BATCH_SIZE = 20


def build_event_url(uid, title_slug=""):
    """Construire l'URL locale de l'événement sur lalouviere.be."""
    return f"{BASE_DOMAIN}/agenda/{title_slug}?u={uid}" if title_slug else f"{BASE_DOMAIN}/agenda?u={uid}"


def generate_filename():
    """Générer le nom du fichier .json avec la date du jour."""
    date_str = datetime.now().strftime("%d-%m-%y")
    return f"lalouviere_{date_str}.json"


def scrape_agenda():
    start_time = datetime.now(timezone.utc)
    all_urls = []
    all_api_ids = []
    extraction_summary = {}
    events_per_page = []
    page_num = 0
    pages_success = 0
    b_start = 0
    items_total = None

    while True:
        page_num += 1
        url = f"{API_URL}?b_start={b_start}" if b_start > 0 else API_URL
        print(f"[Page {page_num}] Récupération de : {url}")

        if page_num > 1:
            time.sleep(1)

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  Erreur: {e}")
            break

        items = data.get("items", [])
        if items_total is None:
            items_total = data.get("items_total", 0)
            print(f"  Total événements sur le site: {items_total}")

        count = len(items)
        print(f"  -> {count} événement(s) trouvé(s)")
        pages_success += 1
        events_per_page.append(count)

        extraction_summary[f"page_{page_num}"] = {
            "url": url,
            "events_found": count
        }

        for item in items:
            uid = item.get("UID", "")
            api_id = item.get("@id", "")
            if api_id not in all_api_ids:
                all_api_ids.append(api_id)
                # Construire l'URL locale
                local_url = f"{BASE_DOMAIN}/agenda/?u={uid}"
                all_urls.append(local_url)

        if count == 0:
            break

        # Pagination: vérifier s'il y a un batch suivant
        batching = data.get("batching", {})
        if "next" in batching:
            b_start += BATCH_SIZE
            print(f"  -> Page suivante disponible (b_start={b_start})")
        else:
            print("  -> Pas de page suivante. Fin de la pagination.")
            break

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    print(f"\nTotal : {len(all_urls)} URL(s) récupérée(s)")

    # Construire le JSON Phase 1
    output = {
        "metadata": {
            "region": "La Louvière",
            "source": "lalouviere.be",
            "scrape_date": start_time.isoformat(),
            "total_events": len(all_urls),
            "total_pages": page_num,
            "data_completeness": "Phase 1: Extraction des URLs complétée. Phase 2: Parsing des événements à venir.",
            "extraction_mode": "api_rest",
            "pagination": {
                "total_pages_requested": page_num,
                "pages_successfully_retrieved": pages_success,
                "events_per_page": events_per_page
            },
            "last_execution": {
                "timestamp": end_time.isoformat(),
                "duration_seconds": round(duration, 1),
                "status": "SUCCESS",
                "notes": f"Extraction URLs via API REST SmartWeb. {len(all_urls)} URLs uniques recuperees en {round(duration)}s."
            },
            "events_extracted": 0,
            "extraction_date": None
        },
        "extraction_summary": extraction_summary,
        "event_urls": all_urls,
        "_api_ids": all_api_ids,
        "events": []
    }

    # Sauvegarder le JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, generate_filename())

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"JSON sauvegardé : {filepath}")
    return filepath


if __name__ == "__main__":
    scrape_agenda()
