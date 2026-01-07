#!/usr/bin/env python3
"""
Main entry point for the Sentiment Recommendation System.
"""

import argparse
import sys

from src.logging_config import configure_logging


def run_api():
    """Start the FastAPI server."""
    import uvicorn
    from src.config import settings

    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


def run_worker():
    """Start Celery worker."""
    from src.modules.module3_orchestration.celery_app import celery_app

    celery_app.worker_main([
        "worker",
        "--loglevel=INFO",
        "--concurrency=4",
    ])


def run_beat():
    """Start Celery beat scheduler."""
    from src.modules.module3_orchestration.celery_app import celery_app

    celery_app.worker_main([
        "beat",
        "--loglevel=INFO",
    ])


def run_flower():
    """Start Flower monitoring."""
    from src.modules.module3_orchestration.celery_app import celery_app

    celery_app.worker_main([
        "flower",
        "--port=5555",
    ])


def init_db():
    """Initialize database tables."""
    import asyncio
    from src.database.connection import init_database

    asyncio.run(init_database())
    print("Database initialized successfully")


def init_vectors():
    """Initialize vector database."""
    import importlib.util
    from pathlib import Path

    # Charger le script directement depuis le fichier
    script_path = Path(__file__).parent / "scripts" / "init_vectors.py"
    spec = importlib.util.spec_from_file_location("init_vectors", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sentiment Recommendation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  api       Start the FastAPI server
  worker    Start Celery worker
  beat      Start Celery beat scheduler
  flower    Start Flower monitoring
  init-db   Initialize database tables
  init-vectors  Initialize vector database

Examples:
  python main.py api
  python main.py worker
  python main.py init-vectors --type all
        """,
    )

    parser.add_argument(
        "command",
        choices=["api", "worker", "beat", "flower", "init-db", "init-vectors"],
        help="Command to run",
    )

    args, remaining = parser.parse_known_args()

    # Configure logging
    configure_logging()

    # Run command
    if args.command == "api":
        run_api()
    elif args.command == "worker":
        run_worker()
    elif args.command == "beat":
        run_beat()
    elif args.command == "flower":
        run_flower()
    elif args.command == "init-db":
        init_db()
    elif args.command == "init-vectors":
        # Pass remaining args to init_vectors
        sys.argv = ["init_vectors.py"] + remaining
        init_vectors()


if __name__ == "__main__":
    main()
