# Guide d'Intégration - Quefaire.be & Site de la Ville

## 📋 Vue d'ensemble

Ce guide explique comment lancer et utiliser les deux dashboards intégrés :

- **Quefaire.be** : Gestionnaire de scraping d'événements sur quefaire.be
- **Site de la Ville** : Gestionnaire de scraping d'événements sur les sites municipaux

## 🚀 Démarrage des services

### Prérequis

Assurez-vous d'avoir Python 3.8+ et pip installés.

### Installation des dépendances

**Pour quefaire.be :**

```bash
cd quefaire.be
pip install -r requirements.txt
```

**Pour site de la ville :**

```bash
cd "site de la ville"
pip install flask
```

### Lancement des serveurs

**Terminal 1 - Quefaire.be (port 5000) :**

```bash
cd quefaire.be
python server.py
```

**Terminal 2 - Site de la Ville (port 5001) :**

```bash
cd "site de la ville"
python server.py
```

### Accès aux dashboards

- **Quefaire.be** : http://localhost:5000
- **Site de la Ville** : http://localhost:5001

## 🔗 Navigation entre les projets

Une barre de navigation commune figure en haut de chaque dashboard, permettant de basculer facilement entre :

- 📦 **Quefaire.be** : Scraper l'agenda quefaire.be
- 🏢 **Site de la Ville** : Scraper les agendas municipaux

## 📊 Fonctionnalités

### Quefaire.be Dashboard

- Gestion des villes (Charleroi, La Louvière, Liège, Mons, Namur)
- Scraping des URLs d'événements
- Extraction des détails d'événements
- Visualisation des données collectées
- Console de débogage en temps réel

### Site de la Ville Dashboard

- Gestion des agendas municipaux (Charleroi, La Louvière, Liège, Mons, Namur)
- Scraping de l'agenda municipal
- Scraping des détails d'événements
- Statistiques globales des événements
- Console de suivi des tâches

## 🔧 Architecture

### Quefaire.be

- **Port** : 5000
- **Scripts** :
  - `extract_urls.py` - Extraction des URLs d'événements
  - `extract_event_details.py` - Extraction des détails
  - Modules dans `src/` pour le fonctionnement avancé

### Site de la Ville

- **Port** : 5001
- **Serveur** : `server.py` (nouvellement créé)
- **Dashboard** : `templates/dashboard.html` (nouvellement créé)
- **Structure** : Dossiers par ville (Charleroi, La Louvière, Liège, Mons, Namur)
  - `scraper_agenda.py` - Scraping de l'agenda
  - `scraper_event_details.py` - Scraping des détails

## 📡 API Endpoints - Site de la Ville

### Récupérer les statuts

```bash
GET http://localhost:5001/api/status
```

### Récupérer les données d'une ville

```bash
GET http://localhost:5001/api/city/{city}
```

### Récupérer les tâches

```bash
GET http://localhost:5001/api/tasks
GET http://localhost:5001/api/tasks/{task_id}
```

### Lancer un scraping d'agenda

```bash
POST http://localhost:5001/api/scrape/agenda
Content-Type: application/json

{"city": "Charleroi"}
```

### Lancer un scraping de détails

```bash
POST http://localhost:5001/api/scrape/details
Content-Type: application/json

{"city": "Charleroi"}
```

## 🎨 Design et Styles

Les deux dashboards utilisent :

- **Thème sombre** : Fond #0f1117, surface #1a1d27
- **Couleurs d'accent** : Violet #6c5ce7
- **Responsive** : Adaptation automatique mobile/desktop

## 📝 Logs et Débogage

Les deux dashboards incluent une console en temps réel affichant :

- Les tâches en cours
- Les statuts de scraping
- Les erreurs et avertissements
- Les durées d'exécution

## 🔄 Synchronisation des données

Les données sont sauvegardées localement dans les dossiers correspondants à chaque ville avec horodatages pour tracer les mises à jour.

## 🛠️ Dépannage

### Le dashboard "Site de la Ville" ne charge pas

1. Vérifiez que le serveur est bien lancé : `python server.py`
2. Vérifiez que le port 5001 est disponible
3. Consultez la console pour les erreurs

### Les liens de navigation ne fonctionnent pas

1. Assurez-vous que les deux serveurs sont actifs
2. Vérifiez les URLs de navigation dans `dashboard.html`
3. Vérifiez que les ports sont corrects (5000 et 5001)

### Erreurs lors du scraping

1. Vérifiez que les scripts scrapers existent dans les dossiers des villes
2. Consultez la console de débogage pour les messages d'erreur
3. Assurez-vous que les dépendances sont installées

## 📚 Fichiers modifiés/créés

### Nouveaux fichiers

- `site de la ville/server.py` - Serveur Flask
- `site de la ville/templates/dashboard.html` - Dashboard intégré
- `site de la ville/templates/` - Dossier templates créé
- `site de la ville/static/` - Dossier static créé

### Fichiers modifiés

- `quefaire.be/templates/dashboard.html` - Ajout de la navbar

## 🎯 Prochaines étapes potentielles

1. Ajouter une authentification utilisateur
2. Implémenter une base de données pour persister les données
3. Créer une API unifiée pour les deux projets
4. Ajouter des graphiques de statistiques avancées
5. Implémenter des planifications de tâches automatiques
6. Ajouter l'export des données (CSV, Excel, JSON)

---

Pour plus d'informations, consultez les README.md de chaque projet.
