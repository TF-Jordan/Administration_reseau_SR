"""
Celery application configuration.
Handles asynchronous task processing.
"""

import logging
from celery import Celery

from src.config import settings
from src.utils.context import set_correlation_id, clear_all_context, get_correlation_id

logger = logging.getLogger(__name__)

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
    """
    Base task with error handling, logging, and correlation ID propagation.

    Automatically extracts and sets correlation_id from task kwargs,
    enabling request tracing across async operations.
    """

    abstract = True
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def __call__(self, *args, **kwargs):
        """
        Execute task with correlation ID context.

        Extracts correlation_id from kwargs and sets it in context
        before task execution, then cleans up after.
        """
        # Extract correlation ID from kwargs
        correlation_id = kwargs.get('correlation_id')

        try:
            # Set correlation ID in context if provided
            if correlation_id:
                set_correlation_id(correlation_id)
                logger.debug(
                    f"Task {self.name} starting with correlation_id: {correlation_id}",
                    extra={"task_id": self.request.id}
                )

            # Execute the task
            return super().__call__(*args, **kwargs)

        finally:
            # Clean up context after task execution
            clear_all_context()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure with correlation ID logging."""
        # Extract correlation_id from kwargs for logging
        correlation_id = kwargs.get('correlation_id')

        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            extra={
                "event": "celery_task_failed",
                "metric_type": "celery_task",
                "task_name": self.name,
                "task_id": task_id,
                "status": "failure",
                "exception": str(exc),
                "exception_type": type(exc).__name__,
                "correlation_id": correlation_id,
                "retry_count": self.request.retries,
            }
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success with correlation ID logging."""
        # Extract correlation_id from kwargs for logging
        correlation_id = kwargs.get('correlation_id')

        logger.info(
            f"Task {self.name}[{task_id}] completed successfully",
            extra={
                "event": "celery_task_completed",
                "metric_type": "celery_task",
                "task_name": self.name,
                "task_id": task_id,
                "status": "success",
                "correlation_id": correlation_id,
                "retry_count": self.request.retries,
            }
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry with correlation ID logging."""
        correlation_id = kwargs.get('correlation_id')

        logger.warning(
            f"Task {self.name}[{task_id}] retrying (attempt {self.request.retries + 1}): {exc}",
            extra={
                "event": "celery_task_retry",
                "metric_type": "celery_task",
                "task_name": self.name,
                "task_id": task_id,
                "status": "retry",
                "exception": str(exc),
                "correlation_id": correlation_id,
                "retry_count": self.request.retries,
            }
        )
