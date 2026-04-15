# Scrapper Urban — Événements en Wallonie

Outil de collecte et de fusion d'événements culturels pour 5 villes belges :
**Charleroi, La Louvière, Liège, Mons, Namur**

Il y a deux sources de données :
- **quefaire.be** — scraper Selenium avec dashboard Flask
- **site de la ville** — scraper requests/BeautifulSoup avec dashboard Flask

Un troisième script (`merge_events.py`) fusionne et déduplique les données des deux sources.

---

## Prérequis

- Python **3.10 ou supérieur**
- Google Chrome installé (pour le scraper quefaire.be qui utilise Selenium)
- ChromeDriver compatible avec ta version de Chrome
  → Téléchargement : https://chromedriver.chromium.org/downloads

Pour vérifier ta version de Chrome : ouvre Chrome > `...` > Aide > À propos de Google Chrome.

---

## Installation

### 1. Cloner ou télécharger le projet

```bash
git clone <url-du-repo>
cd Scrapper-Urban
```

### 2. Créer un environnement virtuel (recommandé)

```bash
python -m venv venv
```

Activer l'environnement :

```bash
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r quefaire.be/requirements.txt
```

Les bibliothèques installées :

| Bibliothèque | Utilisation |
|---|---|
| `requests` | Requêtes HTTP pour le scraper ville |
| `beautifulsoup4` | Parsing HTML |
| `lxml` | Parser HTML rapide |
| `cloudscraper` | Contournement anti-bot |
| `selenium` | Automatisation navigateur (quefaire.be) |
| `flask` | Serveurs de dashboard |

---

## Structure du projet

```
Scrapper-Urban/
│
├── quefaire.be/              # Scraper pour quefaire.be
│   ├── server.py             # Dashboard Flask (port 5000)
│   ├── extract_urls.py       # Extraction des URLs d'événements
│   ├── extract_event_details.py  # Extraction des détails
│   ├── config.py             # Configuration (villes, chemins)
│   ├── requirements.txt      # Dépendances Python
│   └── <Ville>/              # Un dossier par ville avec les JSON
│
├── site de la ville/         # Scraper pour les sites officiels des villes
│   ├── server.py             # Dashboard Flask (port 5001)
│   ├── common/               # Code partagé entre les villes
│   └── <Ville>/              # Un dossier par ville avec scraper + JSON
│
├── combined/                 # Fichiers JSON fusionnés (générés par merge_events.py)
│   └── <Ville>/
│
├── merge_events.py           # Script de fusion et déduplication
├── run_all.py                # Lance les deux dashboards en même temps
└── README.md
```

---

## Utilisation

### Option A — Lancer les deux dashboards (façon simple)

```bash
python run_all.py
```

Cela démarre automatiquement :
- `http://localhost:5000` → dashboard quefaire.be
- `http://localhost:5001` → dashboard site de la ville

Appuie sur `CTRL+C` pour tout arrêter.

---

### Option B — Lancer un seul dashboard

**quefaire.be :**
```bash
cd quefaire.be
python server.py
```

**Site de la ville :**
```bash
cd "site de la ville"
python server.py
```

---

### Option C — Lancer les scrapers manuellement (sans dashboard)

**Extraire les URLs depuis quefaire.be :**
```bash
# Toutes les villes
python quefaire.be/extract_urls.py

# Une ville spécifique
python quefaire.be/extract_urls.py charleroi

# Avec un nombre de pages précis (max 5)
python quefaire.be/extract_urls.py charleroi 3
```

**Extraire les détails des événements :**
```bash
# Toutes les villes
python quefaire.be/extract_event_details.py

# Une ville spécifique
python quefaire.be/extract_event_details.py charleroi
```

---

### Fusionner les deux sources

Le script `merge_events.py` combine les fichiers quefaire.be + site de la ville pour chaque ville/date et supprime les doublons.

```bash
# Toutes les villes, toutes les dates disponibles
python merge_events.py

# Une ville spécifique
python merge_events.py --city charleroi

# Une ville + une date précise
python merge_events.py --city charleroi --date 08-04-26
```

Les fichiers fusionnés sont sauvegardés dans `combined/<Ville>/`.

Exemple de nom de fichier généré : `charleroi_combined_08-04-26.json`

---

## Format des fichiers JSON

Chaque fichier JSON contient :

```json
{
  "metadata": {
    "region": "Charleroi",
    "sources": ["quefaire.be", "charleroi.be"],
    "total_events": 155,
    "duplicates_removed": 3
  },
  "events": [
    {
      "id": "...",
      "title": "Nom de l'événement",
      "description": "...",
      "category": "Culture",
      "location": {
        "venue": "Nom du lieu",
        "address": "Rue ...",
        "postal_code": "6000",
        "city": "Charleroi"
      },
      "dates": {
        "start": "10-04-2026 18:00",
        "end": "11-04-2026 20:00"
      },
      "pricing": "Entrée gratuite",
      "url": "https://...",
      "url_image": "https://..."
    }
  ]
}
```

---

## Villes supportées

| Ville | quefaire.be | Site officiel |
|---|---|---|
| Charleroi | `charleroi` | charleroi.be |
| La Louvière | `la-louvière` | lalouviere.be |
| Liège | `liège` | liege.be |
| Mons | `mons` | mons.be |
| Namur | `namur` | namur.be |

---

## Problèmes courants

**`selenium` ne trouve pas Chrome / ChromeDriver`**
> Vérifie que ChromeDriver est installé et que sa version correspond à celle de Chrome.
> Tu peux aussi l'installer automatiquement avec `pip install webdriver-manager` et adapter le code.

**Erreur `ModuleNotFoundError`**
> Vérifie que ton environnement virtuel est bien activé (`venv\Scripts\activate` sous Windows).

**Encodage sur Windows (caractères bizarres dans le terminal)**
> C'est un problème d'affichage uniquement — les fichiers JSON sont bien en UTF-8.
> Pour forcer UTF-8 dans le terminal : `chcp 65001`

**Pas de données dans `combined/`**
> Lance d'abord les deux scrapers pour générer les JSON, puis lance `merge_events.py`.
