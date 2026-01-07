# Système de Recommandation Basé sur l'Analyse de Sentiment

Un système modulaire de recommandation basé sur l'analyse de sentiment, conçu pour deux types de plateformes :
- **Plateforme de livraison** → Recommandation de livreurs
- **Plateforme de location de véhicules** → Recommandation de véhicules

## 🏗️ Architecture

Le système suit une architecture microservices avec trois modules distincts :

```
┌─────────────────────────────────────────────────────────────────┐
│                      Module 3 - Orchestration                     │
│                    (FastAPI + Celery + Redis)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│  Module 1 - Sentiment   │     │   Module 2 - Recommendation     │
│   (distil-camembert)    │────▶│  (Embeddings + Qdrant + Ranking)│
└─────────────────────────┘     └─────────────────────────────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                         PostgreSQL        Redis          Qdrant
```

### Module 1 - Analyse de Sentiment
- Analyse de sentiment des commentaires clients
- Modèle : distil-camembert fine-tuné
- Sortie : score de sentiment (-1 à 1)

### Module 2 - Moteur de Recommandation
1. Vérification du cache Redis
2. Récupération des données produit (PostgreSQL)
3. Construction de description textuelle
4. Génération d'embedding (paraphrase-multilingual-mpnet-base-v2)
5. Recherche sémantique (Qdrant / HNSW)
6. Ranking final basé sur : similarité, disponibilité, réputation

### Module 3 - Orchestration & API
- API FastAPI avec documentation Swagger
- Tâches asynchrones via Celery
- Rate limiting et authentification
- Monitoring (Prometheus + Grafana, ELK Stack)

## 🚀 Démarrage Rapide

### Avec Docker (Recommandé)

```bash
# Cloner le repository
git clone <repository-url>
cd reseau2

# Démarrer tous les services
make docker-up

# Ou manuellement
docker-compose up -d
```

Services disponibles :
- **API** : http://localhost:8000
- **Documentation Swagger** : http://localhost:8000/docs
- **Flower (Celery)** : http://localhost:5555
- **Grafana** : http://localhost:3000 (admin/admin)
- **Kibana** : http://localhost:5601
- **Prometheus** : http://localhost:9090

### Installation Locale

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos configurations

# Initialiser la base de données
python main.py init-db

# Initialiser les vecteurs
python main.py init-vectors --type all

# Démarrer l'API
python main.py api

# Dans un autre terminal, démarrer le worker Celery
python main.py worker
```

## 📖 Utilisation de l'API

### Obtenir des Recommandations (Workflow Complet)

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations/" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_id": "client_123",
    "commentaire": "Excellent service, très professionnel!",
    "product_type": "vehicle",
    "top_k": 10,
    "async_processing": false
  }'
```

### Analyse de Sentiment Seule

```bash
curl -X POST "http://localhost:8000/api/v1/sentiment/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "vehicle_123",
    "client_id": "client_456",
    "commentaire": "Service rapide et efficace"
  }'
```

### Recommandations avec Score de Sentiment Pré-calculé

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations/direct" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "550e8400-e29b-41d4-a716-446655440000",
    "client_id": "client_123",
    "sentiment_score": 0.75,
    "product_type": "vehicle",
    "top_k": 10
  }'
```

### Traitement Asynchrone

```bash
# Soumettre une tâche
curl -X POST "http://localhost:8000/api/v1/recommendations/" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "vehicle_123",
    "client_id": "client_456",
    "commentaire": "Très bon véhicule",
    "product_type": "vehicle",
    "async_processing": true
  }'

# Vérifier le statut
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

## 🔧 Configuration

Les configurations sont gérées via les variables d'environnement (fichier `.env`) :

| Variable | Description | Défaut |
|----------|-------------|--------|
| `POSTGRES_HOST` | Hôte PostgreSQL | localhost |
| `REDIS_HOST` | Hôte Redis | localhost |
| `QDRANT_HOST` | Hôte Qdrant | localhost |
| `EMBEDDING_MODEL_NAME` | Modèle d'embedding | paraphrase-multilingual-mpnet-base-v2 |
| `SIMILARITY_WEIGHT` | Poids de la similarité | 0.6 |
| `AVAILABILITY_WEIGHT` | Poids de la disponibilité | 0.25 |
| `REPUTATION_WEIGHT` | Poids de la réputation | 0.15 |

## 📊 Monitoring

### Prometheus Metrics

L'API expose des métriques Prometheus sur `/metrics` :
- Requêtes HTTP (count, duration)
- Tâches Celery (pending, completed, failed)
- Cache hits/misses

### Grafana Dashboards

Dashboards pré-configurés pour :
- Performance de l'API
- Métriques Celery
- Statistiques de cache

### Logs (ELK Stack)

Les logs sont collectés automatiquement et disponibles dans Kibana avec :
- Structured JSON logging
- Correlation IDs
- Request tracing

## 🧪 Tests

```bash
# Exécuter tous les tests
make test

# Tests avec couverture
pytest tests/ -v --cov=src --cov-report=html

# Ouvrir le rapport de couverture
open htmlcov/index.html
```

## 📁 Structure du Projet

```
reseau2/
├── src/
│   ├── api/                    # FastAPI application
│   │   ├── routes/             # API endpoints
│   │   ├── schemas.py          # Pydantic schemas
│   │   └── app.py              # Application factory
│   ├── config/                 # Configuration
│   ├── database/               # Models & repositories
│   ├── modules/
│   │   ├── module1_sentiment/  # Sentiment analysis
│   │   ├── module2_recommendation/  # Recommendation engine
│   │   └── module3_orchestration/   # Celery & orchestration
│   └── logging_config.py
├── scripts/                    # Utility scripts
├── monitoring/                 # Prometheus, Grafana, ELK configs
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── main.py                     # Entry point
```

## 🤝 Contribution

1. Fork le repository
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push sur la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## 📝 License

Ce projet est sous licence MIT.
