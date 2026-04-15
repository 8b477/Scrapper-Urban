import sys
import os
import re
import json
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Ajouter le répertoire parent au path pour importer le module common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.utils import generate_id, cleanup_json_data, format_iso_to_readable
from common.http_client import create_session
from common.logger import get_logger

logger = get_logger("charleroi")

BASE_DOMAIN = "https://www.charleroi.be"

# Session HTTP réutilisable (keep-alive + retry automatique)
_session = create_session()


def find_info_block(sidebar, icon_name):
    """Trouver un bloc d'info dans la sidebar via le nom de l'icône SVG."""
    for svg in sidebar.find_all("svg"):
        use = svg.find("use")
        if use:
            href = use.get("xlink:href", "") or use.get("href", "")
            if icon_name in href:
                parent = svg.parent
                while parent:
                    if parent.name == "div":
                        cls = parent.get("class", [])
                        if "tw:relative" in cls and any("tw:pl-" in c for c in cls):
                            return parent
                    parent = parent.parent
    return None


def _format_iso_to_readable(iso_str):
    """Convertir une date ISO en texte lisible DD/MM/YYYY HH:MM."""
    return format_iso_to_readable(iso_str)


def _parse_time_text(time_text):
    """Extraire les heures depuis un texte comme 'De 10h00 à 20h00' ou 'à partir de 18h00'."""
    if not time_text:
        return None, None
    times = re.findall(r'(\d{1,2})[h:](\d{2})?', time_text)
    if len(times) >= 2:
        return (int(times[0][0]), int(times[0][1] or 0)), (int(times[1][0]), int(times[1][1] or 0))
    elif len(times) == 1:
        return (int(times[0][0]), int(times[0][1] or 0)), None
    return None, None


def cleanup_json_data_charleroi(data):
    """Wrapper vers la fonction commune."""
    return cleanup_json_data(data)


def extract_dates(sidebar):
    """Extraire les dates et horaires."""
    schedules = []
    dtstart = ""
    dtend = ""

    cal_block = find_info_block(sidebar, "icon-infos-calendar")
    if cal_block:
        time_els = cal_block.find_all("time")
        if len(time_els) >= 2:
            dtstart = time_els[0].get("datetime", time_els[0].get_text(strip=True))
            dtend = time_els[1].get("datetime", time_els[1].get_text(strip=True))
        elif len(time_els) == 1:
            dtstart = time_els[0].get("datetime", time_els[0].get_text(strip=True))
        else:
            text = cal_block.get_text(strip=True)
            if text:
                schedules.append(text)

    # Extraire les heures depuis le bloc horaire
    time_text = ""
    time_block = find_info_block(sidebar, "icon-infos-time")
    if time_block:
        time_text = time_block.get_text(strip=True)

    start_time, end_time = _parse_time_text(time_text)

    # Injecter les heures dans les dates ISO
    if dtstart:
        try:
            dt = datetime.fromisoformat(dtstart)
            if start_time and dt.hour == 0 and dt.minute == 0:
                dt = dt.replace(hour=start_time[0], minute=start_time[1])
            dtstart = dt.isoformat()
        except (ValueError, TypeError):
            pass

    if dtend:
        try:
            dt = datetime.fromisoformat(dtend)
            if dt.hour == 0 and dt.minute == 0:
                t = end_time or start_time
                if t:
                    dt = dt.replace(hour=t[0], minute=t[1])
            dtend = dt.isoformat()
        except (ValueError, TypeError):
            pass

    # Construire le texte lisible des horaires
    if dtstart and dtend:
        sched = f"Du {_format_iso_to_readable(dtstart)} au {_format_iso_to_readable(dtend)}"
        schedules.append(sched)
    elif dtstart:
        sched = f"Le {_format_iso_to_readable(dtstart)}"
        schedules.append(sched)
    elif time_text:
        schedules.append(time_text)

    result = {"schedules": schedules}
    if dtstart:
        result["start"] = dtstart
    if dtend:
        result["end"] = dtend
    return result


def extract_location(sidebar):
    """Extraire le lieu, l'adresse et la ville."""
    location = {"venue": "", "address": "", "postal_code": "", "city": ""}

    loc_block = find_info_block(sidebar, "icon-infos-locality")
    if loc_block:
        strong = loc_block.find("strong")
        if strong:
            location["city"] = strong.get_text(strip=True)

    venue_block = find_info_block(sidebar, "icon-infos-location")
    if venue_block:
        strong = venue_block.find("strong")
        if strong:
            location["venue"] = strong.get_text(strip=True)
        addr_span = venue_block.find("span", class_=lambda c: c and "tw:!text-[#636466]" in c)
        if addr_span:
            address_text = addr_span.get_text(strip=True)
            location["address"] = address_text
            cp_match = re.search(r"\b(\d{4})\b", address_text)
            if cp_match:
                location["postal_code"] = cp_match.group(1)

    return location


