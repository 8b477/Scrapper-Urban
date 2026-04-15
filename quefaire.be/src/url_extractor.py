"""
Module url_extractor: extrait les URLs des evenements
"""
from bs4 import BeautifulSoup
from typing import List
from config import BASE_URL


class URLExtractorException(Exception):
    """Exception personnalisee pour l'URL extractor"""
    pass


def extract_event_urls(html: str, city: str) -> List[str]:
    """
    Extrait toutes les URLs des evenements de la page
    
    Args:
        html (str): Contenu HTML de la page
        city (str): Nom de la ville (pour infos)
        
    Returns:
        List[str]: Liste des URLs completes des evenements
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Trouver tous les conteneurs d'evenements
        event_containers = soup.find_all('div', class_='box_event')
        print(f"Nombre de conteneurs trouves : {len(event_containers)}")
        
        urls = []
        
        for container in event_containers:
            # Chercher la balise <a> dans le conteneur
            link = container.find('a', class_='listing-item-container')
            
            if link and link.get('href'):
                href = link.get('href')
                
                # Construire l'URL complete si c'est un chemin relatif
                if href.startswith('/'):
                    full_url = BASE_URL + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = BASE_URL + '/' + href
                
                urls.append(full_url)
        
        print(f"+ {len(urls)} URLs d'evenements extraites")
        return urls
    
    except Exception as e:
        raise URLExtractorException(f"Erreur lors de l'extraction des URLs : {str(e)}")


def extract_event_urls_from_multiple_pages(pages_html: dict, city: str) -> List[str]:
    """
    Extrait toutes les URLs des evenements de plusieurs pages
    
    Args:
        pages_html (dict): Dictionnaire avec cles 'page_X' contenant le HTML
        city (str): Nom de la ville (pour infos)
        
    Returns:
        List[str]: Liste complete des URLs (sans doublons) de tous les evenements
    """
    try:
        all_urls = []
        see_urls = set()  # Pour eviter les doublons
        
        for page_key in sorted(pages_html.keys()):
            html = pages_html[page_key]
            soup = BeautifulSoup(html, 'lxml')
            
            # Trouver tous les conteneurs d'evenements
            event_containers = soup.find_all('div', class_='box_event')
            page_num = page_key.split('_')[1]
            print(f"\nPage {page_num} : {len(event_containers)} conteneurs")
            
            for container in event_containers:
                # Chercher la balise <a> dans le conteneur
                link = container.find('a', class_='listing-item-container')
                
                if link and link.get('href'):
                    href = link.get('href')
                    
                    # Construire l'URL complete si c'est un chemin relatif
                    if href.startswith('/'):
                        full_url = BASE_URL + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = BASE_URL + '/' + href
                    
                    # Eviter les doublons
                    if full_url not in see_urls:
                        all_urls.append(full_url)
                        see_urls.add(full_url)
        
        print(f"\n+ Total : {len(all_urls)} URLs d'evenements extraites (doublons supprimes)")
        return all_urls
    
    except Exception as e:
        raise URLExtractorException(f"Erreur lors de l'extraction multi-pages : {str(e)}")



def save_urls_to_file(urls: List[str], filepath: str) -> None:
    """
    Sauvegarde les URLs dans un fichier .txt (une par ligne)
    
    Args:
        urls (List[str]): Liste des URLs
        filepath (str): Chemin du fichier de sortie
        
    Raises:
        URLExtractorException: Si la sauvegarde echoue
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + '\n')
        
        print(f"+ {len(urls)} URLs sauvegardees dans {filepath}")
    
    except IOError as e:
        raise URLExtractorException(f"Erreur I/O lors de la sauvegarde : {str(e)}")
    except Exception as e:
        raise URLExtractorException(f"Erreur lors de la sauvegarde : {str(e)}")


def get_output_filepath(city: str) -> str:
    """
    Genere le chemin du fichier de sortie pour les URLs
    
    Args:
        city (str): Nom de la ville
        
    Returns:
        str: Chemin du fichier .txt
    """
    from datetime import datetime
    from config import CITY_DIRS
    from pathlib import Path
    
    output_dir = Path(CITY_DIRS.get(city.lower(), 'data'))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    filename = f"{city.lower()}-urls-{now.day:02d}-{now.month:02d}-{now.year % 100:02d}.txt"
    
    return str(output_dir / filename)


if __name__ == "__main__":
    # Test simple
    from src.fetcher_selenium import fetch_page
    
    try:
        html = fetch_page("charleroi")
        urls = extract_event_urls(html, "charleroi")
        
        filepath = get_output_filepath("charleroi")
        save_urls_to_file(urls, filepath)
        
        print(f"✓ Test reussi : {len(urls)} URLs extraites et sauvegardees")
    except Exception as e:
        print(f"Erreur : {e}")
