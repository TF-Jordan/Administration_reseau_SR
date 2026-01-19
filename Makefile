# ==============================================================================
# Makefile for AR_AS Recommendation System
# Simplifies Docker operations and development workflow
# ==============================================================================

.PHONY: help build up down restart logs clean test lint format migrate seed backup restore

# Default target
.DEFAULT_GOAL := help

# Load environment variables
include .env.example
export

# ==============================================================================
# COLORS FOR OUTPUT
# ==============================================================================
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ==============================================================================
# HELP
# ==============================================================================
help: ## Show this help message
	@echo "$(BLUE)==================================================================$(NC)"
	@echo "$(BLUE)  AR_AS Recommendation System - Docker Management$(NC)"
	@echo "$(BLUE)==================================================================$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ==============================================================================
# DOCKER BUILD & RUN
# ==============================================================================
build: ## Build all Docker images
	@echo "$(BLUE)Building all Docker images...$(NC)"
	docker-compose build --parallel
	@echo "$(GREEN)✓ Build complete!$(NC)"

build-no-cache: ## Build all Docker images without cache
	@echo "$(BLUE)Building all Docker images (no cache)...$(NC)"
	docker-compose build --parallel --no-cache
	@echo "$(GREEN)✓ Build complete!$(NC)"

up: ## Start all services in detached mode
	@echo "$(BLUE)Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ All services started!$(NC)"
	@echo "$(YELLOW)API:     http://localhost:8000$(NC)"
	@echo "$(YELLOW)Docs:    http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Flower:  http://localhost:5555$(NC)"
	@echo "$(YELLOW)Kibana:  http://localhost:5601$(NC)"

up-build: ## Build and start all services
	@echo "$(BLUE)Building and starting all services...$(NC)"
	docker-compose up -d --build
	@echo "$(GREEN)✓ All services started!$(NC)"

down: ## Stop and remove all containers
	@echo "$(BLUE)Stopping all services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ All services stopped!$(NC)"

down-volumes: ## Stop and remove all containers and volumes
	@echo "$(RED)Stopping all services and removing volumes...$(NC)"
	@read -p "This will delete all data. Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "$(GREEN)✓ Services stopped and volumes removed!$(NC)"; \
	else \
		echo "$(YELLOW)Operation cancelled.$(NC)"; \
	fi

restart: ## Restart all services
	@echo "$(BLUE)Restarting all services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✓ Services restarted!$(NC)"

restart-api: ## Restart only the API service
	@echo "$(BLUE)Restarting API service...$(NC)"
	docker-compose restart api
	@echo "$(GREEN)✓ API restarted!$(NC)"

restart-worker: ## Restart Celery workers
	@echo "$(BLUE)Restarting Celery workers...$(NC)"
	docker-compose restart celery-worker
	@echo "$(GREEN)✓ Workers restarted!$(NC)"

# ==============================================================================
# LOGS & MONITORING
# ==============================================================================
logs: ## Show logs from all services
	docker-compose logs -f

logs-api: ## Show logs from API service
	docker-compose logs -f api

logs-worker: ## Show logs from Celery workers
	docker-compose logs -f celery-worker

logs-postgres: ## Show logs from PostgreSQL
	docker-compose logs -f postgres

logs-redis: ## Show logs from Redis
	docker-compose logs -f redis

logs-elk: ## Show logs from ELK stack
	docker-compose logs -f elasticsearch logstash kibana

status: ## Show status of all services
	@echo "$(BLUE)Service Status:$(NC)"
	@docker-compose ps

ps: status ## Alias for status

# ==============================================================================
# SHELL ACCESS
# ==============================================================================
shell-api: ## Open shell in API container
	docker-compose exec api /bin/bash

shell-worker: ## Open shell in Worker container
	docker-compose exec celery-worker /bin/bash

shell-postgres: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-recommendation_db}

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli

# ==============================================================================
# DATABASE OPERATIONS
# ==============================================================================
migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	docker-compose exec api alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete!$(NC)"

migrate-create: ## Create a new migration (use: make migrate-create MESSAGE="description")
	@echo "$(BLUE)Creating new migration...$(NC)"
	docker-compose exec api alembic revision --autogenerate -m "$(MESSAGE)"
	@echo "$(GREEN)✓ Migration created!$(NC)"

migrate-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	docker-compose exec api alembic downgrade -1
	@echo "$(GREEN)✓ Rollback complete!$(NC)"

seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	docker-compose exec api python scripts/seed_data.py
	@echo "$(GREEN)✓ Database seeded!$(NC)"

init-vectors: ## Initialize vector database
	@echo "$(BLUE)Initializing vector database...$(NC)"
	docker-compose exec api python scripts/init_vectors.py
	@echo "$(GREEN)✓ Vector database initialized!$(NC)"

# ==============================================================================
# BACKUP & RESTORE
# ==============================================================================
backup-db: ## Backup PostgreSQL database
	@echo "$(BLUE)Backing up database...$(NC)"
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U $${POSTGRES_USER:-postgres} $${POSTGRES_DB:-recommendation_db} | gzip > backups/db_$(shell date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)✓ Database backup created in backups/$(NC)"

