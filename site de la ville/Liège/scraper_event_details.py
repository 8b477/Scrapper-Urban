import sys
import os
import re
import json
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Ajouter le répertoire parent au path pour importer le module common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.utils import generate_id, cleanup_json_data
from common.http_client import create_session
from common.logger import get_logger
from common.plone_helpers import (
    get_detail_li,
    get_detail_li_by_text,
    extract_label_value,
    extract_dates_plone as extract_dates,
    extract_location_plone,
    extract_contact_plone as extract_contact,
    extract_organiser_plone as extract_organiser,
    extract_image_plone,
    extract_description_plone as extract_description,
    extract_audience_plone as extract_audience,
)

logger = get_logger("liege")

BASE_DOMAIN = "https://www.liege.be"

# Session HTTP réutilisable (keep-alive + retry automatique)
_session = create_session()


def extract_location(ul_details):
    """Extraire le lieu (wrapper Liège)."""
    return extract_location_plone(ul_details, default_city="Liège")


def extract_image(event_div):
    """Extraire l'image (wrapper Liège)."""
    return extract_image_plone(event_div, BASE_DOMAIN)


def extract_category(ul_details):
    """Extraire la catégorie depuis li.taxonomy_agenda (spécifique Liège)."""
    li = get_detail_li(ul_details, "taxonomy_agenda")
    if li:
        return extract_label_value(li)
    return ""


def extract_pricing(ul_details):
    """Extraire le tarif depuis li.taxonomy_tarification (spécifique Liège)."""
    li = get_detail_li(ul_details, "taxonomy_tarification")
    if li:
        return extract_label_value(li)
    li = get_detail_li_by_text(ul_details, "tarifs")
    if li:
        return extract_label_value(li)
    return ""


def scrape_event(url):
    """Scraper les détails d'une page événement Liège."""
    try:
        response = _session.get(url, timeout=30)
        if response.status_code == 404:
            logger.warning("404 - Page introuvable: %s", url)
            return None
        response.raise_for_status()
    except Exception as e:
        logger.error("Erreur réseau: %s", e)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Titre
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    # Conteneur principal de l'événement
    event_div = soup.find("div", class_="event")
    if not event_div:
        logger.warning("Pas de div.event trouvé: %s", url)
        return None

    # Liste des détails (métadonnées)
    ul_details = event_div.find("ul", class_="details")

    # Extractions
    dates = extract_dates(event_div, ul_details)
    location = extract_location(ul_details)
    category = extract_category(ul_details)
    pricing = extract_pricing(ul_details)
    audience = extract_audience(ul_details)
    contact = extract_contact(ul_details)
    organiser = extract_organiser(ul_details)
    image_url = extract_image(event_div)
    description = extract_description(event_div)

    # Enrichir la location avec p.adresse si disponible
    addr_p = event_div.find("p", class_="adresse")
    if addr_p:
        addr_text = addr_p.get_text(strip=True)
        location["address"] = addr_text
        cp_match = re.search(r"\b(\d{4})\b", addr_text)
        if cp_match:
            location["postal_code"] = cp_match.group(1)

    # Titre de secours via hCalendar
    if not title:
        hcal = event_div.find("ul", class_="hCalendar-hidden")
        if hcal:
            summary = hcal.find("li", class_="summary")
            if summary:
                title = summary.get_text(strip=True)

    return {
        "id": generate_id(url),
        "url": url,
        "title": title,
        "description": description,
        "category": category,
        "location": location,
        "dates": dates,
        "pricing": pricing,
        "audience": audience,
        "contact": contact,
        "accessibility": True,
        "url_image": image_url,
        "organiser": organiser,
        "parsed_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Trouver le JSON Phase 1 le plus récent
    json_files = [f for f in os.listdir(script_dir) if f.startswith("liege_") and f.endswith(".json")]
    if not json_files:
        logger.error("Aucun fichier liege_*.json trouvé. Lancez d'abord scraper_agenda.py.")
        return

    json_file = sorted(json_files)[-1]
    json_path = os.path.join(script_dir, json_file)
    logger.info("Lecture du JSON Phase 1 : %s", json_file)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls = data.get("event_urls", [])
    logger.info("%d URL(s) à scraper", len(urls))

    start_time = datetime.now(timezone.utc)
    events = []
    success = 0
    errors = 0

    for i, url in enumerate(urls, 1):
        event = scrape_event(url)
        if event:
            title = event.get('title', '')[:50]
            sched = event.get('dates', {}).get('schedules', [])
            sched_str = sched[0][:50] if sched else "pas de date"
            logger.info("[%d/%d] %s | %s", i, len(urls), title, sched_str)
            events.append(event)
            success += 1
        else:
            logger.warning("[%d/%d] ECHEC", i, len(urls))
            errors += 1

        if i < len(urls):
            time.sleep(0.5)

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Mettre à jour le JSON avec les résultats Phase 2
    data["metadata"]["events_extracted"] = success
    data["metadata"]["extraction_date"] = end_time.isoformat()
    data["metadata"]["data_completeness"] = f"Phase 1: {len(urls)} URLs extraites. Phase 2: {success}/{len(urls)} événements parsés ({errors} erreurs)."
    data["metadata"]["last_execution"] = {
        "timestamp": end_time.isoformat(),
        "duration_seconds": round(duration, 1),
        "status": "SUCCESS" if errors == 0 else "PARTIAL",
        "notes": f"Phase 2 terminée. {success} événements parsés en {round(duration)}s."
    }
    data["events"] = events

    # Nettoyer les données avant sauvegarde
    data = cleanup_json_data(data)

    # Sauvegarder le JSON mis à jour
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("Total: %d événement(s) scrapé(s), %d erreur(s)", success, errors)
    logger.info("JSON mis à jour : %s", json_path)


if __name__ == "__main__":
    main()
