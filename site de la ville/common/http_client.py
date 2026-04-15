"""
Client HTTP avec requests.Session(), retry automatique et backoff exponentiel.
Remplace les appels requests.get() individuels pour réutiliser les connexions TCP.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logger import get_logger

logger = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DEFAULT_TIMEOUT = 30


def create_session(
    headers: dict = None,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
) -> requests.Session:
    """
    Crée une Session HTTP avec retry automatique et réutilisation de connexion.
    
    - Réutilisation TCP (keep-alive) → ~10-20x plus rapide que requests.get() individuel
    - Retry automatique avec backoff exponentiel sur erreurs transitoires
    - Headers par défaut configurables
    """
    session = requests.Session()
    session.headers.update(headers or DEFAULT_HEADERS)

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def fetch_page(session: requests.Session, url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    """
    Récupère une page HTML avec gestion d'erreurs.
    
    Returns:
        Response object ou None si erreur irrécupérable.
    
    Raises:
        requests.RequestException: sur erreur réseau après tous les retries.
    """
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def fetch_json(session: requests.Session, url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Récupère du JSON depuis une API avec gestion d'erreurs.
    
    Returns:
        dict parsé depuis la réponse JSON.
    
    Raises:
        requests.RequestException: sur erreur réseau.
        ValueError: si la réponse n'est pas du JSON valide.
    """
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()