restore-db: ## Restore PostgreSQL database (use: make restore-db FILE=backups/db_YYYYMMDD_HHMMSS.sql.gz)
	@echo "$(YELLOW)Restoring database from $(FILE)...$(NC)"
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: Please specify FILE=path/to/backup.sql.gz$(NC)"; \
		exit 1; \
	fi
	gunzip < $(FILE) | docker-compose exec -T postgres psql -U $${POSTGRES_USER:-postgres} $${POSTGRES_DB:-recommendation_db}
	@echo "$(GREEN)✓ Database restored!$(NC)"

backup-qdrant: ## Backup Qdrant vector database
	@echo "$(BLUE)Creating Qdrant snapshot...$(NC)"
	docker-compose exec qdrant curl -X POST "http://localhost:6333/snapshots"
	@echo "$(GREEN)✓ Qdrant snapshot created!$(NC)"

# ==============================================================================
# TESTING & QUALITY
# ==============================================================================
test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	docker-compose exec api pytest -v
	@echo "$(GREEN)✓ Tests complete!$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose exec api pytest --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Tests complete! Coverage report in htmlcov/$(NC)"

lint: ## Run linters
	@echo "$(BLUE)Running linters...$(NC)"
	docker-compose exec api flake8 src/
	@echo "$(GREEN)✓ Linting complete!$(NC)"

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	docker-compose exec api black src/
	@echo "$(GREEN)✓ Formatting complete!$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	docker-compose exec api mypy src/
	@echo "$(GREEN)✓ Type checking complete!$(NC)"

quality: lint type-check test ## Run all quality checks

# ==============================================================================
# CLEANUP
# ==============================================================================
clean: ## Remove stopped containers and unused images
	@echo "$(BLUE)Cleaning up Docker resources...$(NC)"
	docker-compose down --remove-orphans
	docker system prune -f
	@echo "$(GREEN)✓ Cleanup complete!$(NC)"

clean-all: ## Remove all containers, images, and volumes
	@echo "$(RED)This will remove ALL Docker resources for this project.$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		docker system prune -a -f --volumes; \
		echo "$(GREEN)✓ All resources removed!$(NC)"; \
	else \
		echo "$(YELLOW)Operation cancelled.$(NC)"; \
	fi

clean-logs: ## Remove log volumes
	@echo "$(BLUE)Removing log volumes...$(NC)"
	docker volume rm ar-as-api-logs ar-as-worker-logs || true
	@echo "$(GREEN)✓ Log volumes removed!$(NC)"

# ==============================================================================
# HEALTH CHECKS
# ==============================================================================
health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo ""
	@echo "$(YELLOW)API Health:$(NC)"
	@curl -sf http://localhost:8000/api/v1/health/live || echo "$(RED)✗ API not healthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Elasticsearch Health:$(NC)"
	@curl -sf http://localhost:9200/_cluster/health || echo "$(RED)✗ Elasticsearch not healthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Kibana Health:$(NC)"
	@curl -sf http://localhost:5601/api/status || echo "$(RED)✗ Kibana not healthy$(NC)"
	@echo ""

# ==============================================================================
# MONITORING
# ==============================================================================
monitor-api: ## Monitor API metrics
	@echo "$(BLUE)Opening API metrics...$(NC)"
	@open http://localhost:8000/api/v1/metrics || xdg-open http://localhost:8000/api/v1/metrics

monitor-flower: ## Open Flower dashboard
	@echo "$(BLUE)Opening Flower dashboard...$(NC)"
	@open http://localhost:5555 || xdg-open http://localhost:5555

monitor-kibana: ## Open Kibana dashboard
	@echo "$(BLUE)Opening Kibana dashboard...$(NC)"
	@open http://localhost:5601 || xdg-open http://localhost:5601

# ==============================================================================
# DEVELOPMENT
# ==============================================================================
dev: ## Start in development mode with hot-reload
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
	@echo "$(GREEN)✓ Development environment started!$(NC)"

dev-down: ## Stop development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# ==============================================================================
# QUICK START
# ==============================================================================
quickstart: ## Quick start: build, start, and initialize everything
	@echo "$(BLUE)Quick start: Setting up AR_AS Recommendation System...$(NC)"
	@make build
	@make up
	@echo "$(YELLOW)Waiting for services to be ready...$(NC)"
	@sleep 20
	@make migrate
	@make init-vectors
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  ✓ AR_AS Recommendation System is ready!$(NC)"
	@echo "$(GREEN)════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Access points:$(NC)"
	@echo "  API:     http://localhost:8000"
	@echo "  Docs:    http://localhost:8000/docs"
	@echo "  Flower:  http://localhost:5555"
	@echo "  Kibana:  http://localhost:5601"
	@echo ""
	@echo "$(YELLOW)Useful commands:$(NC)"
	@echo "  make logs       - View logs"
	@echo "  make status     - Check service status"
	@echo "  make health     - Check service health"
	@echo "  make down       - Stop all services"
	@echo ""

# ==============================================================================
# DOCUMENTATION
# ==============================================================================
docs: ## Open API documentation in browser
	@echo "$(BLUE)Opening API documentation...$(NC)"
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs

api-docs: docs ## Alias for docs
