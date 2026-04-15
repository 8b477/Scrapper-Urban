"""
Module storage: sauvegarde les données en JSON
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from config import DATA_DIR, JSON_FILENAME_FORMAT, CITY_DIRS


class StorageException(Exception):
    """Exception personnalisée pour le storage"""
    pass


def save_events(data: Dict[str, Any], city: str) -> str:
    """
    Sauvegarde les données des événements en fichier JSON
    
    Args:
        data (Dict): Dictionnaire contenant métadonnées et événements
        city (str): Nom de la ville
        
    Returns:
        str: Chemin du fichier créé
        
    Raises:
        StorageException: Si la sauvegarde échoue
    """
    try:
        # Créer le répertoire de sortie s'il n'existe pas
        output_dir = Path(CITY_DIRS.get(city.lower(), DATA_DIR))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Générer le nom du fichier
        now = datetime.now()
        filename = JSON_FILENAME_FORMAT.format(
            city=city.lower().replace(" ", "-"),
            day=now.day,
            month=now.month,
            year=now.year % 100
        )
        
        filepath = output_dir / filename
        
        # Sauvegarder en JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"+ Donnees sauvegardees : {filepath}")
        print(f"  - {data['metadata']['total_events']} evenements")
        print(f"  - Date : {data['metadata']['scrape_date']}")
        
        return str(filepath)
    
    except IOError as e:
        raise StorageException(f"Erreur I/O lors de la sauvegarde : {str(e)}")
    except Exception as e:
        raise StorageException(f"Erreur lors de la sauvegarde : {str(e)}")


def load_events(filepath: str) -> Dict[str, Any]:
    """
    Charge les données des événements depuis un fichier JSON
    
    Args:
        filepath (str): Chemin du fichier JSON
        
    Returns:
        Dict: Données des événements
        
    Raises:
        StorageException: Si le chargement échoue
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"+ Donnees chargees : {filepath}")
        print(f"  - {data['metadata']['total_events']} evenements")
        
        return data
    
    except FileNotFoundError:
        raise StorageException(f"Fichier non trouvé : {filepath}")
    except json.JSONDecodeError:
        raise StorageException(f"Fichier JSON invalide : {filepath}")
    except Exception as e:
        raise StorageException(f"Erreur lors du chargement : {str(e)}")


def update_json_metadata(city: str, update_data: Dict[str, Any]) -> str:
    """
    Met à jour le JSON existant avec les nouvelles métadonnées et données
    
    Args:
        city (str): Nom de la ville
        update_data (Dict): Données à ajouter/mettre à jour
                           {
                              'total_events': int,
                              'total_pages': int,
                              'events_per_page': list,
                              'event_urls': list,
                              'pagination_details': dict,
                              'last_execution': dict
                           }
        
    Returns:
        str: Chemin du fichier mis à jour
        
    Raises:
        StorageException: Si la mise à jour échoue
    """
    try:
        # Récupérer le chemin du fichier JSON existant
        output_dir = Path(CITY_DIRS.get(city.lower(), DATA_DIR))
        now = datetime.now()
        filename = JSON_FILENAME_FORMAT.format(
            city=city.lower().replace(" ", "-"),
            day=now.day,
            month=now.month,
            year=now.year % 100
        )
        filepath = output_dir / filename
        
        # Charger le JSON existant ou en créer un nouveau
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "metadata": {},
                "extraction_summary": {},
                "event_urls": [],
                "events": [],
                "notes": {}
            }
        
        # Mettre à jour metadata
        data['metadata'].update({
            "region": city.capitalize(),
            "source": "quefaire.be",
            "scrape_date": datetime.utcnow().isoformat() + "Z",
            "total_events": update_data.get('total_events', 0),
            "total_pages": update_data.get('total_pages', 0),
            "data_completeness": "URLS EXTRACTED - Phase 1: Extraction des URLs complétée. Phase 2: Parsing des événements à venir",
            "extraction_mode": "selenium"
        })
        
        # Ajouter pagination details
        if 'events_per_page' in update_data:
            data['metadata']['pagination'] = {
                "total_pages_requested": update_data.get('total_pages', 0),
                "pages_successfully_retrieved": len(update_data.get('events_per_page', [])),
                "events_per_page": update_data.get('events_per_page', [])
            }
        
        # Ajouter last_execution
        if 'last_execution' in update_data:
            data['metadata']['last_execution'] = update_data['last_execution']
        
        # Mettre à jour extraction_summary
        if 'pagination_details' in update_data:
            data['extraction_summary'] = update_data['pagination_details']
        
        # Mettre à jour event_urls
        if 'event_urls' in update_data:
            data['event_urls'] = update_data['event_urls']
        
        # Sauvegarder le JSON mis à jour
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n+ JSON mis a jour : {filepath}")
        print(f"  - Total events: {update_data.get('total_events', 0)}")
        print(f"  - Total pages: {update_data.get('total_pages', 0)}")
        print(f"  - URLs: {len(update_data.get('event_urls', []))}")
        
        return str(filepath)
    
    except IOError as e:
        raise StorageException(f"Erreur I/O lors de la mise a jour : {str(e)}")
    except Exception as e:
        raise StorageException(f"Erreur lors de la mise a jour : {str(e)}")


def list_saved_files(city: Optional[str] = None) -> list:
    """
    Liste tous les fichiers JSON sauvegardés
    
    Args:
        city (str, optional): Filtrer par ville. Si None, liste tous les fichiers
        
    Returns:
        list: Liste des chemins de fichiers
    """
    try:
        files = []
        
        if city:
            search_dir = Path(CITY_DIRS.get(city.lower(), DATA_DIR))
            if search_dir.exists():
                files = list(search_dir.glob('*.json'))
        else:
            # Chercher dans tous les répertoires
            for city_dir in CITY_DIRS.values():
                if city_dir.exists():
                    files.extend(city_dir.glob('*.json'))
            
            # Aussi dans DATA_DIR
            if DATA_DIR.exists():
                files.extend(DATA_DIR.glob('*.json'))
        
        return sorted(files, reverse=True)
    
    except Exception as e:
        raise StorageException(f"Erreur lors de la lecture des fichiers : {str(e)}")


def get_latest_file(city: str) -> Optional[str]:
    """
    Récupère le dernier fichier sauvegardé pour une ville
    
    Args:
        city (str): Nom de la ville
        
    Returns:
        str: Chemin du dernier fichier ou None
    """
    try:
        files = list_saved_files(city)
        return str(files[0]) if files else None
    except Exception as e:
        print(f"Erreur : {str(e)}")
        return None


if __name__ == "__main__":
    # Test simple
    test_data = {
        'metadata': {
            'total_events': 5,
            'scrape_date': datetime.utcnow().isoformat() + "Z",
            'source': 'quefaire.be',
            'region': 'Charleroi',
            'data_completeness': 'TEST'
        },
        'events': [
            {
                'id': '1',
                'title': 'Événement test',
                'description': 'Description test',
                'category': 'Test',
                'author': 'Test',
                'published_date': '2026-04-01',
                'url': 'https://example.com',
                'location': {},
                'dates': {},
                'pricing': {},
                'audience': {},
                'contact': {},
                'media': {},
                'metadata': {}
            }
        ]
    }
    
    try:
        filepath = save_events(test_data, "charleroi")
        print(f"✓ Test sauvegarde réussi : {filepath}")
        
        loaded = load_events(filepath)
        print(f"✓ Test chargement réussi : {len(loaded['events'])} événement(s)")
    except StorageException as e:
        print(f"Erreur : {e}")
