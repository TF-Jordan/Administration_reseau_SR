#!/usr/bin/env python3
"""
API Server Runner Script
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

from src.config import settings
from src.logging_config import configure_logging


def main():
    """Run the FastAPI server."""
    # Configure logging
    configure_logging()

    # Run server
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
