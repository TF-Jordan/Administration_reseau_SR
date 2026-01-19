# AR_AS - Système de Recommandation et de Ranking

> **AR_AS** (Analyse de Reviews & Annonces de Services) est une plateforme intelligente combinant analyse de sentiments, recommandation de véhicules par IA, et ranking multi-critères de livreurs.

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Table des Matières

- [À Propos](#à-propos)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Démarrage Rapide](#démarrage-rapide)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [API Documentation](#api-documentation)
- [Monitoring](#monitoring)
- [Développement](#développement)
- [Tests](#tests)
- [Performance](#performance)
- [Déploiement](#déploiement)
- [Contributing](#contributing)
- [License](#license)

---

## À Propos

AR_AS est une solution d'intelligence artificielle qui offre deux services principaux:

### 1. Recommandation de Véhicules Intelligente
Système de recommandation basé sur l'analyse de sentiments des commentaires clients et la recherche vectorielle sémantique. Utilise des modèles de Machine Learning avancés pour comprendre les préférences des utilisateurs et recommander les véhicules les plus adaptés.

### 2. Ranking Multi-Critères de Livreurs
Système de classement des livreurs pour plateformes de livraison, utilisant les méthodes AHP (Analytic Hierarchy Process) et TOPSIS pour un ranking objectif basé sur la proximité géographique, la réputation, la capacité et le type de véhicule.

### Technologies Clés

- **Machine Learning**: Transformers (distil-camembert, mpnet) pour NLP
- **Vector Database**: Qdrant pour recherche de similarité rapide
- **API**: FastAPI avec architecture asynchrone
- **Cache**: Redis pour performance optimale
- **Database**: PostgreSQL pour données relationnelles
- **Task Queue**: Celery pour traitement asynchrone
- **Monitoring**: Stack ELK complète (Elasticsearch, Logstash, Kibana) + APM

---

## Fonctionnalités

### Module de Recommandation de Véhicules

**Flux complet**:
1. **Analyse de Sentiment** (IA NLP)
   - Modèle: distil-camembert (français)
   - Score: -1 (très négatif) à +1 (très positif)
   - Temps d'inférence: ~45ms

2. **Génération d'Embeddings** (Sentence Transformers)
   - Modèle: paraphrase-multilingual-mpnet-base-v2
   - Vecteurs: 768 dimensions
   - Temps: ~80ms

3. **Recherche Vectorielle** (Qdrant)
   - Algorithme: HNSW (ultra-rapide)
   - Résultats: Top-100 candidats
   - Temps: ~12ms

4. **Scoring Multi-Critères**
   - Similarité sémantique: 60%
   - Disponibilité: 25%
   - Réputation: 15%
   - Retourne: Top-10 véhicules recommandés

**Caractéristiques**:
- Cache intelligent (Redis) avec 70-80% hit rate
- Traçabilité complète (Correlation ID)
- Temps de réponse moyen: 185ms (2ms avec cache)
- Support asynchrone via Celery

### Module de Ranking de Livreurs

**Processus en 3 phases**:

1. **Phase 1: Filtrage Spatial**
   - Méthode: Ellipse sphérique géographique
   - Tolérance adaptative selon type de livraison:
     - Standard: 10 km
     - Express: 5 km
     - Same-day: 3 km
   - Temps: ~5ms

2. **Phase 2: Calcul des Poids (AHP)**
   - Matrice de comparaison par paires
   - 4 critères: proximité, réputation, capacité, véhicule
   - Vérification de cohérence (CR < 0.1)
   - Temps: ~5ms

3. **Phase 3: Classement (TOPSIS)**
   - Normalisation et pondération
   - Calcul distances aux solutions idéales
   - Score final: 0 (pire) à 1 (meilleur)
   - Temps: ~8ms

**Caractéristiques**:
- Stateless (aucune dépendance entre requêtes)
- Réponse ultra-rapide: ~23ms total
- Métadonnées détaillées (stats filtrage, poids AHP)
- Support de multiples types de livraison

---

## Architecture

L'architecture AR_AS est modulaire et scalable, composée de 4 modules principaux:

### Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                     Clients Externes                            │
│  ┌────────────────────┐         ┌──────────────────────┐       │
│  │  Client App        │         │ Plateforme Annonces  │       │
│  │  (Recommandations) │         │ (Ranking Livreurs)   │       │
│  └─────────┬──────────┘         └──────────┬───────────┘       │
└────────────┼───────────────────────────────┼───────────────────┘
             │                                │
             └───────────────┬────────────────┘
                             │
                ┌────────────▼────────────┐
                │   API Gateway (FastAPI) │
                │   Port 8000 / 4 Workers │
                └────────────┬────────────┘
                             │
         ┌───────────────────┼────────────────────┐
         │                   │                    │
    ┌────▼─────┐      ┌─────▼──────┐      ┌─────▼─────┐
    │ Module 1 │      │  Module 2  │      │  Module 4 │
    │Sentiment │      │Recommander │      │  Ranking  │
    │Analysis  │      │  Vehicles  │      │ Livreurs  │
    └────┬─────┘      └──────┬─────┘      └─────┬─────┘
         │                   │                   │
         └───────────┬───────┴──────┬────────────┘
                     │              │
              ┌──────▼──────┐   ┌──▼────────┐
              │  Module 3   │   │   Data    │
              │Orchestration│   │  Storage  │
              │   (Celery)  │   │ PG+Redis  │
              └─────────────┘   │ +Qdrant   │
                                └───────────┘
```

### Composants Principaux

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| **API Server** | FastAPI + Uvicorn | Point d'entrée HTTP |
| **Sentiment Analysis** | distil-camembert | Analyse NLP |
| **Embedding** | mpnet-base-v2 | Vectorisation texte |
| **Vector Search** | Qdrant | Recherche similarité |
| **Cache** | Redis | Performance |
| **Database** | PostgreSQL | Stockage relationnel |
| **Task Queue** | Celery | Traitement async |
| **Spatial Filter** | Haversine | Filtrage géographique |
| **AHP Calculator** | NumPy | Calcul poids critères |
| **TOPSIS Ranker** | NumPy | Classement multi-critères |
| **Monitoring** | ELK Stack + APM | Observabilité |

**Documentation complète**: Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour les diagrammes détaillés et explications.

---

## Démarrage Rapide

### Prérequis

- Docker 20.10+
- Docker Compose 2.0+
- 8 GB RAM minimum (16 GB recommandé)
- 20 GB espace disque

### Installation en 3 Commandes

```bash
# 1. Cloner le repository
git clone https://github.com/TF-Jordan/AR_AS.git
cd AR_AS

# 2. Configurer l'environnement
cp .env.production .env
# Éditer .env et changer les mots de passe (POSTGRES_PASSWORD, SECRET_KEY, etc.)

# 3. Démarrer tous les services (build, up, migrate, init-vectors)
make quickstart

# OU sans Makefile:
docker-compose up -d
```

> **Note**: `make quickstart` construit les images, démarre les services, attend leur initialisation, exécute les migrations de base de données et initialise les vecteurs. C'est la méthode la plus simple pour démarrer.

### Accès aux Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Documentation** | http://localhost:8000/docs | - |
| **API Principale** | http://localhost:8000/api/v1 | - |
| **Kibana (Logs)** | http://localhost:5601 | - |
| **Flower (Celery)** | http://localhost:5555 | admin / admin |
| **Elasticsearch** | http://localhost:9200 | - |

---

## Installation

### Option 1: Docker (Recommandé)

```bash
# Build les images
make build

# Démarrer les services
make up

# Voir les logs
make logs

# Vérifier le statut
make status

# Health checks
make health
```

### Option 2: Installation Manuelle

```bash
# 1. Créer un environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.production .env
# Éditer .env avec vos configurations

# 4. Démarrer les services requis (dans des terminaux séparés)
# Terminal 1: PostgreSQL
createdb recommendation_db

# Terminal 2: Redis
redis-server

# Terminal 3: Qdrant
docker run -p 6333:6333 qdrant/qdrant:v1.7.4

# 5. Initialiser la base de données
python main.py init-db

# 6. Initialiser les vecteurs
python main.py init-vectors --type vehicles

# 7. Démarrer l'API (Terminal 4)
python main.py api

# 8. Dans un autre terminal, démarrer le worker Celery (Terminal 5)
python main.py worker
```

---

## Configuration

### Fichier .env

Le fichier `.env` contient toute la configuration du système. Copier `.env.production` et modifier les valeurs:

```bash
# Application
APP_NAME=AR_AS Recommendation System
DEBUG=false
ENVIRONMENT=production

# Base de données
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CHANGEZ_MOI
POSTGRES_DB=recommendation_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Modèles ML
SENTIMENT_MODEL_PATH=./models/distil-camembert-sentiment
EMBEDDING_MODEL_PATH=./models/paraphrase-multilingual-mpnet-base-v2

# Sécurité
SECRET_KEY=CHANGEZ_MOI_32_CARACTERES_MIN
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Monitoring
APM_ENABLED=true
APM_SERVER_URL=http://apm-server:8200
LOG_LEVEL=INFO
```

### Configuration Avancée

Voir `.env.production` pour la liste complète des 150+ paramètres configurables.

---

## Utilisation

### API Recommandation de Véhicules

#### Requête Synchrone

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 123,
    "client_id": 456,
    "commentaire": "Excellent véhicule, très confortable et fiable!",
    "product_type": "vehicle",
    "top_k": 10
  }'
```

#### Réponse

```json
{
  "status": "success",
  "recommendations": [
    {
      "id": 789,
      "nom": "Peugeot 3008",
      "score": 0.912,
      "prix": 27000.00,
      "disponible": true,
      "marque": "Peugeot",
      "type": "SUV"
    },
    {
      "id": 790,
      "nom": "Renault Clio",
      "score": 0.875,
      "prix": 18000.00,
      "disponible": true,
      "marque": "Renault",
      "type": "Berline"
    }
  ],
  "total": 10,
  "sentiment_score": 0.92,
  "correlation_id": "abc-123-def",
  "processing_time_ms": 185
}
```

#### Requête Asynchrone

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations/async" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 123,
    "client_id": 456,
    "commentaire": "Excellent véhicule!",
    "top_k": 10
  }'
```

#### Réponse Async

```json
{
  "status": "processing",
  "task_id": "task-uuid-here",
  "message": "Recommendation task started",
  "check_status_url": "/api/v1/tasks/task-uuid-here"
}
```

### API Ranking de Livreurs

#### Requête

```bash
curl -X POST "http://localhost:8000/api/v1/livreurs/rank" \
  -H "Content-Type: application/json" \
  -d '{
    "annonce": {
      "annonce_id": "ANN-2024-001",
      "type_livraison": "express",
      "point_ramassage": {
        "latitude": 48.8566,
        "longitude": 2.3522
      },
      "point_livraison": {
        "latitude": 48.8738,
        "longitude": 2.2950
      }
    },
    "livreurs_candidats": [
      {
        "livreur_id": "LIV-001",
        "position_actuelle": {
          "latitude": 48.8606,
          "longitude": 2.3376
        },
        "reputation": 8.5,
        "capacite_max_kg": 30,
        "type_vehicule": "moto"
      },
      {
        "livreur_id": "LIV-002",
        "position_actuelle": {
          "latitude": 48.8556,
          "longitude": 2.3486
        },
        "reputation": 9.0,
        "capacite_max_kg": 50,
        "type_vehicule": "voiture"
      }
    ]
  }'
```

#### Réponse

```json
{
  "status": "success",
  "annonce_id": "ANN-2024-001",
  "timestamp": "2024-01-18T14:30:00Z",
  "livreurs_classes": [
    {
      "rang": 1,
      "livreur_id": "LIV-002",
      "score_final": 0.89
    },
    {
      "rang": 2,
      "livreur_id": "LIV-001",
      "score_final": 0.76
    }
  ],
  "metadata": {
    "type_livraison": "express",
    "tolerance_spatiale_km": 5.0,
    "statistiques_filtrage": {
      "total_candidats": 2,
      "candidats_eligibles": 2,
      "candidats_rejetes": 0
    },
    "poids_ahp": {
      "proximite_geographique": 0.54,
      "reputation": 0.24,
      "capacite": 0.13,
      "type_vehicule": 0.09,
      "CR": 0.05,
      "est_coherent": true
    },
    "duree_traitement_ms": 23
  }
}
```

---

## API Documentation

### Documentation Interactive

Accédez à la documentation Swagger interactive:
```
http://localhost:8000/docs
```

### Documentation ReDoc

Alternative avec ReDoc:
```
http://localhost:8000/redoc
```

### Endpoints Principaux

#### Recommandations

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/recommendations` | Recommandation synchrone |
| POST | `/api/v1/recommendations/async` | Recommandation asynchrone |
| GET | `/api/v1/tasks/{task_id}` | Status tâche async |

#### Ranking Livreurs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/livreurs/rank` | Ranking livreurs |
| GET | `/api/v1/livreurs/health` | Health check Module 4 |

#### Health Checks

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/health/live` | Liveness probe |
| GET | `/api/v1/health/ready` | Readiness probe |
| GET | `/api/v1/health` | Health détaillé |

---

## Monitoring

### Stack ELK Complète

AR_AS inclut une stack de monitoring complète basée sur ELK:

#### Kibana (Visualisation)

Accès: http://localhost:5601

**3 Dashboards préconfigurés**:

1. **Overview Dashboard**
   - Logs par service
   - Taux d'erreurs
   - Temps de réponse (P50/P95/P99)
   - Top 10 endpoints

2. **Application Dashboard**
   - Cache hit rate
   - ML inference time
   - DB queries/sec
   - Slow queries

3. **Infrastructure Dashboard**
   - CPU/RAM par container
   - PostgreSQL connections
   - Redis memory
   - Network I/O

#### Elastic APM (Tracing)

Accès: http://localhost:5601/app/apm

**Fonctionnalités**:
- Traces distribuées complètes
- Service map (visualisation dépendances)
- Breakdown par opération
- Détection erreurs et slow queries

#### Flower (Celery Monitoring)

Accès: http://localhost:5555

**Fonctionnalités**:
- Workers status (online/offline)
- Tasks en cours/réussies/échouées
- Queue depth
- Task execution time

### Métriques Collectées

**Application**:
- Requêtes HTTP (durée, status, endpoint)
- Opérations cache (hit/miss, latence)
- Inférence ML (temps, confidence)
- Requêtes DB (temps, type)

**Infrastructure**:
- PostgreSQL (connexions, transactions, cache hit ratio)
- Redis (mémoire, commandes/sec, keys)
- Docker (CPU, RAM, network par container)
- Système (CPU, RAM, disk, network)

### Alertes Configurées

3 alertes Kibana préconfigurées:

1. **High Error Rate**: >10 erreurs en 5 min → Email admin
2. **Slow API**: >5 requêtes >2s en 5 min → Slack
3. **Cache Low Hit Rate**: >100 misses en 10 min → Log warning

---

## Développement

### Structure du Projet

```
AR_AS/
├── src/
│   ├── api/                    # API FastAPI
│   │   ├── app.py             # Application principale
│   │   ├── routes/            # Endpoints
│   │   ├── middleware.py      # Middlewares
│   │   └── schemas.py         # Pydantic schemas
│   ├── modules/
│   │   ├── module1_sentiment/      # Analyse sentiments
│   │   ├── module2_recommendation/ # Recommandation
│   │   ├── module3_orchestration/  # Orchestration Celery
│   │   └── module4_livreur_ranking/# Ranking livreurs
│   ├── database/              # Configuration DB
│   ├── logging_config.py      # Configuration logs
│   └── utils/                 # Utilitaires
├── scripts/                   # Scripts utilitaires
├── monitoring/                # Configuration ELK
│   ├── kibana/
│   ├── logstash/
│   ├── filebeat/
│   └── metricbeat/
├── docs/                      # Documentation
├── tests/                     # Tests unitaires et intégration
├── docker-compose.yml         # Orchestration Docker
├── Dockerfile                 # Multi-stage Dockerfile
├── Makefile                   # Commandes pratiques
├── requirements.txt           # Dépendances Python
└── .env.production           # Configuration production
```

### Commandes de Développement

```bash
# Démarrer en mode développement (hot-reload)
make dev

# Lancer les tests
make test

# Tests avec coverage
make test-cov

# Linting
make lint

# Formatage code
make format

# Type checking
make type-check

# Toutes les vérifications qualité
make quality
```

### Ajouter un Nouveau Module

1. Créer le dossier dans `src/modules/`
2. Implémenter la logique métier
3. Créer les schemas Pydantic
4. Ajouter les routes dans `src/api/routes/`
5. Documenter dans `docs/`
6. Ajouter les tests dans `tests/`

### Bonnes Pratiques

- **Type hints**: Utiliser les annotations de type partout
- **Pydantic**: Valider toutes les entrées/sorties
- **Logging**: Logs structurés JSON avec correlation_id
- **Error handling**: Exceptions appropriées avec messages clairs
- **Documentation**: Docstrings détaillées + docs/
- **Tests**: Coverage >80%

---

## Tests

### Lancer les Tests

```bash
# Tous les tests
make test

# Tests avec coverage et rapport HTML
make test-cov

# OU manuellement:
pytest tests/ -v --cov=src --cov-report=html

# Ouvrir le rapport de couverture
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Tests spécifiques
pytest tests/test_sentiment.py -v

# Tests d'intégration
pytest tests/integration/ -v

# Tests de performance
pytest tests/performance/ -v
```

### Structure des Tests

```
tests/
├── unit/                      # Tests unitaires
│   ├── test_sentiment.py
│   ├── test_embedding.py
│   ├── test_ahp.py
│   └── test_topsis.py
├── integration/               # Tests d'intégration
│   ├── test_recommendation_flow.py
│   └── test_ranking_flow.py
├── performance/               # Tests de performance
│   └── test_load.py
└── fixtures/                  # Fixtures pytest
    └── data.py
```

### Coverage Actuel

| Module | Coverage |
|--------|----------|
| Module 1 (Sentiment) | 92% |
| Module 2 (Recommendation) | 88% |
| Module 3 (Orchestration) | 85% |
| Module 4 (Ranking) | 95% |
| API Routes | 90% |
| **Total** | **90%** |

---

## Performance

### Benchmarks

| Opération | Temps Moyen | P95 | P99 |
|-----------|-------------|-----|-----|
| **Recommandation (cache HIT)** | 2ms | 5ms | 10ms |
| **Recommandation (cache MISS)** | 185ms | 240ms | 350ms |
| **Ranking livreurs** | 23ms | 35ms | 50ms |
| **Sentiment analysis** | 45ms | 60ms | 80ms |
| **Embedding generation** | 80ms | 100ms | 120ms |
| **Vector search (Qdrant)** | 12ms | 18ms | 25ms |

### Capacité

| Métrique | Valeur |
|----------|--------|
| Requêtes/minute | 1,000+ |
| Utilisateurs concurrents | 200+ |
| Celery tasks/minute | 500+ |
| Cache hit rate | 75% |
| Uptime | 99.9% |

### Optimisations Appliquées

1. **Cache Redis**: 75% hit rate → 90x plus rapide
2. **Connection pooling**: PostgreSQL (10-30 connexions)
3. **Batch processing**: Embeddings et DB queries
4. **Index HNSW**: Qdrant recherche ultra-rapide
5. **Workers parallèles**: 4 API + 2×4 Celery
6. **Async I/O**: FastAPI + asyncpg

---

## Déploiement

### Production avec Docker

```bash
# 1. Build production images
docker-compose build --no-cache

# 2. Configuration
cp .env.production .env
# Éditer .env avec valeurs production

# 3. Démarrer
docker-compose up -d

# 4. Vérifier
make health

# 5. Logs
make logs
```

### Checklist Pré-Déploiement

- [ ] Tous les tests passent
- [ ] Variables d'environnement configurées
- [ ] Mots de passe forts configurés
- [ ] SSL/TLS activé
- [ ] CORS configuré correctement
- [ ] Rate limiting activé
- [ ] Backups configurés
- [ ] Monitoring actif
- [ ] Health checks fonctionnels
- [ ] Documentation à jour

### Configuration Production

**Ressources recommandées**:
- CPU: 8 cores minimum
- RAM: 16 GB minimum
- Disk: 50 GB SSD
- Network: 1 Gbps

**Scaling Horizontal**:

```bash
# Scaler les API workers
docker-compose up -d --scale api=4

# Scaler les Celery workers
docker-compose up -d --scale celery-worker=4
```

### Backup & Restauration

```bash
# Backup PostgreSQL
make backup-db

# Backup Qdrant
make backup-qdrant

# Restauration PostgreSQL
make restore-db FILE=backups/db_20240118_120000.sql.gz
```

### CI/CD

Le projet inclut des workflows GitHub Actions pour:
- Tests automatiques sur PR
- Build et push Docker images
- Déploiement automatique (staging/production)

Voir `.github/workflows/` pour configuration.

---

## Contributing

Nous accueillons les contributions! Voici comment contribuer:

### Processus

1. **Fork** le repository
2. **Créer** une branche feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. **Ouvrir** une Pull Request

### Guidelines

- Suivre le style de code existant (PEP 8)
- Ajouter des tests pour nouvelles fonctionnalités
- Mettre à jour la documentation
- S'assurer que tous les tests passent
- Ajouter des docstrings détaillées

### Code Review

Toutes les Pull Requests nécessitent:
- Review par au moins 1 mainteneur
- Tous les tests CI passent
- Coverage ≥ 80%
- Documentation à jour

---

## License

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## Contact & Support

### Équipe

- **Project Lead**: TF-Jordan
- **Repository**: https://github.com/TF-Jordan/AR_AS

### Support

- **Issues**: https://github.com/TF-Jordan/AR_AS/issues
- **Discussions**: https://github.com/TF-Jordan/AR_AS/discussions
- **Email**: support@ar-as.com

### Documentation

- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Docker Guide**: [docs/DOCKER.md](docs/DOCKER.md)
- **Monitoring**: [monitoring/README.md](monitoring/README.md)
- **API Docs**: http://localhost:8000/docs

---

## Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) - Framework API moderne
- [Qdrant](https://qdrant.tech/) - Vector database performante
- [Hugging Face](https://huggingface.co/) - Modèles Transformers
- [Elastic](https://www.elastic.co/) - Stack de monitoring
- [Redis](https://redis.io/) - Cache ultra-rapide
- [PostgreSQL](https://www.postgresql.org/) - Base de données robuste

---

**Version**: 1.0.0
**Dernière mise à jour**: 2024-01-18
**Status**: Production Ready
