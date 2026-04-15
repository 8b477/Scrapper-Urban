"""
extract_event_details.py: Script pour extraire les details complets de chaque evenement
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Ajouter le repertoire src au chemin Python
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fetcher_selenium import fetch_page_with_interactions, FetcherException
from event_parser import EventParser, EventParserException
from storage import update_json_metadata, load_events, StorageException
from config import CITIES, CITY_DIRS
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time as time_module


class EventDetailsException(Exception):
    """Exception personnalisee"""
    pass


def setup_shared_driver():
    """
    Configure un driver Chrome UNIQUE pour tous les événements
    À réutiliser pour toutes les pages (gain de temps énorme)
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        # Supprimer les logs Chrome/GPU/GCM dans la console
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-gpu-sandbox")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        from selenium.webdriver.chrome.service import Service
        service = Service(log_path="NUL")

        driver = webdriver.Chrome(options=chrome_options, service=service)
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(3)
        
        print("+ Driver Chrome initialise (partage global)")
        return driver
    except Exception as e:
        raise EventDetailsException(f"Erreur creation driver: {str(e)}")


def read_urls_from_file(city: str) -> list:
    """
    Lit les URLs depuis le fichier .txt
    
    Args:
        city (str): Nom de la ville
        
    Returns:
        list: Liste des URLs
    """
    try:
        city_dir = Path(CITY_DIRS.get(city.lower(), 'data'))
        now = datetime.now()
        
        # Chercher le fichier d'URLs le plus recent
        url_files = list(city_dir.glob(f'{city.lower()}-urls-*.txt'))
        if not url_files:
            raise EventDetailsException(f"Aucun fichier d'URLs trouve pour {city}")
        
        # Prendre le plus recent
        url_file = sorted(url_files, reverse=True)[0]
        
        print(f"Lecture des URLs depuis : {url_file}")
        
        with open(url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        print(f"+ {len(urls)} URLs a traiter")
        return urls
    
    except Exception as e:
        raise EventDetailsException(f"Erreur lecture URLs: {str(e)}")


def fetch_event_page(url: str, driver=None, accept_cookies_first_time=True) -> str:
    """
    Recupere le HTML d'une page d'evenement
    
    Args:
        url (str): URL de l'evenement
        driver: Driver Selenium existant (None = créer un nouveau, déprécié)
        accept_cookies_first_time (bool): Accepter les cookies sur la première page
        
    Returns:
        str: Contenu HTML
    """
    try:
        if driver is None:
            raise EventDetailsException("Driver Selenium requis (optimisation)")
        
        # Naviguer vers l'URL
        driver.get(url)
        
        # Attendre le contenu principal (pas un sleep fixe)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "description"))
            )
        except:
            # Timeout acceptable - la page peut charger partiellement
            time_module.sleep(1)
        
        # Accepter les cookies seulement si nécessaire (première page)
        if accept_cookies_first_time:
            try:
                # Bouton cookies (classe spécifique à quefaire.be)
                cookie_button = driver.find_element(By.CLASS_NAME, "sd-cmp-7Ga7b")
                cookie_button.click()
                time_module.sleep(0.5)
            except:
                # Aucun bouton cookies trouvé ou déjà accepté - c'est ok
                pass
        
        html = driver.page_source
        return html
    
    except Exception as e:
        raise EventDetailsException(f"Erreur recuperation page {url[:50]}: {str(e)}")


