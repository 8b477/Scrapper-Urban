"""
Module commun pour les scrapers "site de la ville".
Contient les fonctions partagées entre toutes les villes.
"""
from .utils import (
    generate_id,
    cleanup_json_data,
    format_iso_to_readable,
    html_to_text,
    clean_description,
    format_iso_to_short,
)
from .http_client import create_session, fetch_page, fetch_json
from .logger import get_logger
from .base_scraper import BaseScraper

__all__ = [
    "generate_id",
    "cleanup_json_data",
    "format_iso_to_readable",
    "html_to_text",
    "clean_description",
    "format_iso_to_short",
    "create_session",
    "fetch_page",
    "fetch_json",
    "get_logger",
    "BaseScraper",
]
