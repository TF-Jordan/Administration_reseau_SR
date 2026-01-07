"""
Celery application configuration.
Handles asynchronous task processing.
"""

from celery import Celery

from src.config import settings

# Initialize Celery app
celery_app = Celery(
    "recommendation_system",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=[
        "src.modules.module3_orchestration.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,

    # Retry settings
    task_default_retry_delay=30,
    task_max_retries=3,

    # Result settings
    result_expires=3600,

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_concurrency=4,

    # Queue settings
    task_default_queue="default",
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
        "recommendations": {
            "exchange": "recommendations",
            "routing_key": "recommendations",
        },
        "sentiment": {
            "exchange": "sentiment",
            "routing_key": "sentiment",
        },
        "vectorization": {
            "exchange": "vectorization",
            "routing_key": "vectorization",
        },
    },

    # Task routes
    task_routes={
        "src.modules.module3_orchestration.tasks.process_recommendation_task": {
            "queue": "recommendations"
        },
        "src.modules.module3_orchestration.tasks.process_sentiment_task": {
            "queue": "sentiment"
        },
        "src.modules.module3_orchestration.tasks.vectorize_products_task": {
            "queue": "vectorization"
        },
    },

    # Beat schedule (for periodic tasks if needed)
    beat_schedule={
        "health-check-every-5-minutes": {
            "task": "src.modules.module3_orchestration.tasks.health_check_task",
            "schedule": 300.0,  # 5 minutes
        },
    },
)


# Task base class with custom configurations
class BaseTask(celery_app.Task):
    """Base task with error handling and logging."""

    abstract = True
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            extra={
                "task_id": task_id,
                "args": args,
                "kwargs": kwargs,
                "exception": str(exc),
            }
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Task {self.name}[{task_id}] completed successfully",
            extra={"task_id": task_id}
        )