def extract_events_from_urls(city: str, max_events: int = None) -> dict:
    """
    Extrait les details de tous les evenements a partir des URLs
    
    Args:
        city (str): Nom de la ville
        max_events (int): Nombre maximum d'evenements a traiter (None = tous)
        
    Returns:
        dict: Dictionnaire avec les evenements extraits
    """
    city_lower = city.lower().strip()
    start_time = time.time()
    
    if city_lower not in CITIES:
        raise EventDetailsException(f"Ville '{city}' non reconnue")
    
    print(f"\n{'='*60}")
    print(f"Extraction des details des evenements pour {city.upper()}")
    print(f"{'='*60}\n")
    
    # Créer UN SEUL driver pour tous les événements
    driver = None
    
    try:
        # Lire les URLs
        urls = read_urls_from_file(city_lower)
        
        if max_events:
            urls = urls[:max_events]
        
        # Charger le JSON existant
        city_dir = Path(CITY_DIRS.get(city_lower, 'data'))
        now = datetime.now()
        json_files = list(city_dir.glob(f'{city_lower}-*.json'))
        if not json_files:
            raise EventDetailsException(f"Aucun fichier JSON trouve pour {city}")
        
        json_file = sorted(json_files, reverse=True)[0]
        existing_data = load_events(str(json_file))
        
        # Initialiser le driver UNE FOIS
        driver = setup_shared_driver()
        
        # Traiter chaque URL
        events = []
        processed = 0
        failed = 0
        cookies_accepted = False
        
        for idx, url in enumerate(urls, 1):
            try:
                print(f"[{idx}/{len(urls)}] Traitement : {url.split('/')[-1][:50]}...")
                
                # Recuperer le HTML (avec driver partagé)
                html = fetch_event_page(url, driver=driver, accept_cookies_first_time=not cookies_accepted)
                cookies_accepted = True  # Cookies acceptés après la première page
                
                # Parser l'evenement
                parser = EventParser(html, url)
                event = parser.parse()
                events.append(event)
                processed += 1
                
                print(f"    + Titre: {event['title'][:50]}...")
                
                # Délai court pour ne pas surcharger le serveur
                time_module.sleep(0.2)
                
            except Exception as e:
                failed += 1
                print(f"    x Erreur: {str(e)[:80]}...")
                continue
        
        # Fermer le driver APRÈS tous les événements
        if driver:
            try:
                driver.quit()
                print("\n+ Driver Chrome fermé")
            except:
                pass
        
        # Mettre a jour le JSON avec les evenements
        duration = int(time.time() - start_time)
        
        print(f"\n{'='*60}")
        print(f"Resultats:")
        print(f"  + {processed} evenements extraits")
        print(f"  x {failed} echecs")
        print(f"  + Duree: {duration}s ({duration//60}m {duration%60}s)")
        print(f"{'='*60}\n")
        
        return {
            'events': events,
            'processed': processed,
            'failed': failed,
            'duration': duration,
            'json_file': str(json_file)
        }
    
    except Exception as e:
        # S'assurer que le driver est fermé en cas d'erreur
        if driver:
            try:
                driver.quit()
            except:
                pass
        raise EventDetailsException(f"Erreur extraction evenements: {str(e)}")


def save_events_to_json(city: str, events_data: dict) -> str:
    """
    Sauvegarde les evenements dans le JSON existant
    
    Args:
        city (str): Nom de la ville
        events_data (dict): Donnees des evenements extraits
        
    Returns:
        str: Chemin du fichier JSON
    """
    try:
        json_file = events_data['json_file']
        
        # Charger le JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            import json
            import re as _re
            data = json.load(f)
        
        # Ajouter les evenements
        data['events'] = events_data['events']
        data['metadata']['events_extracted'] = len(events_data['events'])
        data['metadata']['extraction_date'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Nettoyer les descriptions (supprimer \n, normaliser espaces)
        for event in data.get('events', []):
            desc = event.get('description', '')
            if desc:
                desc = desc.replace('\n', ' ')
                desc = _re.sub(r'\s+', ' ', desc).strip()
                event['description'] = desc
        
        # Sauvegarder
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"+ JSON mis a jour: {json_file}")
        print(f"  - {len(events_data['events'])} evenements")
        
        return json_file
    
    except Exception as e:
        raise EventDetailsException(f"Erreur sauvegarde JSON: {str(e)}")


def extract_details_all_cities(max_events: int = None) -> dict:
    """
    Extrait les détails pour toutes les villes configurées.
    
    Args:
        max_events (int): Nombre max d'événements par ville (None = tous)
    
    Returns:
        dict: Résultats par ville
    """
    results = {}
    total = len(CITIES)

    print(f"\n{'='*60}")
    print(f"Extraction des détails pour {total} villes...")
    print(f"{'='*60}")

    for idx, city in enumerate(CITIES, 1):
        print(f"\n[{idx}/{total}] Extraction pour {city.upper()}...")

        try:
            events_data = extract_events_from_urls(city, max_events)
            save_events_to_json(city, events_data)
            results[city] = {'status': 'succes', 'processed': events_data['processed'], 'failed': events_data['failed']}
        except EventDetailsException as e:
            print(f"x Erreur : {str(e)}")
            results[city] = {'status': 'erreur', 'message': str(e)}

    # Resume
    print(f"\n{'='*60}")
    print(f"RESUME")
    print(f"{'='*60}")

    success_count = sum(1 for r in results.values() if r['status'] == 'succes')
    error_count = sum(1 for r in results.values() if r['status'] == 'erreur')

    for city, result in results.items():
        status_icon = "+" if result['status'] == 'succes' else "x"
        print(f"{status_icon} {city}: {result['status']}")

    print(f"\nTotal : {success_count} succes, {error_count} erreurs")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    
    city_to_process = None
    max_events_to_process = None
    
    # Parser les arguments
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.isdigit():
            max_events_to_process = int(arg)
        else:
            city_to_process = arg
    
    if city_to_process:
        try:
            events_data = extract_events_from_urls(city_to_process, max_events_to_process)
            save_events_to_json(city_to_process, events_data)
            sys.exit(0)
        except EventDetailsException as e:
            print(f"Erreur: {e}")
            sys.exit(1)
    else:
        try:
            results = extract_details_all_cities(max_events_to_process)
            sys.exit(0)
        except Exception as e:
            print(f"Erreur: {e}")
            sys.exit(1)
