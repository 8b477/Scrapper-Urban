"""
Module event_parser: extrait les details complets d'un evenement depuis sa page HTML
"""
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class EventParserException(Exception):
    """Exception personnalisee pour le parser d'evenements"""
    pass


class EventParser:
    """Parser specialise pour extraire les details d'un evenement"""
    
    def __init__(self, html: str, url: str):
        """
        Initialise le parser avec le HTML et l'URL
        
        Args:
            html (str): Contenu HTML de la page
            url (str): URL de la page (pour extraire l'ID)
        """
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, 'lxml')
        self.event_id = self._extract_event_id()
    
    def _extract_event_id(self) -> str:
        """Extrait l'ID de l'événement depuis l'URL ou le HTML"""
        # Essayer d'abord depuis le hidden input
        id_input = self.soup.find('input', {'id': 'num'})
        if id_input:
            return id_input.get('value', '').strip()
        
        # Sinon, extraire depuis l'URL (format: ...-ID.shtml)
        match = re.search(r'-(\d+)\.shtml', self.url)
        if match:
            return match.group(1)
        
        return ""
    
    def extract_title(self) -> str:
        """Extrait le titre de l'événement"""
        try:
            h1 = self.soup.find('h1', class_='referant')
            if h1:
                return h1.get_text(strip=True)
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction titre: {str(e)}")
    
    def extract_description(self) -> str:
        """Extrait la description complète de l'événement"""
        try:
            description_div = self.soup.find('div', class_='description')
            if description_div:
                # Chercher le col-12 avec le texte principal (pas l'image)
                cols = description_div.find_all('div', class_='col-12')
                for col in cols:
                    # Ignorer les colonnes qui sont seulement des images
                    if col.find('img') and not col.find_next(text=True):
                        continue
                    
                    # Prendre le texte du col
                    text = col.get_text(separator='\n', strip=True)
                    if text and len(text) > 50:  # Minimum 50 caractères pour être une vraie description
                        # Nettoyer les espaces multiples
                        text = re.sub(r'\n\s*\n', '\n', text)
                        text = re.sub(r' +', ' ', text)
                        return text.strip()
            
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction description: {str(e)}")
    
    def extract_images(self) -> str:
        """Extrait l'URL de la première image de l'événement"""
        try:
            # 1) Galerie slides (data-background-image)
            image_links = self.soup.find_all('a', class_=['item', 'mfp-gallery'])
            for link in image_links:
                bg_image = link.get('data-background-image')
                if bg_image and '/img/logo' not in bg_image:
                    return bg_image
            
            # 2) Image principale dans la description (<img class="center-block">)
            desc_div = self.soup.find('div', class_='description')
            if desc_div:
                img = desc_div.find('img', class_='center-block')
                if img:
                    src = img.get('src', '')
                    if src and '/img/logo' not in src:
                        return src
            
            # 3) Lien galerie (<a class="mfp-image">)
            mfp_link = self.soup.find('a', class_='mfp-image')
            if mfp_link:
                href = mfp_link.get('href', '')
                if href and '/img/logo' not in href:
                    return href
            
            # 4) Toute <img> avec /imgok/ ou /gal/ dans le src
            for img in self.soup.find_all('img'):
                src = img.get('src', '')
                if src and ('/imgok/' in src or '/gal/' in src):
                    return src
            
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction images: {str(e)}")
    
    def extract_location(self) -> Dict[str, str]:
        """Extrait les informations de localisation"""
        try:
            location = {
                "venue": "",
                "address": "",
                "postal_code": "",
                "city": ""
            }
            
            des_detail = self.soup.find('div', class_='des_detail')
            if not des_detail:
                return location
            
            # Trouver tous les labels et extraire le contenu "Où"
            labels = des_detail.find_all('label')
            for label in labels:
                label_text = label.get_text(strip=True)
                
                # Chercher le label "Où :"
                if "Où" in label_text:
                    # Le contenu est dans le prochain div avec col-lg-8
                    next_div = label.find_next('div', class_='col-lg-8')
                    if next_div:
                        # Extraire tout le texte
                        text_parts = []
                        for item in next_div.children:
                            if isinstance(item, str):
                                text = item.strip()
                                if text:
                                    text_parts.append(text)
                            elif item.name == 'div':
                                # Le div contient address, postal_code, city
                                spans = item.find_all('span')
                                if len(spans) >= 1:
                                    location['address'] = spans[0].get_text(strip=True)
                                if len(spans) >= 2:
                                    location['postal_code'] = spans[1].get_text(strip=True)
                                if len(spans) >= 3:
                                    # City est souvent un lien
                                    link = spans[2].find('a')
                                    if link:
                                        location['city'] = link.get_text(strip=True)
                                    else:
                                        location['city'] = spans[2].get_text(strip=True)
                        
                        # Venue est le texte avant le div interne
                        if text_parts and text_parts[0]:
                            location['venue'] = text_parts[0]
                    break
            
            return location
        except Exception as e:
            raise EventParserException(f"Erreur extraction localisation: {str(e)}")
    
    def extract_phone(self) -> str:
        """Extrait le numéro de téléphone"""
        try:
            des_detail = self.soup.find('div', class_='des_detail')
            if not des_detail:
                return ""
            
            labels = des_detail.find_all('label')
            for label in labels:
                if "Téléphone" in label.get_text():
                    # Trouver le div col-lg-8 suivant
                    next_div = label.find_next('div', class_='col-lg-8')
                    if next_div:
                        # Chercher le lien tel:
                        tel_link = next_div.find('a', href=re.compile(r'^tel:'))
                        if tel_link:
                            href = tel_link.get('href', '')
                            phone = href.replace('tel:', '').strip()
                            return phone
                    break
            
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction telephone: {str(e)}")
    
    def extract_price(self) -> str:
        """Extrait le tarif"""
        try:
            des_detail = self.soup.find('div', class_='des_detail')
            if not des_detail:
                return ""
            
            labels = des_detail.find_all('label')
            for label in labels:
                if "Tarif" in label.get_text():
                    # Trouver le div col-lg-8 suivant
                    next_div = label.find_next('div', class_='col-lg-8')
                    if next_div:
                        return next_div.get_text(strip=True)
                    break
            
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction tarif: {str(e)}")
    
    def extract_audience(self) -> str:
        """Extrait le public visé"""
        try:
            des_detail = self.soup.find('div', class_='des_detail')
            if not des_detail:
                return ""
            
            labels = des_detail.find_all('label')
            for label in labels:
                if "Public" in label.get_text():
                    # Trouver le div col-lg-8 suivant
                    next_div = label.find_next('div', class_='col-lg-8')
                    if next_div:
                        return next_div.get_text(strip=True)
                    break
            
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction audience: {str(e)}")
    
    def extract_category(self) -> str:
        """Extrait la catégorie de l'événement"""
        try:
            des_detail = self.soup.find('div', class_='des_detail')
            if not des_detail:
                return ""
            
            labels = des_detail.find_all('label')
            for label in labels:
                if "Catégorie" in label.get_text():
                    # Trouver le div col-lg-8 suivant
                    next_div = label.find_next('div', class_='col-lg-8')
                    if next_div:
                        link = next_div.find('a')
                        if link:
                            return link.get_text(strip=True)
                        return next_div.get_text(strip=True)
                    break
            
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction categorie: {str(e)}")
    
    def extract_website(self) -> str:
        """Extrait l'URL du site/contact internet"""
        try:
            des_detail = self.soup.find('div', class_='des_detail')
            if not des_detail:
                return ""
            
            labels = des_detail.find_all('label')
            for label in labels:
                if "Internet" in label.get_text():
                    # Trouver le div col-lg-8 suivant
                    next_div = label.find_next('div', class_='col-lg-8')
                    if next_div:
                        link = next_div.find('a')
                        if link:
                            # Prendre le href si c'est un lien /red.php
                            href = link.get('href', '')
                            if href.startswith('/red.php'):
                                # C'est une redirection, ne pas utiliser le texte visible
                                # Retourner vide car on ne peut pas accéder au lien réel
                                return ""
                            else:
                                # C'est un lien direct
                                return href if href.startswith('http') else ""
                    break
            
            return ""
        except Exception as e:
            raise EventParserException(f"Erreur extraction website: {str(e)}")
    
    def _parse_google_calendar_dates(self) -> tuple:
        """Extraire start/end depuis le lien Google Calendar."""
        link = self.soup.find('a', href=re.compile(r'google\.com/calendar'))
        if not link:
            return None, None
        href = link.get('href', '')
        m = re.search(r'dates=(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})\d{2}/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})\d{2}', href)
        if m:
            g = m.groups()
            start = datetime(int(g[0]), int(g[1]), int(g[2]), int(g[3]), int(g[4]))
            end = datetime(int(g[5]), int(g[6]), int(g[7]), int(g[8]), int(g[9]))
            return start, end
        return None, None

    def _parse_text_dates(self) -> tuple:
        """Extraire start/end depuis le texte h2 + horaires (fallback)."""
        des_detail = self.soup.find('div', class_='des_detail')
        if not des_detail:
            return None, None

        # Extraire les horaires depuis les lignes de texte (ex: "Samedi: de 10:00 à 18:00")
        first_start_time = None
        first_end_time = None
        col_lg_12_divs = des_detail.find_all('div', class_='col-lg-12')
        for div in reversed(col_lg_12_divs):
            if '<br' not in str(div):
                continue
            for elem in div.children:
                if isinstance(elem, str):
                    text = elem.strip()
                    if text and 'de' in text and 'à' in text and not first_start_time:
                        times = re.findall(r'(\d{1,2}):(\d{2})', text)
                        if len(times) >= 2:
                            first_start_time = (int(times[0][0]), int(times[0][1]))
                            first_end_time = (int(times[1][0]), int(times[1][1]))
                        elif len(times) == 1:
                            first_start_time = (int(times[0][0]), int(times[0][1]))
            if first_start_time:
                break

        # Extraire la plage de dates depuis le h2
        MONTHS = {'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5,
                  'juin': 6, 'juillet': 7, 'août': 8, 'septembre': 9, 'octobre': 10,
                  'novembre': 11, 'décembre': 12}
        now = datetime.now()

        for h2 in des_detail.find_all('h2'):
            text = h2.get_text(strip=True)
            # "Du 4 au 5 avril" or "Du 4 au 5 avril 2026"
            m = re.match(r'Du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?', text)
            if m:
                day1, day2, month_name, year = int(m.group(1)), int(m.group(2)), m.group(3).lower(), m.group(4)
                month = MONTHS.get(month_name)
                if not month:
                    continue
                yr = int(year) if year else now.year
                h1, m1 = first_start_time or (0, 0)
                h2_, m2_ = first_end_time or (h1, m1)
                return datetime(yr, month, day1, h1, m1), datetime(yr, month, day2, h2_, m2_)

            # "Du 3 avril au 2 mai" or "Du 3 avril au 2 mai 2026"
            m = re.match(r'Du\s+(\d{1,2})\s+(\w+)\s+au\s+(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?', text)
            if m:
                day1, mon1, day2, mon2, year = int(m.group(1)), m.group(2).lower(), int(m.group(3)), m.group(4).lower(), m.group(5)
                m1 = MONTHS.get(mon1)
                m2 = MONTHS.get(mon2)
                if not m1 or not m2:
                    continue
                yr = int(year) if year else now.year
                h1, mi1 = first_start_time or (0, 0)
                h2_, mi2 = first_end_time or (h1, mi1)
                return datetime(yr, m1, day1, h1, mi1), datetime(yr, m2, day2, h2_, mi2)

            # "Le 5 avril" or "Le 29 janvier 2027"
            m = re.match(r'Le\s+(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?', text)
            if m:
                day, month_name, year = int(m.group(1)), m.group(2).lower(), m.group(3)
                month = MONTHS.get(month_name)
                if not month:
                    continue
                yr = int(year) if year else now.year
                h1, m1 = first_start_time or (0, 0)
                h2_, m2_ = first_end_time or (h1, m1)
                return datetime(yr, month, day, h1, m1), datetime(yr, month, day, h2_, m2_)

        return None, None

    def extract_dates(self) -> Dict[str, Any]:
        """Extrait les dates et horaires de l'événement"""
        try:
            # 1) Source fiable : lien Google Calendar
            start_dt, end_dt = self._parse_google_calendar_dates()

            # 2) Fallback : parsing du texte h2 + horaires
            if not start_dt:
                start_dt, end_dt = self._parse_text_dates()

            # 3) Construire le résultat structuré
            dates: Dict[str, Any] = {"schedules": []}

            if start_dt and end_dt and start_dt.date() != end_dt.date():
                sched = f"Du {start_dt.strftime('%d/%m/%Y %H:%M')} au {end_dt.strftime('%d/%m/%Y %H:%M')}"
                dates["schedules"].append(sched)
                dates["start"] = start_dt.strftime('%d-%m-%Y %H:%M')
                dates["end"] = end_dt.strftime('%d-%m-%Y %H:%M')
            elif start_dt:
                end_dt = end_dt or start_dt
                if end_dt != start_dt:
                    sched = f"Le {start_dt.strftime('%d/%m/%Y')} de {start_dt.strftime('%H:%M')} à {end_dt.strftime('%H:%M')}"
                    dates["end"] = end_dt.strftime('%d-%m-%Y %H:%M')
                else:
                    sched = f"Le {start_dt.strftime('%d/%m/%Y %H:%M')}"
                dates["schedules"].append(sched)
                dates["start"] = start_dt.strftime('%d-%m-%Y %H:%M')

            return dates
        except Exception as e:
            raise EventParserException(f"Erreur extraction dates: {str(e)}")
    
    def extract_accessibility(self) -> bool:
        """Vérifie si l'événement est accessible (icône wheelchair)"""
        try:
            des_detail = self.soup.find('div', class_='des_detail')
            if not des_detail:
                return False
            
            wheelchair_icon = des_detail.find('i', class_='icon-wheelchair-alt')
            return wheelchair_icon is not None
        except Exception as e:
            raise EventParserException(f"Erreur extraction accessibilite: {str(e)}")
    
    def parse(self) -> Dict[str, Any]:
        """Parse l'événement complet"""
        try:
            event = {
                "id": self.event_id,
                "url": self.url,
                "title": self.extract_title(),
                "description": self.extract_description(),
                "category": self.extract_category(),
                "location": self.extract_location(),
                "dates": self.extract_dates(),
                "pricing": self.extract_price(),
                "audience": self.extract_audience(),
                "contact": {
                    "phone": self.extract_phone(),
                    "website": self.extract_website()
                },
                "accessibility": self.extract_accessibility(),
                "url_image": self.extract_images(),
                "parsed_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            
            return event
        except Exception as e:
            raise EventParserException(f"Erreur parsing complet: {str(e)}")
