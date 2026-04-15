"""
Configuration de logging structuré pour les scrapers.
Remplace les print() par un logger configurable avec niveaux et timestamps.
"""
import logging
import sys


_configured = False


def _configure_root():
    """Configure le root logger une seule fois."""
    global _configured
    if _configured:
        return
    _configured = True

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)

    root = logging.getLogger("scraper")
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour un module donné.
    
    Usage:
        from common.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Scraping %s", url)
        logger.warning("404 pour %s", url)
        logger.error("Échec: %s", e)
    """
    _configure_root()
    return logging.getLogger(f"scraper.{name}")
