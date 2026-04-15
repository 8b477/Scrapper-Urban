"""
Classe de base pour la Phase 2 (extraction des détails d'événements).
Factorise la boucle main() dupliquée dans les 5 scraper_event_details.py.
"""
import json
import os
import time
from datetime import datetime, timezone
from abc import ABC, abstractmethod

from .utils import cleanup_json_data
from .http_client import create_session
from .logger import get_logger


class BaseScraper(ABC):
    """
    Classe de base pour les scrapers de détails d'événements.
    
    Chaque ville hérite de cette classe et implémente uniquement
    scrape_event() avec sa logique spécifique de parsing HTML/API.
    
    La boucle d'exécution, la gestion du JSON Phase 1, la sauvegarde,
    la mise à jour des métadonnées et les délais sont partagés.
    """

    # À surcharger dans chaque sous-classe
    city_name: str = ""           # Ex: "Charleroi"
    json_prefix: str = ""         # Ex: "charleroi"
    request_delay: float = 0.5    # Délai entre les requêtes (secondes)

    def __init__(self):
        self.logger = get_logger(self.city_name or self.__class__.__name__)
        self.session = create_session()

    @abstractmethod
    def scrape_event(self, url: str, **kwargs):
        """
        À implémenter dans chaque ville.
        Reçoit l'URL (ou les infos nécessaires) et retourne un dict événement ou None.
        """
        ...

    def find_phase1_json(self, script_dir: str) -> str:
        """Trouve le fichier JSON Phase 1 le plus récent."""
        json_files = [
            f for f in os.listdir(script_dir)
            if f.startswith(f"{self.json_prefix}_") and f.endswith(".json")
        ]
        if not json_files:
            return None
        return os.path.join(script_dir, sorted(json_files)[-1])

    def log_event_result(self, index: int, total: int, event: dict):
        """Log le résultat d'un scrape d'événement."""
        if event:
            title = event.get('title', '')[:50]
            sched = event.get('dates', {}).get('schedules', [])
            sched_str = sched[0][:50] if sched else "pas de date"
            self.logger.info("[%d/%d] %s | %s", index, total, title, sched_str)
        else:
            self.logger.warning("[%d/%d] ECHEC", index, total)

    def update_metadata(self, data: dict, success: int, errors: int, total_urls: int, duration: float, extra_notes: str = ""):
        """Met à jour les métadonnées du JSON avec les résultats Phase 2."""
        end_time = datetime.now(timezone.utc)
        data["metadata"]["events_extracted"] = success
        data["metadata"]["extraction_date"] = end_time.isoformat()
        data["metadata"]["data_completeness"] = (
            f"Phase 1: {total_urls} URLs extraites. "
            f"Phase 2: {success}/{total_urls} événements parsés ({errors} erreurs)."
        )
        data["metadata"]["last_execution"] = {
            "timestamp": end_time.isoformat(),
            "duration_seconds": round(duration, 1),
            "status": "SUCCESS" if errors == 0 else "PARTIAL",
            "notes": extra_notes or f"Phase 2 terminée. {success} événements parsés en {round(duration)}s.",
        }

    def save_json(self, data: dict, json_path: str):
        """Nettoie et sauvegarde le JSON final."""
        data = cleanup_json_data(data)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info("JSON mis à jour : %s", json_path)

    def run(self):
        """
        Boucle d'exécution principale Phase 2.
        
        Charge le JSON Phase 1, scrape chaque URL, met à jour les métadonnées
        et sauvegarde le résultat.
        """
        script_dir = os.path.dirname(os.path.abspath(self._get_caller_file()))
        json_path = self.find_phase1_json(script_dir)

        if not json_path:
            self.logger.error("Aucun fichier %s_*.json trouvé. Lancez d'abord scraper_agenda.py.", self.json_prefix)
            return

        self.logger.info("Lecture du JSON Phase 1 : %s", os.path.basename(json_path))

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        urls = data.get("event_urls", [])
        self.logger.info("%d URL(s) à scraper", len(urls))

        start_time = datetime.now(timezone.utc)
        events = []
        success = 0
        errors = 0

        for i, url in enumerate(urls, 1):
            event = self.scrape_event(url)
            self.log_event_result(i, len(urls), event)

            if event:
                events.append(event)
                success += 1
            else:
                errors += 1

            if i < len(urls):
                time.sleep(self.request_delay)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        data["events"] = events
        self.update_metadata(data, success, errors, len(urls), duration)
        self.save_json(data, json_path)

        self.logger.info("Total: %d événement(s) scrapé(s), %d erreur(s)", success, errors)

    def _get_caller_file(self) -> str:
        """Retourne le fichier de la sous-classe (pour trouver le script_dir)."""
        import inspect
        # Remonter la stack pour trouver le fichier de la sous-classe
        for frame_info in inspect.stack():
            if frame_info.filename != __file__ and 'scraper_event_details' in frame_info.filename:
                return frame_info.filename
        # Fallback: utiliser le module de la sous-classe
        return inspect.getfile(self.__class__)
