"""
extract_urls.py: Script pour extraire les URLs des evenements et les sauvegarder
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ajouter le repertoire src au chemin Python
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fetcher_selenium import fetch_page, fetch_multiple_pages, FetcherException as FetcherE
from url_extractor import (extract_event_urls, extract_event_urls_from_multiple_pages, 
                           save_urls_to_file, get_output_filepath, URLExtractorException)
from storage import update_json_metadata, StorageException
from config import CITIES


class ExtractorException(Exception):
    """Exception personnalisee"""
    pass


def extract_urls_city(city: str, num_pages: int = 5) -> str:
    """
    Extrait les URLs des evenements pour une ville avec pagination
    
    Args:
        city (str): Nom de la ville
        num_pages (int): Nombre de pages a recuperer (par defaut 5, MAX = 5)
        
    Returns:
        str: Chemin du fichier genere
    """
    city_lower = city.lower().strip()
    start_time = time.time()
    
    # Limiter à 5 pages maximum
    MAX_PAGES = 5
    if num_pages > MAX_PAGES:
        num_pages = MAX_PAGES
    
    if city_lower not in CITIES:
        raise ExtractorException(
            f"Ville '{city}' non reconnue. Villes disponibles : {', '.join(CITIES)}"
        )
    
    print(f"\n{'='*60}")
    print(f"Extraction des URLs pour {city.upper()} ({num_pages} pages)")
    print(f"{'='*60}\n")
    
    try:
        # Etape 1: Recuperer le HTML de plusieurs pages
        print("[1/3] Recuperation des pages...")
        pages_html = fetch_multiple_pages(city_lower, num_pages)
        
        # Etape 2: Extraire les URLs
        print("\n[2/3] Extraction des URLs...")
        urls = extract_event_urls_from_multiple_pages(pages_html, city_lower)
        
        # Etape 3: Sauvegarder URLs dans .txt
        output_path = get_output_filepath(city_lower)
        save_urls_to_file(urls, output_path)
        
        # Etape 4: Mettre a jour le JSON avec les nouvelles donnees
        print("\n[3/3] Mise a jour du JSON...")
        duration = int(time.time() - start_time)
        
        # Calculer les evenements par page
        events_per_page = []
        for page_key in sorted(pages_html.keys()):
            # Compter les evenements dans chaque page
            html = pages_html[page_key]
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            count = len(soup.find_all('div', class_='box_event'))
            events_per_page.append(count)
        
        # Preparer les donnees de pagination
        pagination_details = {}
        for idx, page_key in enumerate(sorted(pages_html.keys()), 1):
            pagination_details[f'page_{idx}'] = {
                "url_pattern": "https://www.quefaire.be/" + city_lower,
                "events_found": events_per_page[idx - 1] if idx - 1 < len(events_per_page) else 0,
                "pagination_param": f"?com={idx*49 - 49}" if idx > 1 else "?com=0"
            }
        
        # Appeler la fonction de mise a jour
        from storage import update_json_metadata
        update_json_metadata(city_lower, {
            'total_events': len(urls),
            'total_pages': len(pages_html),
            'events_per_page': events_per_page,
            'event_urls': urls,
            'pagination_details': pagination_details,
            'last_execution': {
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'duration_seconds': duration,
                'status': 'SUCCESS',
                'notes': f'Extraction URLs avec pagination. {len(urls)} URLs uniques recuperees en {duration}s.'
            }
        })
        
        print(f"\n{'='*60}")
        print(f"+ Extraction reussie pour {city.upper()}")
        print(f"+ Pages : {len(pages_html)}")
        print(f"+ URLs : {len(urls)}")
        print(f"+ Fichier .txt : {output_path}")
        print(f"+ Durée : {duration}s")
        print(f"{'='*60}\n")
        
        return output_path
    
    except FetcherE as e:
        raise ExtractorException(f"Erreur fetcher : {str(e)}")
    except URLExtractorException as e:
        raise ExtractorException(f"Erreur extraction : {str(e)}")
    except StorageException as e:
        raise ExtractorException(f"Erreur mise a jour JSON : {str(e)}")
    except Exception as e:
        raise ExtractorException(f"Erreur non prevue : {str(e)}")


def extract_urls_all_cities(num_pages: int = 5) -> dict:
    """
    Extrait les URLs pour toutes les villes avec pagination
    
    Args:
        num_pages (int): Nombre de pages par ville (MAX = 5)
    """
    # Limiter à 5 pages maximum
    MAX_PAGES = 5
    if num_pages > MAX_PAGES:
        num_pages = MAX_PAGES
    
    results = {}
    total = len(CITIES)
    
    print(f"\n{'='*60}")
    print(f"Extraction des URLs pour {total} villes ({num_pages} pages chacune)...")
    print(f"{'='*60}")
    
    for idx, city in enumerate(CITIES, 1):
        print(f"\n[{idx}/{total}] Extraction pour {city.upper()}...")
        
        try:
            filepath = extract_urls_city(city, num_pages)
            results[city] = {'status': 'succes', 'filepath': filepath}
        except ExtractorException as e:
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
    
    num_pages = 5  # Valeur par defaut (MAX = 5)
    city_to_extract = None
    MAX_PAGES = 5
    
    # Parser les arguments
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.isdigit():
            num_pages = int(arg)
            # Limiter à 5 pages maximum
            if num_pages > MAX_PAGES:
                print(f"⚠️  Maximum {MAX_PAGES} pages autorisees. Limitation appliquee.")
                num_pages = MAX_PAGES
        else:
            city_to_extract = arg
    
    if city_to_extract:
        try:
            filepath = extract_urls_city(city_to_extract, num_pages)
            sys.exit(0)
        except ExtractorException as e:
            print(f"Erreur : {e}")
            sys.exit(1)
    else:
        try:
            results = extract_urls_all_cities(num_pages)
            sys.exit(0)
        except Exception as e:
            print(f"Erreur : {e}")
            sys.exit(1)
