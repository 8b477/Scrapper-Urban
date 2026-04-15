"""
Helpers partagés pour les sites Plone (Liège, Namur).
Ces deux villes utilisent la même structure HTML (div.event, ul.details, hCalendar-hidden).
"""
import re
from bs4 import Tag


def get_detail_li(ul_details: Tag, class_name: str):
    """Trouver un LI par sa classe dans ul.details."""
    if not ul_details:
        return None
    return ul_details.find("li", class_=class_name)


def get_detail_li_by_text(ul_details: Tag, keyword: str):
    """Trouver un LI sans classe spécifique via un mot-clé dans son texte."""
    if not ul_details:
        return None
    for li in ul_details.find_all("li", recursive=False):
        if keyword.lower() in li.get_text().lower():
            return li
    return None


def extract_label_value(li: Tag) -> str:
    """Extraire la valeur après le label (<strong>) d'un LI."""
    if not li:
        return ""
    strong = li.find("strong")
    value_span = li.find("span", recursive=False)
    if value_span and strong:
        return value_span.get_text(strip=True)
    if strong:
        strong_text = strong.get_text(strip=True)
        full_text = li.get_text(" ", strip=True)
        value = full_text.replace(strong_text, "", 1).strip()
        return value
    return li.get_text(strip=True)


def extract_dates_plone(event_div: Tag, ul_details: Tag) -> dict:
    """Extraire les dates depuis hCalendar-hidden et li.event-date-dates."""
    schedules = []

    hcal = event_div.find("ul", class_="hCalendar-hidden")
    dtstart = ""
    dtend = ""
    if hcal:
        start_li = hcal.find("li", class_="dtstart")
        end_li = hcal.find("li", class_="dtend")
        if start_li:
            dtstart = start_li.get_text(strip=True)
        if end_li:
            dtend = end_li.get_text(strip=True)

    date_li = get_detail_li(ul_details, "event-date-dates")
    if date_li:
        date_text = date_li.get_text(" ", strip=True)
        strong = date_li.find("strong")
        if strong:
            date_text = date_text.replace(strong.get_text(strip=True), "", 1).strip()
        date_text = re.sub(r"\(Europe/Brussels\s*/\s*UTC\d*\)", "", date_text).strip()
        date_text = re.sub(r"https?://\S+", "", date_text).strip()
        date_text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}", "", date_text).strip()
        date_text = re.sub(r"\s{2,}", " ", date_text)
        if date_text:
            schedules.append(date_text)

    result = {"schedules": schedules}
    if dtstart:
        result["start"] = dtstart
    if dtend:
        result["end"] = dtend
    return result


def extract_location_plone(ul_details: Tag, default_city: str = "") -> dict:
    """Extraire le lieu depuis le LI 'Localisation'."""
    location = {"venue": "", "address": "", "postal_code": "", "city": default_city}
    loc_li = get_detail_li_by_text(ul_details, "localisation")
    if loc_li:
        a = loc_li.find("a", href=True)
        if a:
            location["venue"] = a.get_text(strip=True)
        else:
            location["venue"] = extract_label_value(loc_li)
    return location


def extract_contact_plone(ul_details: Tag) -> dict:
    """Extraire les infos de contact depuis li.event_contacts."""
    contact = {"phone": "", "website": ""}
    li = get_detail_li(ul_details, "event_contacts")
    if not li:
        return contact

    for a in li.find_all("a", href=True):
        href = a["href"]
        if href.startswith("tel:"):
            contact["phone"] = a.get_text(strip=True)
        elif href.startswith("http"):
            contact["website"] = href

    if not contact["phone"]:
        text = li.get_text(" ", strip=True)
        phone_match = re.search(r"(\+?\d[\d\s\(\)/-]{7,})", text)
        if phone_match:
            contact["phone"] = phone_match.group(1).strip()

    return contact


def extract_organiser_plone(ul_details: Tag) -> str:
    """Extraire l'organisateur depuis le LI contenant 'Organisateur'."""
    li = get_detail_li_by_text(ul_details, "organisateur")
    if not li:
        return ""
    a = li.find("a", href=True)
    if a:
        return a.get_text(strip=True)
    return extract_label_value(li)


def extract_image_plone(event_div: Tag, base_domain: str) -> str:
    """Extraire l'URL de l'image principale (exclure icônes/tuiles/markers)."""
    excluded = ["tile.osm", "marker", "leaflet", "plone.app.event", "++resource++"]
    for img in event_div.find_all("img"):
        src = img.get("src", "")
        if any(ex in src for ex in excluded):
            continue
        if src:
            if src.startswith("/"):
                src = base_domain + src
            return src
    return ""


def extract_description_plone(event_div: Tag) -> str:
    """Extraire la description depuis les <p> directs de div.event."""
    paragraphs = []
    for p in event_div.find_all("p", recursive=False):
        cls = p.get("class", [])
        if "adresse" in cls or "lien" in cls or "image-dummy" in cls:
            continue
        text = p.get_text(strip=True)
        if len(text) > 5:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_audience_plone(ul_details: Tag) -> str:
    """Extraire le public cible depuis li.taxonomy_publiccible."""
    li = get_detail_li(ul_details, "taxonomy_publiccible")
    if li:
        return extract_label_value(li)
    return ""
