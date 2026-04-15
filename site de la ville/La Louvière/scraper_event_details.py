import sys
import os
import re
import json
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Ajouter le répertoire parent au path pour importer le module common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.utils import generate_id, cleanup_json_data, format_iso_to_readable, html_to_text
from common.http_client import create_session
from common.logger import get_logger

logger = get_logger("lalouviere")

# Session HTTP réutilisable (keep-alive + retry automatique)
_session = create_session(headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
})

# Mapping des catégories internes vers labels français
CATEGORY_MAP = {
    "internships_courses": "Stages et cours",
    "exhibition_artistic_meeting": "Exposition et rencontre artistique",
    "music": "Musique",
    "show": "Spectacle",
    "conference_debate": "Conférence et débat",
    "festival": "Festival",
    "fair": "Foire et salon",
    "sport": "Sport",
    "visit_discovery": "Visite et découverte",
    "party_folklore": "Fête et folklore",
    "market": "Marché",
    "other": "Autre",
}

TOPIC_MAP = {
    "entertainment": "Activités et divertissement",
    "culture": "Culture",
    "sports": "Sports",
    "health": "Santé",
    "education": "Éducation",
    "environment": "Environnement",
    "social": "Social",
}


# generate_id et cleanup_json_data importés depuis common.utils
# html_to_text importé depuis common.utils


def translate_category(token):
    """Traduire un token de catégorie en label français."""
    if isinstance(token, dict):
        return token.get("title", token.get("token", ""))
    if isinstance(token, list):
        return ", ".join(translate_category(t) for t in token)
    return CATEGORY_MAP.get(token, token or "")


def _format_iso_to_readable(iso_str):
    """Wrapper vers la fonction commune."""
    return format_iso_to_readable(iso_str)


def translate_topics(topics_list):
    """Traduire une liste de topics en labels français."""
    if not topics_list:
        return []
    result = []
    for t in topics_list:
        if isinstance(t, dict):
            result.append(t.get("title", t.get("token", "")))
        else:
            result.append(TOPIC_MAP.get(t, t))
    return result


