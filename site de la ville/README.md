# Site de la Ville - Centre de Contrôle

Interface graphique centralisée pour la gestion du scraping d'événements sur les sites municipaux.

## 📋 Vue d'ensemble

Ce serveur Flask fournit un **centre de contrôle intégré** pour scraper et gérer les événements des sites municipaux :

- **Charleroi** : https://www.charleroi.be/agenda
- **La Louvière** : (À configurer)
- **Liège** : (À configurer)
- **Mons** : (À configurer)
- **Namur** : (À configurer)

## 🚀 Démarrage rapide

### Installation

```bash
pip install flask
```

### Lancement

```bash
python server.py
```

Le serveur démarre sur `http://localhost:5001` par défaut.

## 📊 Dashboard

Le dashboard offre une interface complète pour :

- ✅ **Visualiser les statuts** des données pour chaque ville
- 🔧 **Contrôler les scraps** - Lancer manuellement l'extraction de l'agenda et des détails
- 📊 **Voir les statistiques** - Nombre total d'événements collectés
- 📝 **Consulter la console** - Suivi en temps réel des tâches
- 🔗 **Navigation** - Basculer vers Quefaire.be

## 📡 API REST

### Endpoints

#### Statut global

```
GET /api/status
```

Retourne les données et statistiques globales de toutes les villes.

**Réponse :**

```json
{
  "status": "ok",
  "timestamp": "2026-04-03T12:34:56+00:00",
  "total_events": 245,
  "cities": {
    "Charleroi": {
      "city": "Charleroi",
      "has_data": true,
      "events_count": 50,
      "json_files": ["charleroi_03-04-26.json"],
      "metadata": {...}
    },
    ...
  }
}
```

#### Données d'une ville

```
GET /api/city/{city}
```

Retourne les données complètes et le statut du cache d'une ville.

**Réponse :**

```json
{
  "city": "Charleroi",
  "data": {
    "city": "Charleroi",
    "has_data": true,
    "events_count": 50,
    "json_files": ["charleroi_03-04-26.json"],
    "metadata": {...}
  },
  "cache": {
    "cached": true,
    "age_minutes": 125,
    "age_hours": 2.1,
    "timestamp": "2026-04-03T10:30:00Z"
  }
}
```

#### Lancer le scraping de l'agenda

```
POST /api/scrape/agenda
Content-Type: application/json

{"city": "Charleroi"}
```

Retourne l'ID de la tâche `task_id` pour suivi.

#### Lancer le scraping des détails

```
POST /api/scrape/details
Content-Type: application/json

{"city": "Charleroi"}
```

#### Récupérer les tâches

```
GET /api/tasks
```

Retourne toutes les tâches en cours et terminées.

#### Récupérer le statut d'une tâche

```
GET /api/tasks/{task_id}
```

## 🏗️ Structure

```
site de la ville/
├── server.py                    # Serveur Flask principal
├── Charleroi/
│   ├── scraper_agenda.py        # Scraper l'agenda municipal
│   ├── scraper_event_details.py # Extraire les détails des événements
│   └── charleroi_03-04-26.json  # Données collectées
├── La Louvière/
├── Liège/
├── Mons/
├── Namur/
├── templates/
│   └── dashboard.html           # Interface web
└── static/                      # (Ressources statiques - optionnel)
```

## 🔄 Flux de travail

1. **Accès au dashboard** : http://localhost:5001
2. **Sélection d'une ville** : Via le sélecteur de ville
3. **Lancement du scraping** :
   - Cliquer "Scraper l'agenda" pour extraire la liste des événements
   - Cliquer "Scraper les détails" pour extraire les détails de chaque événement
4. **Suivi en temps réel** : Console affiche la progression
5. **Consultation des résultats** : Les données JSON sont sauvegardées localement

## 📊 Format des données

### Structure JSON des événements

```json
{
  "metadata": {
    "extraction_date": "2026-04-03T12:34:56Z",
    "source": "charleroi.be",
    "total_events": 50
  },
  "events": [
    {
      "title": "Exposition d'art",
      "date": "2026-04-10",
      "time": "14:00",
      "location": "Musée de Charleroi",
      "url": "https://www.charleroi.be/agenda/exposition-dart",
      "description": "Une exposition fascinante...",
      "category": "Culture"
    },
    ...
  ]
}
```

## 🔧 Configuration

### Variables d'environnement

- `PORT` : Port d'écoute (par défaut 5001)
- `DEBUG` : Mode debug (par défaut true)

```bash
PORT=5002 DEBUG=false python server.py
```

## 📝 Logs et débogage

Les logs sont affichés dans :

1. La console du terminal
2. La console intégrée du dashboard

Format des logs :

```
[HH:MM:SS] [INFO|SUCCESS|ERROR] Message
```

## 🔗 Intégration avec Quefaire.be

Une barre de navigation en haut du dashboard permet de basculer vers Quefaire.be :

- 📦 Quefaire.be (http://localhost:5000)
- 🏢 Site de la Ville (http://localhost:5001)

Pour lancer les deux serveurs simultanément :

```bash
python run_all.py
```

## 🛠️ Dépannage

### Le dashboard ne charge pas

- Vérifiez que le serveur est actif : `python server.py`
- Vérifiez le port 5001 : `netstat -an | grep 5001`

### Les tâches ne démarrent pas

- Vérifiez que les scripts scrapers existent dans les dossiers des villes
- Vérifiez les permissions du dossier

### Erreurs de scraping

- Consultez la console du dashboard pour les détails
- Vérifiez la connexion internet et l'accès aux sites
- Vérifiez les changements de structure des sites web

## 🚀 Améliorations futures

- [ ] Base de données pour persister les données
- [ ] Planification automatique des scraps
- [ ] Statistiques avancées et graphiques
- [ ] Authentification utilisateur
- [ ] Export en CSV/Excel
- [ ] Notifications d'erreurs
- [ ] Tests unitaires

## 📄 License

Voir LICENSE à la racine du projet.

## 📞 Support

Pour les problèmes, consultez le [GUIDE_INTEGRATION.md](../GUIDE_INTEGRATION.md)
