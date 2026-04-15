import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urlparse
import json
import time
import re
import os

BASE_URL = "https://www.charleroi.be/agenda"
BASE_DOMAIN = "https://www.charleroi.be"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_event_url(url):
    """Vérifier qu'une URL est bien celle d'un événement (pas pagination, pas page agenda)."""
    if re.match(r"https://www\.charleroi\.be/agenda(/page/\d+)?$", url):
        return False
    return url.startswith("https://www.charleroi.be/agenda/")


def get_event_urls(soup):
    """Extraire les URLs des événements depuis les balises <a> dans les divs grille."""
    urls = []
    grids = soup.find_all("div", class_=lambda c: c and "tw:grid" in c and "tw:gap-5" in c)
    for grid in grids:
        links = grid.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if href.startswith("/"):
                href = BASE_DOMAIN + href
            if is_event_url(href) and href not in urls:
                urls.append(href)
    return urls


def get_next_page_url(soup):
    """Vérifier si le bouton 'Suivant' est disponible et retourner son URL."""
    next_link = soup.find("a", attrs={"rel": "next"})
    if next_link and next_link.get("href"):
        href = next_link["href"]
        if href.startswith("/"):
            href = BASE_DOMAIN + href
        return href
    return None


def generate_filename():
    """Générer le nom du fichier à partir de la date du jour."""
    date_str = datetime.now().strftime("%d-%m-%y")
    return f"charleroi_{date_str}.json"


def scrape_agenda():
    start_time = datetime.now(timezone.utc)
    all_urls = []
    extraction_summary = {}
    events_per_page = []
    current_url = BASE_URL
    page_num = 1
    pages_success = 0

    while current_url:
        print(f"[Page {page_num}] Récupération de : {current_url}")
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Erreur lors de la requête : {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")

        # Extraire les URLs de la page courante
        page_urls = get_event_urls(soup)
        count = len(page_urls)
        print(f"  -> {count} URL(s) trouvée(s)")
        pages_success += 1
        events_per_page.append(count)

        # Résumé par page
        extraction_summary[f"page_{page_num}"] = {
            "url": current_url,
            "events_found": count
        }

        for url in page_urls:
            if url not in all_urls:
                all_urls.append(url)

        # Vérifier le bouton suivant
        next_url = get_next_page_url(soup)
        if next_url:
            print(f"  -> Bouton 'Suivant' trouvé : {next_url}")
            current_url = next_url
            page_num += 1
            time.sleep(1)
        else:
            print("  -> Pas de bouton 'Suivant'. Fin de la pagination.")
            current_url = None

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    print(f"\nTotal : {len(all_urls)} URL(s) récupérée(s)")

    # Construire le JSON Phase 1
    output = {
        "metadata": {
            "region": "Charleroi",
            "source": "charleroi.be",
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
