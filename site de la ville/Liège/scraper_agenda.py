import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import time
import os

BASE_URL = "https://www.liege.be/fr/evenements/agenda"
FACETED_URL = f"{BASE_URL}/@@faceted_query"
BASE_DOMAIN = "https://www.liege.be"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
BATCH_SIZE = 10


def get_event_urls_from_soup(soup):
    """Extraire les URLs des événements depuis les div.event-entry."""
    urls = []
    entries = soup.find_all("div", class_=lambda c: c and "event-entry" in c)
    for entry in entries:
        a = entry.find("a", href=True)
        if a:
            href = a["href"]
            if href.startswith("/"):
                href = BASE_DOMAIN + href
            if href not in urls:
                urls.append(href)
    return urls


def generate_filename():
    """Générer le nom du fichier .json avec la date du jour."""
    date_str = datetime.now().strftime("%d-%m-%y")
    return f"liege_{date_str}.json"


def scrape_agenda():
    start_time = datetime.now(timezone.utc)
    all_urls = []
    extraction_summary = {}
    events_per_page = []
    page_num = 0
    pages_success = 0
    b_start = 0

    while True:
        page_num += 1

        print(f"[Page {page_num}] Récupération via @@faceted_query (b_start={b_start})...")
        if page_num > 1:
            time.sleep(1)

        try:
            response = requests.post(
                FACETED_URL,
                headers=HEADERS,
                data={
                    "c6": "faceted-agenda-ungrouped-view-items",
                    "b_start:int": str(b_start),
                },
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"  Erreur: {e}")
            break

        soup = BeautifulSoup(response.text, "lxml")
        page_urls = get_event_urls_from_soup(soup)
        count = len(page_urls)
        print(f"  -> {count} URL(s) trouvée(s)")

        # Filtrer les doublons
        new_urls = [u for u in page_urls if u not in all_urls]
        if not new_urls:
            print("  -> Aucune nouvelle URL. Fin de la pagination.")
            break

        pages_success += 1
        events_per_page.append(len(new_urls))

        extraction_summary[f"page_{page_num}"] = {
            "url": f"{FACETED_URL}?b_start:int={b_start}",
            "events_found": len(new_urls)
        }

        all_urls.extend(new_urls)

        # Passer à la page suivante
        b_start += BATCH_SIZE

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    print(f"\nTotal : {len(all_urls)} URL(s) récupérée(s)")

    output = {
        "metadata": {
            "region": "Liège",
            "source": "liege.be",
            "scrape_date": start_time.isoformat(),
            "total_events": len(all_urls),
            "total_pages": pages_success,
            "data_completeness": "Phase 1: Extraction des URLs complétée. Phase 2: Parsing des événements à venir.",
            "extraction_mode": "requests",
            "pagination": {
                "total_pages_requested": page_num,
                "pages_successfully_retrieved": pages_success,
                "events_per_page": events_per_page
            },
            "last_execution": {
                "timestamp": end_time.isoformat(),
                "duration_seconds": round(duration, 1),
                "status": "SUCCESS",
                "notes": f"Extraction URLs avec faceted_query. {len(all_urls)} URLs uniques recuperees en {round(duration)}s."
            },
            "events_extracted": 0,
            "extraction_date": None
        },
        "extraction_summary": extraction_summary,
        "event_urls": all_urls,
        "events": []
    }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, generate_filename())

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"JSON sauvegardé : {filepath}")
    return filepath


if __name__ == "__main__":
    scrape_agenda()
