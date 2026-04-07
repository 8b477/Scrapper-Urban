# 📦 Résumé : Intégration des Dashboards

Date: 3 avril 2026
Projet: Scraper Urban - Quefaire.be et Site de la Ville

## ✅ Ce qui a été fait

### 1. **Nouveau serveur Flask pour Site de la Ville**

- Fichier: `site de la ville/server.py`
- Port: 5001
- Endpoints REST complets pour:
  - Récupérer le statut global (`/api/status`)
  - Récupérer les données par ville (`/api/city/{city}`)
  - Lancer des scraps fondé sur les villes (`/api/scrape/agenda`, `/api/scrape/details`)
  - Suivre les tâches (`/api/tasks`, `/api/tasks/{task_id}`)

### 2. **Dashboard Web pour Site de la Ville**

- Fichier: `site de la ville/templates/dashboard.html`
- Interface complète avec:
  - 📊 Statistiques globales (nombre d'événements totaux)
  - 🏙️ Gestion des villes (Charleroi, La Louvière, Liège, Mons, Namur)
  - 🔧 Contrôles de scraping avec sélection de ville
  - ⏱️ Suivi des tâches en temps réel
  - 📝 Console de débogage
  - 🔗 Barre de navigation intégrée

### 3. **Barre de Navigation Commune**

- Ajoutée à `quefaire.be/templates/dashboard.html`
- Ajoutée à `site de la ville/templates/dashboard.html`
- Permet de basculer facilement entre:
  - 📦 Quefaire.be (http://localhost:5000)
  - 🏢 Site de la Ville (http://localhost:5001)

### 4. **Documentation Complète**

- `GUIDE_INTEGRATION.md` : Guide d'intégration et d'utilisation
- `site de la ville/README.md` : Documentation du serveur
- `run_all.py` : Lanceur Python pour démarrer les deux serveurs
- `run_all.bat` : Lanceur Windows (batch) pour facilité

### 5. **Design Unifié**

- Thème sombre cohérent sur les deux dashboards
- Couleurs d'accent harmonisées (violet #6c5ce7)
- Responsive design (desktop et mobile)
- Console en temps réel avec logs formatés

## 🚀 Comment démarrer

### Option 1 : Windows (le plus simple)

```bash
Double-clic sur: run_all.bat
```

### Option 2 : Python (multiplateforme)

```bash
python run_all.py
```

### Option 3 : Manuel (2 terminaux)

```bash
# Terminal 1
cd quefaire.be
python server.py

# Terminal 2
cd "site de la ville"
python server.py
```

## 📍 URLs d'accès

Une fois les serveurs lancés:

- **Quefaire.be** : http://localhost:5000
- **Site de la Ville** : http://localhost:5001

## 📁 Fichiers créés/modifiés

### ✨ Nouveaux (9 fichiers)

1. `site de la ville/server.py` - Serveur Flask
2. `site de la ville/templates/dashboard.html` - Dashboard avec UI complète
3. `site de la ville/templates/.gitkeep` - Dossier templates
4. `site de la ville/static/.gitkeep` - Dossier static
5. `GUIDE_INTEGRATION.md` - Docs complètes d'intégration
6. `site de la ville/README.md` - Docs Site de la Ville
7. `run_all.py` - Lanceur Python
8. `run_all.bat` - Lanceur Windows
9. `/memories/repo/architecture.md` - Mise à jour architecture

### 📝 Modifiés (1 fichier)

1. `quefaire.be/templates/dashboard.html` - Ajout navbar

## 🎯 Fonctionnalités principales

### Quefaire.be Dashboard

✅ Extraction des URLs d'événements  
✅ Scraping des détails d'événements  
✅ Statut par ville  
✅ Console en temps réel  
✅ Lien vers Site de la Ville

### Site de la Ville Dashboard

✅ Scraping de l'agenda municipal  
✅ Scraping des détails événements  
✅ Vue d'ensemble globale  
✅ Gestion par ville  
✅ Suivi des tâches asynchrones  
✅ Console de débogage  
✅ Lien vers Quefaire.be

## 🔗 Navigation intégrée

Chaque dashboard affiche une barre de navigation permettant de:

- Voir le nom du projet actuel
- Basculer vers l'autre projet d'un clic
- Marquer le projet actif avec un badge

## 📊 Données affichées

### Quefaire.be

- Statut du scraping (urls et détails)
- Nombre d'événements par ville
- Fichiers JSON générés
- Tâches en cours

### Site de la Ville

- Nombre total d'événements (toutes villes)
- Dernière mise à jour
- Villes couvertes
- Détails des données par ville

## 🔧 Architecture technique

- **Framework**: Flask (léger, simple à déployer)
- **Frontend**: HTML5 + CSS3 (thème sombre natif)
- **JS**: Vanilla JavaScript (fetch API, événements)
- **API**: REST endpoints JSON
- **Async**: Threading pour exécution des scripts scrapers
- **Logs**: Streaming en temps réel via console

## 🛠️ Dépendances requises

```
Flask            # Serveur web
(+ dépendances existantes: requests, beautifulsoup4, etc.)
```

Pour installer:

```bash
pip install flask
```

## 📝 Notes importantes

1. **Ports** : Assurez-vous que 5000 et 5001 ne sont pas utilisés
2. **Scripts scrapers** : Les scripts scrapers doivent être présents pour fonctionner
3. **Dépendances** : Chaque projet a ses propres dépendances
4. **Logs** : Consultables en temps réel sur le dashboard

## 🔄 Prochaines étapes potentielles

1. ✅ **Déploiement multilingue** (FR/EN)
2. ✅ **API unifiée** (endpoint central pour les deux serveurs)
3. ✅ **Base de données** (au lieu de fichiers JSON)
4. ✅ **Authentification** (login simple)
5. ✅ **Graphiques** (Chart.js ou similar)
6. ✅ **Export** (CSV, Excel, PDF)
7. ✅ **Dockerization** (pour déploiement simple)
8. ✅ **CI/CD** (tests automatiques)

## 💾 Sauvegarde des données

Les données collectées sont sauvegardées dans:

- `quefaire.be/{city}/{city}-DD-MM-YY.json`
- `site de la ville/{city}/{city}_DD-MM-YY.json`

Format unifié avec métadonnées (timestamp, source, nombre d'événements).

## 🐛 Débogage

Si quelque chose ne fonctionne pas:

1. Consultez la console du dashboard (logs en temps réel)
2. Vérifiez les terminaux des serveurs pour les erreurs
3. Vérifiez le port (netstat -an | grep 5000/5001)
4. Consultez le GUIDE_INTEGRATION.md pour le dépannage complet

## 📞 Support

Pour toute question ou problème, consultez:

- `GUIDE_INTEGRATION.md` - Guide complet
- `site de la ville/README.md` - Documentation Site
- `quefaire.be/README.md` - Documentation Quefaire

---

**Bon scraping ! 🚀**
