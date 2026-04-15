"""
Configuration centralisée pour le scraper quefaire.be
"""
import os
from pathlib import Path

# Répertoire racine du projet
PROJECT_ROOT = Path(__file__).parent

# URL de base
BASE_URL = "https://www.quefaire.be"

# Villes disponibles
CITIES = ["charleroi", "la-louvière", "liège", "mons", "namur"]

# Répertoires de sortie
DATA_DIR = PROJECT_ROOT / "data"

# Chemins des répertoires par ville
CITY_DIRS = {
    city: PROJECT_ROOT / city.replace("-", " ").title().replace(" ", "_") 
    for city in CITIES
}

# Configuration Selenium/Requests
REQUEST_TIMEOUT = 10
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.quefaire.be/',
    'DNT': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Cache-Control': 'max-age=0',
}

# Sélecteurs CSS (à vérifier et affiner selon la structure réelle du site)
CSS_SELECTORS = {
    'event_container': 'div.event-item',
    'event_title': 'h2.event-title, h3.event-title',
    'event_description': 'div.event-description, p.description',
    'event_category': 'span.category',
    'event_author': 'span.author',
    'publish_date': 'span.publish-date',
    'event_url': 'a.event-link',
    
    'location_name': 'span.location-name, div.location',
    'location_address': 'span.address',
    'location_postal': 'span.postal-code',
    'location_city': 'span.city',
    'location_phone': 'span.phone',
    'location_website': 'a.website',
    
    'date_start': 'span.date-start',
    'date_end': 'span.date-end',
    'date_schedules': 'div.schedules, table.schedules',
    
    'price_min': 'span.price-min',
    'price_max': 'span.price-max',
    'price_note': 'span.price-note',
    
    'age_min': 'span.age-min',
    'audience': 'span.audience-note',
    'accessibility': 'span.accessibility',
    
    'contact_email': 'span.email, a[href^="mailto"]',
    'contact_phone': 'span.phone',
    'contact_website': 'a.website',
    'contact_social': 'a.social',
    
    'image_url': 'img.event-image',
}

# Configuration de scraping
SCRAPER_CONFIG = {
    'retry_attempts': 5,
    'retry_delay': 3,
    'max_retries_connection': 3,
}

# Statuts possibles des événements
EVENT_STATUSES = ['active', 'inactive', 'archived']

# Format de date pour les fichiers JSON
JSON_FILENAME_FORMAT = "{city}-{day:02d}-{month:02d}-{year:02d}.json"
