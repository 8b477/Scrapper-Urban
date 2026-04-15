"""
Module fetcher_selenium: recupere le contenu HTML avec Selenium (avec interactions)
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from config import BASE_URL, REQUEST_TIMEOUT, SCRAPER_CONFIG


class FetcherException(Exception):
    """Exception personnalisee pour le fetcher"""
    pass


def setup_chrome_driver():
    """Configure et crée un driver Chrome headless"""
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
    # Supprimer les logs Chrome/GPU/GCM dans la console
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-gpu-sandbox")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.page_load_strategy = "eager"  # DOMContentLoaded suffit, pas besoin d'attendre toutes les ressources
    
    from selenium.webdriver.chrome.service import Service
    service = Service(log_path="NUL")

    try:
        driver = webdriver.Chrome(options=chrome_options, service=service)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        raise FetcherException(f"Erreur lors de la creation du driver Chrome: {str(e)}")


def fetch_page_with_interactions(city: str) -> str:
    """
    Recupere le contenu HTML avec interactions (cookies, modal)
    
    Args:
        city (str): Nom de la ville
        
    Returns:
        str: Contenu HTML de la page
        
    Raises:
        FetcherException: Si la page ne peut pas etre recup
    """
    url = f"{BASE_URL}/{city}"
    driver = None
    
    try:
        print(f"Lancement du navigateur...")
        driver = setup_chrome_driver()
        
        print(f"Recuperation de {url}...")
        driver.get(url)
        
        # Attendre le chargement de la page
        time.sleep(2)
        
        # Etape 1: Accepter les cookies
        try:
            print("Acceptation des cookies...")
            cookie_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sd-cmp-7Ga7b"))
            )
            if cookie_button:
                cookie_button.click()
                print("Cookies acceptes")
                time.sleep(1)
        except Exception as e:
            print(f"Note: Impossible d'accepter les cookies (non bloquant): {str(e)[:50]}")
        
        # Etape 2: Fermer la modal
        try:
            print("Fermeture de la modal...")
            close_button = driver.find_element(By.CSS_SELECTOR, "a.close[data-dismiss='modal']")
            if close_button:
                close_button.click()
                print("Modal fermee")
                time.sleep(1)
        except Exception as e:
            print(f"Note: Pas de modal a fermer (non bloquant): {str(e)[:50]}")
        
        # Recuperer le HTML
        html = driver.page_source
        print(f"+ Page recuperee avec succes ({len(html)} caracteres)")
        
        return html
        
    except Exception as e:
        raise FetcherException(f"Erreur lors de la recuperation: {str(e)}")
    finally:
        if driver:
            driver.quit()
            print("Navigateur ferme")


def fetch_page(city: str) -> str:
    """Wrapper pour maintenir la compatibilite"""
    return fetch_page_with_interactions(city)


def fetch_multiple_pages(city: str, num_pages: int = 5) -> dict:
    """
    Recupere le contenu HTML de plusieurs pages avec pagination
    
    Args:
        city (str): Nom de la ville
        num_pages (int): Nombre de pages a recuperer (par defaut 5)
        
    Returns:
        dict: Dictionnaire avec cles 'page_X' contenant le HTML de chaque page
        
    Raises:
        FetcherException: Si la recuperation echoue
    """
    url = f"{BASE_URL}/{city}"
    driver = None
    pages_html = {}
    
    try:
        print(f"Lancement du navigateur...")
        driver = setup_chrome_driver()
        
        print(f"Recuperation de {url}...")
        driver.get(url)
        
        # Attendre le chargement de la page
        time.sleep(2)
        
        # Etape 1: Accepter les cookies
        try:
            print("Acceptation des cookies...")
            cookie_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sd-cmp-7Ga7b"))
            )
            if cookie_button:
                cookie_button.click()
                print("Cookies acceptes")
                time.sleep(1)
        except Exception as e:
            print(f"Note: Impossible d'accepter les cookies (non bloquant): {str(e)[:50]}")
        
        # Etape 2: Fermer la modal
        try:
            print("Fermeture de la modal...")
            close_button = driver.find_element(By.CSS_SELECTOR, "a.close[data-dismiss='modal']")
            if close_button:
                close_button.click()
                print("Modal fermee")
                time.sleep(1)
        except Exception as e:
            print(f"Note: Pas de modal a fermer (non bloquant): {str(e)[:50]}")
        
        # Boucle pour parcourir les pages
        consecutive_errors = 0
        
        for page_num in range(num_pages):
            print(f"\n--- Page {page_num + 1}/{num_pages} ---")
            
            # Recuperer le HTML de la page actuelle
            html = driver.page_source
            pages_html[f'page_{page_num + 1}'] = html
            print(f"+ Page {page_num + 1} : {len(html)} caracteres")
            
            # Si ce n'est pas la derniere page, chercher le bouton "suivant"
            if page_num < num_pages - 1:
                try:
                    print("Scroll en bas de la page...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    # Chercher le lien avec icone angle-right (suivant)
                    print("Recherche du lien 'Suivant'...")
                    # XPath ameliore: chercher le lien avec icone angle-right
                    next_button = WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.XPATH, "//a[.//i[@class='icon-angle-right']]"))
                    )
                    
                    # Verifier que c'est bien un lien de pagination (contient ?com=)
                    href = next_button.get_attribute('href')
                    if href and '?com=' in href:
                        print(f"+ Lien trouve: {href}")
                        print("Clic sur le bouton 'Suivant'...")
                        
                        # Navigation directe par URL (évite les blocages du JS click)
                        try:
                            driver.get(href)
                        except TimeoutException:
                            print(f"Timeout chargement {href}, arret forcé")
                            driver.execute_script("window.stop();")
                        
                        time.sleep(2)
                        print(f"Chargement de la page {page_num + 2}...")
                        consecutive_errors = 0
                    else:
                        print(f"No valid pagination link found (href: {href})")
                        break
                
                except Exception as e:
                    consecutive_errors += 1
                    error_msg = str(e)[:70]
                    print(f"x Erreur navigation : {error_msg}")
                    
                    if consecutive_errors >= 2:
                        print(f"=> Fin de pagination apres {consecutive_errors} erreurs consecutives")
                        break
                    else:
                        print(f"=> Tentative {consecutive_errors}/2, continuation...")
                        time.sleep(2)
        
        return pages_html
        
    except Exception as e:
        raise FetcherException(f"Erreur lors de la recuperation multi-pages: {str(e)}")
    finally:
        if driver:
            driver.quit()
            print("Navigateur ferme")


if __name__ == "__main__":
    try:
        html = fetch_page("charleroi")
        print(f"✓ Recuperation reussie")
    except FetcherException as e:
        print(f"Erreur : {e}")
