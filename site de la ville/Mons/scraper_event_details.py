import sys
import os
import re
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

# Ajouter le répertoire parent au path pour importer le module common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.utils import generate_id, cleanup_json_data, format_iso_to_readable, html_to_text
from common.http_client import create_session
from common.logger import get_logger

logger = get_logger("mons")

API_RESULTS_URL = "https://www.mons.be/fr/que-faire-a-mons/agenda/@results"

# Session HTTP réutilisable (keep-alive + retry automatique)
_session = create_session(headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
})

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
    "flea_market_market": "Brocante et marché",
    "market": "Marché",
    "other": "Autre",
}


# generate_id importé depuis common.utils


def extract_uid(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    uids = params.get("u", [])
    return uids[0] if uids else ""


# html_to_text importé depuis common.utils


def translate_category(token):
    if isinstance(token, dict):
        return token.get("title", token.get("token", ""))
    if isinstance(token, list):
        return ", ".join(translate_category(t) for t in token)
    return CATEGORY_MAP.get(token, token or "")


def _format_iso_to_readable(iso_str):
    """Wrapper vers la fonction commune."""
    return format_iso_to_readable(iso_str)


# cleanup_json_data importé depuis common.utils


def fetch_all_api_items():
    """Récupérer tous les items de l'API @results avec pagination."""
    all_items = []
    b_start = 0
    page = 0
    while True:
        page += 1
        url = f"{API_RESULTS_URL}?b_start={b_start}" if b_start > 0 else API_RESULTS_URL
        logger.info("[API page %d] %s", page, url)
        try:
            resp = _session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except (Exception, ValueError) as e:
            logger.error("Erreur API: %s", e)
            break

        items = data.get("items", [])
        if not items:
            break
        all_items.extend(items)
        logger.info("%d items (total: %d)", len(items), len(all_items))

        if "next" in data.get("batching", {}):
            b_start += 20
            time.sleep(0.5)
        else:
            break
    return all_items


def fetch_event_detail(api_url):
    try:
        response = _session.get(api_url, timeout=30)
        if response.status_code == 404:
            logger.warning("404 pour %s", api_url)
            return None
        response.raise_for_status()
        return response.json()
    except (Exception, ValueError) as e:
        logger.error("Erreur: %s", e)
        return None


def build_event(detail, local_url, occ_start, occ_end):
    title = detail.get("title", "")

    text_field = detail.get("text", {})
    description = ""
    if isinstance(text_field, dict):
        description = html_to_text(text_field.get("data", ""))
    elif isinstance(text_field, str):
        description = text_field
    if not description:
        desc = detail.get("description", "")
        description = desc.get("data", "") if isinstance(desc, dict) else desc

    category = translate_category(detail.get("category", ""))

    location = {
        "venue": "",
        "address": "",
        "postal_code": str(detail.get("zipcode", "")) if detail.get("zipcode") else "",
        "city": detail.get("city", "") or "Mons"
    }
    parent = detail.get("parent", {})
    if isinstance(parent, dict):
        location["venue"] = parent.get("title", "")
    if not location["venue"]:
        location["venue"] = detail.get("contact_name", "") or ""
    street = detail.get("street", "") or ""
    number = detail.get("number", "") or ""
    complement = detail.get("complement", "") or ""
    if street:
        addr_parts = [street]
        if number:
            addr_parts.append(number)
        if complement:
            addr_parts.append(complement)
        location["address"] = " ".join(addr_parts)

    start = occ_start or detail.get("start", "") or ""
    end = occ_end or detail.get("end", "") or ""
    schedules = []
    if start and end:
        schedules.append(f"Du {_format_iso_to_readable(start)} au {_format_iso_to_readable(end)}")
    elif start:
        schedules.append(f"Le {_format_iso_to_readable(start)}")

    pricing = "Gratuit" if detail.get("free_entry", False) else "Payant"

    contact = {
        "phone": detail.get("contact_phone", "") or "",
        "website": detail.get("event_url", "") or ""
    }

    image_url = ""
    image_field = detail.get("image", {})
    if isinstance(image_field, dict) and image_field.get("download"):
        image_url = image_field["download"]
    if not image_url:
        image_url = detail.get("image_full_scale", "") or detail.get("image_affiche_scale", "") or ""

    iam = detail.get("iam", []) or []
    audience_str = ""
    if iam:
        parts = []
        for item in iam:
            if isinstance(item, dict):
                parts.append(item.get("title", item.get("token", str(item))))
            else:
                parts.append(str(item))
        audience_str = ", ".join(parts)

    organiser = ""
    if isinstance(parent, dict):
        organiser = parent.get("title", "")
    if not organiser:
        api_id = detail.get("@id", "")
        parts = [p for p in api_id.split("/") if p and p != "mons"]
        if len(parts) >= 2:
            organiser = parts[-2].replace("-", " ").title()

    accessibility = detail.get("reduced_mobility_facilities", True)

    dates = {"schedules": schedules}
    if start:
        dates["start"] = start
    if end:
        dates["end"] = end

    unique_key = f"{local_url}_{start}_{end}"

    return {
        "id": generate_id(unique_key),
        "url": local_url,
        "title": title,
        "description": description,
        "category": category,
        "location": location,
        "dates": dates,
        "pricing": pricing,
        "audience": audience_str,
        "contact": contact,
        "accessibility": accessibility,
        "url_image": image_url,
        "organiser": organiser,
        "parsed_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    json_files = [f for f in os.listdir(script_dir) if f.startswith("mons_") and f.endswith(".json")]
    if not json_files:
        logger.error("Aucun fichier mons_*.json trouvé. Lancez d'abord scraper_agenda.py.")
        return

    json_file = sorted(json_files)[-1]
    json_path = os.path.join(script_dir, json_file)
    logger.info("Lecture du JSON Phase 1 : %s", json_file)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls = data.get("event_urls", [])
    logger.info("%d URL(s) à traiter", len(urls))

    # Extraire les UIDs depuis les URLs
    url_uids = [(url, extract_uid(url)) for url in urls]
    unique_uids = set(uid for _, uid in url_uids if uid)
    logger.info("%d UID(s) unique(s)", len(unique_uids))

    # Récupérer tous les items API pour construire le mapping UID -> occurrences
    logger.info("Récupération des items API (@results)...")
    api_items = fetch_all_api_items()
    logger.info("%d item(s) API total", len(api_items))

    # Construire le mapping UID -> [list of {api_id, start, end}] en ordre
    uid_occurrences = {}
    for item in api_items:
        uid = item.get("UID", "")
        if uid:
            if uid not in uid_occurrences:
                uid_occurrences[uid] = []
            uid_occurrences[uid].append({
                "api_id": item.get("@id", ""),
                "start": item.get("start", ""),
                "end": item.get("end", ""),
            })

    # Récupérer les détails pour chaque UID unique (cache)
    logger.info("Récupération des détails pour %d UID(s) unique(s)...", len(unique_uids))
    detail_cache = {}
    for i, uid in enumerate(sorted(unique_uids), 1):
        occs = uid_occurrences.get(uid, [])
        api_url = occs[0]["api_id"] if occs else ""
        if not api_url:
            logger.warning("[%d/%d] UID %s - pas d'URL API connue, SKIP", i, len(unique_uids), uid[:12])
            continue
        detail = fetch_event_detail(api_url)
        if detail:
            logger.info("[%d/%d] %s", i, len(unique_uids), detail.get('title', '')[:50])
            detail_cache[uid] = detail
        else:
            logger.warning("[%d/%d] ECHEC", i, len(unique_uids))
        time.sleep(0.3)

    logger.info("%d/%d détails récupérés", len(detail_cache), len(unique_uids))

    # Construire un compteur pour suivre quelle occurrence on utilise par UID
    uid_occ_index = {uid: 0 for uid in unique_uids}

    start_time = datetime.now(timezone.utc)
    events = []
    success = 0
    errors = 0

    for i, (local_url, uid) in enumerate(url_uids, 1):
        if not uid:
            logger.warning("[%d/%d] SKIP - pas de UID dans l'URL", i, len(urls))
            errors += 1
            continue

        detail = detail_cache.get(uid)
        if not detail:
            logger.warning("[%d/%d] SKIP - pas de détail pour UID %s", i, len(urls), uid[:12])
            errors += 1
            continue

        # Récupérer les dates de l'occurrence courante
        occs = uid_occurrences.get(uid, [])
        idx = uid_occ_index.get(uid, 0)
        if idx < len(occs):
            occ_start = occs[idx]["start"]
            occ_end = occs[idx]["end"]
            uid_occ_index[uid] = idx + 1
        else:
            occ_start = detail.get("start", "")
            occ_end = detail.get("end", "")

        event = build_event(detail, local_url, occ_start, occ_end)
        title = event['title'][:40]
        sched = event['dates']['schedules'][0][:50] if event['dates']['schedules'] else ""
        logger.info("[%d/%d] %s | %s", i, len(urls), title, sched)
        events.append(event)
        success += 1

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    data["metadata"]["events_extracted"] = success
    data["metadata"]["extraction_date"] = end_time.isoformat()
    data["metadata"]["data_completeness"] = f"Phase 1: {len(urls)} URLs extraites. Phase 2: {success}/{len(urls)} événements parsés ({errors} erreurs)."
    data["metadata"]["last_execution"] = {
        "timestamp": end_time.isoformat(),
        "duration_seconds": round(duration, 1),
        "status": "SUCCESS" if errors == 0 else "PARTIAL",
        "notes": f"Phase 2 terminée. {success} événements parsés ({len(detail_cache)} appels API uniques)."
    }
    data["events"] = events

    # Nettoyer les données avant sauvegarde
    data = cleanup_json_data(data)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("Total: %d événement(s) scrapé(s), %d erreur(s)", success, errors)
    logger.info("JSON mis à jour : %s", json_path)


if __name__ == "__main__":
    main()
