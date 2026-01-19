#!/usr/bin/env python3
"""
Celery Worker Runner Script
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.module3_orchestration.celery_app import celery_app
from src.logging_config import configure_logging


def main():
    """Run Celery worker."""
    configure_logging()

    celery_app.worker_main([
        "worker",
        "--loglevel=INFO",
        "--concurrency=4",
        "-Q", "default,recommendations,sentiment,vectorization",
    ])


if __name__ == "__main__":
    main()
