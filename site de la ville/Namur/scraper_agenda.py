import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import time
import os
import re

BASE_URL = "https://www.namur.be/fr/agenda"
# La première page est chargée via AJAX faceted query
FIRST_PAGE_URL = "https://www.namur.be/fr/agenda/agenda/@@faceted_query?c4%5B%5D=faceted-agenda-ungrouped-view-items"
BASE_DOMAIN = "https://www.namur.be"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
PAGE_SIZE = 20


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


def get_next_page_url(soup):
    """Vérifier si le lien '20 éléments suivants' est disponible."""
    next_link = soup.find("a", class_="next")
    if next_link and next_link.get("href"):
        href = next_link["href"]
        if href.startswith("/"):
            href = BASE_DOMAIN + href
        return href
    return None


def generate_filename():
    """Générer le nom du fichier .json avec la date du jour."""
    date_str = datetime.now().strftime("%d-%m-%y")
    return f"namur_{date_str}.json"


def scrape_agenda():
    start_time = datetime.now(timezone.utc)
    all_urls = []
    extraction_summary = {}
    events_per_page = []
    page_num = 0
    pages_success = 0
    current_url = FIRST_PAGE_URL

    while current_url:
        page_num += 1
        print(f"[Page {page_num}] Récupération de : {current_url}")
        time.sleep(1 if page_num > 1 else 0)

        try:
            response = requests.get(current_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Erreur lors de la requête : {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")

        page_urls = get_event_urls_from_soup(soup)
        count = len(page_urls)
        print(f"  -> {count} URL(s) trouvée(s)")
        pages_success += 1
        events_per_page.append(count)

        extraction_summary[f"page_{page_num}"] = {
            "url": current_url,
            "events_found": count
        }

        for url in page_urls:
            if url not in all_urls:
                all_urls.append(url)

        next_url = get_next_page_url(soup)
        if next_url:
            print(f"  -> Bouton 'Suivant' trouvé")
            current_url = next_url
        else:
            print("  -> Pas de bouton 'Suivant'. Fin de la pagination.")
            current_url = None

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    print(f"\nTotal : {len(all_urls)} URL(s) récupérée(s)")

    # Construire le JSON Phase 1
    output = {
        "metadata": {
            "region": "Namur",
            "source": "namur.be",
            "scrape_date": start_time.isoformat(),
            "total_events": len(all_urls),
            "total_pages": page_num,
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
                "notes": f"Extraction URLs avec pagination. {len(all_urls)} URLs uniques recuperees en {round(duration)}s."
            },
            "events_extracted": 0,
            "extraction_date": None
        },
        "extraction_summary": extraction_summary,
        "event_urls": all_urls,
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
