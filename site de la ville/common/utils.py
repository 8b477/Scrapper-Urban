"""
Fonctions utilitaires partagées entre tous les scrapers de villes.
Élimine la duplication de cleanup_json_data, generate_id, etc.
"""
import hashlib
import re
from datetime import datetime
from bs4 import BeautifulSoup


def generate_id(text: str) -> str:
    """Générer un ID unique basé sur un texte (URL, clé composite, etc.)."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def clean_description(text: str) -> str:
    """Nettoyer une description : retirer \\n, normaliser les espaces."""
    if not text:
        return text
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def format_iso_to_short(iso_str: str) -> str:
    """Convertir une date ISO en format court DD-MM-YYYY HH:MM."""
    if not iso_str:
        return iso_str
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%d-%m-%Y %H:%M')
    except (ValueError, TypeError):
        return iso_str


def format_iso_to_readable(iso_str: str) -> str:
    """Convertir une date ISO en texte lisible DD/MM/YYYY HH:MM."""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.hour == 0 and dt.minute == 0:
            return dt.strftime("%d/%m/%Y")
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return iso_str


def cleanup_json_data(data: dict) -> dict:
    """Nettoyer les données JSON: descriptions et dates ISO -> DD-MM-YYYY HH:MM."""
    if 'events' not in data:
        return data

    for event in data['events']:
        if 'description' in event and event['description']:
            event['description'] = clean_description(event['description'])

        if 'dates' in event:
            dates = event['dates']
            if 'start' in dates and dates['start']:
                dates['start'] = format_iso_to_short(dates['start'])
            if 'end' in dates and dates['end']:
                dates['end'] = format_iso_to_short(dates['end'])

    return data


def html_to_text(html_content: str) -> str:
    """Convertir du HTML en texte propre."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for p in soup.find_all("p"):
        p.insert_after("\n")
    text = soup.get_text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