def extract_category(sidebar):
    """Extraire la catégorie via icon-infos-category."""
    cat_block = find_info_block(sidebar, "icon-infos-category")
    if cat_block:
        strong = cat_block.find("strong")
        if strong:
            return strong.get_text(strip=True)
    return ""


def extract_image(soup, article):
    """Extraire l'URL de l'image principale de l'événement."""
    wc = soup.find("div", class_=lambda c: c and "webpage" in c and "container" in c)
    if not wc:
        return ""

    if article:
        for a_tag in article.find_all("a", href=True):
            href = a_tag["href"]
            if "assets/images" in href:
                if href.startswith("/"):
                    href = BASE_DOMAIN + href
                return href

    nav = wc.find("nav")
    if nav:
        figure = nav.find("figure")
        if figure:
            img = figure.find("img")
            if img:
                srcset = img.get("data-srcset", "") or img.get("srcset", "")
                if srcset:
                    parts = [p.strip() for p in srcset.split(",") if p.strip()]
                    if parts:
                        last = parts[-1].split()[0]
                        if last.startswith("/"):
                            last = BASE_DOMAIN + last
                        return last
                src = img.get("data-src", "") or img.get("src", "")
                if src and not src.startswith("data:"):
                    if src.startswith("/"):
                        src = BASE_DOMAIN + src
                    return src

    return ""


def extract_description(content_col):
    """Extraire la description textuelle de l'événement."""
    if not content_col:
        return ""

    paragraphs = []
    stop_keywords = ["prix", "lien", "liens", "organisateur", "ceci pourrait"]
    for el in content_col.find_all(["p", "h2", "h3"]):
        if el.name in ("h2", "h3"):
            text_lower = el.get_text(strip=True).lower()
            if any(kw in text_lower for kw in stop_keywords):
                break
        elif el.name == "p":
            text = el.get_text(strip=True)
            if len(text) > 5:
                paragraphs.append(text)

    return "\n".join(paragraphs)


def extract_pricing(content_col):
    """Extraire le prix depuis la section Prix."""
    if not content_col:
        return ""
    for h2 in content_col.find_all("h2"):
        if "prix" in h2.get_text(strip=True).lower():
            next_el = h2.find_next_sibling()
            if next_el:
                return next_el.get_text(strip=True)
            parent = h2.parent
            texts = parent.get_text(strip=True).replace(h2.get_text(strip=True), "").strip()
            return texts
    return ""


def extract_organiser_and_links(content_col):
    """Extraire l'organisateur et les liens externes."""
    website = ""
    organiser = ""

    if not content_col:
        return organiser, website

    for h2 in content_col.find_all("h2"):
        text = h2.get_text(strip=True).lower()
        if "organisateur" in text:
            parent = h2.parent
            for a in parent.find_all("a", href=True):
                organiser = a.get_text(strip=True)
                website = a["href"]
        elif "lien" in text:
            parent = h2.parent
            for a in parent.find_all("a", href=True):
                if not website:
                    website = a["href"]

    return organiser, website


def scrape_event(url):
    """Scraper les détails d'une page événement."""
    try:
        response = _session.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        logger.error("Erreur réseau: %s", e)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    wc = soup.find("div", class_=lambda c: c and "webpage" in c and "container" in c)
    if not wc:
        logger.warning("Pas de container trouvé pour %s", url)
        return None

    sidebar = wc.find("nav")
    if not sidebar:
        sidebar = wc

    content_col = None
    row = wc.find("div", class_="row")
    if row:
        content_col = row.find("article")
        if not content_col:
            for child in row.children:
                if hasattr(child, "name") and child.name and child.name != "nav" and child.find("h2"):
                    content_col = child
                    break

    dates = extract_dates(sidebar)
    location = extract_location(sidebar)
    category = extract_category(sidebar)
    image_url = extract_image(soup, content_col)
    description = extract_description(content_col)
    pricing = extract_pricing(content_col)
    organiser, website = extract_organiser_and_links(content_col)

    return {
        "id": generate_id(url),
        "url": url,
        "title": title,
        "description": description,
        "category": category,
        "location": location,
        "dates": dates,
        "pricing": pricing,
        "audience": "",
        "contact": {
            "phone": "",
            "website": website
        },
        "accessibility": True,
        "url_image": image_url,
        "organiser": organiser,
        "parsed_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Trouver le JSON Phase 1 le plus récent
    json_files = [f for f in os.listdir(script_dir) if f.startswith("charleroi_") and f.endswith(".json")]
    if not json_files:
        logger.error("Aucun fichier charleroi_*.json trouvé. Lancez d'abord scraper_agenda.py.")
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
            logger.info("[%d/%d] %s | %s | %s", i, len(urls), event['title'][:50], event['category'], event['dates']['schedules'])
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