def scrape_event(api_url, local_url):
    """Récupérer les détails d'un événement via l'API REST."""
    try:
        response = _session.get(api_url, timeout=30)
        if response.status_code == 404:
            logger.warning("404 - Événement introuvable")
            return None
        response.raise_for_status()
        data = response.json()
    except (Exception, ValueError) as e:
        logger.error("Erreur: %s", e)
        return None

    # Titre
    title = data.get("title", "")

    # Description - texte complet depuis le champ 'text'
    text_field = data.get("text", {})
    description = ""
    if isinstance(text_field, dict):
        html_content = text_field.get("data", "")
        description = html_to_text(html_content)
    elif isinstance(text_field, str):
        description = text_field

    # Si pas de texte complet, utiliser la description courte
    if not description:
        description = data.get("description", "")
        if isinstance(description, dict):
            description = description.get("data", "")

    # Catégorie
    category_token = data.get("category", "")
    category = translate_category(category_token)

    # Topics / thèmes
    topics = data.get("topics", []) or []
    if isinstance(topics, list):
        topics = translate_topics(topics)

    # Location
    location = {
        "venue": data.get("usefull_container_title", "") or "",
        "address": "",
        "postal_code": str(data.get("zipcode", "")) if data.get("zipcode") else "",
        "city": data.get("city", "") or ""
    }
    # Construire l'adresse
    street = data.get("street", "") or ""
    number = data.get("number", "") or ""
    complement = data.get("complement", "") or ""
    if street:
        addr_parts = [street]
        if number:
            addr_parts.append(number)
        if complement:
            addr_parts.append(complement)
        location["address"] = " ".join(addr_parts)

    # Dates
    start = data.get("start", "") or data.get("first_start", "") or ""
    end = data.get("end", "") or data.get("first_end", "") or ""

    schedules = []
    if start and end:
        schedules.append(f"Du {_format_iso_to_readable(start)} au {_format_iso_to_readable(end)}")
    elif start:
        schedules.append(f"Le {_format_iso_to_readable(start)}")

    dates = {"schedules": schedules}
    if start:
        dates["start"] = start
    if end:
        dates["end"] = end

    # Pricing
    free_entry = data.get("free_entry", False)
    pricing = "Gratuit" if free_entry else "Payant"

    # Contact
    contact = {
        "phone": data.get("contact_phone", "") or "",
        "email": data.get("contact_email", "") or "",
        "name": data.get("contact_name", "") or "",
        "website": data.get("event_url", "") or ""
    }

    # Réseaux sociaux
    social = {}
    if data.get("facebook"):
        social["facebook"] = data["facebook"]
    if data.get("instagram"):
        social["instagram"] = data["instagram"]
    if data.get("twitter"):
        social["twitter"] = data["twitter"]

    # Image - dans le détail c'est un dict avec 'download', dans le listing c'est image_full_scale
    image_url = ""
    image_field = data.get("image", {})
    if isinstance(image_field, dict) and image_field.get("download"):
        image_url = image_field["download"]
    if not image_url:
        image_url = data.get("image_full_scale", "") or data.get("image_affiche_scale", "") or ""

    # Géolocation
    geolocation = data.get("geolocation", {}) or {}

    # Audience / IAM
    iam = data.get("iam", []) or []

    # Vidéo
    video_url = data.get("video_url", "") or ""

    # Organiseur - déduit du parent container
    organiser = ""
    parent = data.get("parent", {})
    if isinstance(parent, dict):
        organiser = parent.get("title", "")
    if not organiser:
        # Fallback: extraire du path @id
        api_id = data.get("@id", "")
        parts = [p for p in api_id.split("/") if p and p != "la-louviere"]
        if len(parts) >= 2:
            organiser = parts[-2].replace("-", " ").title()

    # Audience en string (comme Charleroi)
    if iam:
        parts = []
        for item in iam:
            if isinstance(item, dict):
                parts.append(item.get("title", item.get("token", str(item))))
            else:
                parts.append(str(item))
        audience_str = ", ".join(parts)
    else:
        audience_str = ""

    return {
        "id": generate_id(local_url),
        "url": local_url,
        "title": title,
        "description": description,
        "category": category,
        "location": location,
        "dates": dates,
        "pricing": pricing,
        "audience": audience_str,
        "contact": {
            "phone": contact["phone"],
            "website": contact["website"]
        },
        "accessibility": True,
        "url_image": image_url,
        "organiser": organiser,
        "parsed_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Trouver le JSON Phase 1 le plus récent
    json_files = [f for f in os.listdir(script_dir) if f.startswith("lalouviere_") and f.endswith(".json")]
    if not json_files:
        logger.error("Aucun fichier lalouviere_*.json trouvé. Lancez d'abord scraper_agenda.py.")
        return

    json_file = sorted(json_files)[-1]
    json_path = os.path.join(script_dir, json_file)
    logger.info("Lecture du JSON Phase 1 : %s", json_file)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls = data.get("event_urls", [])
    api_ids = data.get("_api_ids", [])
    logger.info("%d événement(s) à scraper", len(urls))

    start_time = datetime.now(timezone.utc)
    events = []
    success = 0
    errors = 0

    for i in range(len(api_ids)):
        api_url = api_ids[i]
        local_url = urls[i] if i < len(urls) else api_url
        event = scrape_event(api_url, local_url)
        if event:
            logger.info("[%d/%d] %s | %s", i+1, len(api_ids), event['title'][:50], event['category'])
            events.append(event)
            success += 1
        else:
            logger.warning("[%d/%d] ECHEC", i+1, len(api_ids))
            errors += 1

        if i < len(api_ids) - 1:
            time.sleep(0.3)

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

    # Retirer le champ interne _api_ids du JSON final
    data.pop("_api_ids", None)

    # Nettoyer les données avant sauvegarde
    data = cleanup_json_data(data)

    # Sauvegarder le JSON mis à jour
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("Total: %d événement(s) scrapé(s), %d erreur(s)", success, errors)
    logger.info("JSON mis à jour : %s", json_path)


if __name__ == "__main__":
    main()
