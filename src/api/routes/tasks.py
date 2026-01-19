"""
Async Task Management API endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import TaskStatusResponse, ErrorResponse
from src.modules.module3_orchestration.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get task status",
    description="Check the status of an async task by its ID.",
)
async def get_task_status(task_id: str):
    """
    Get the status of an async task.

    Returns:
    - PENDING: Task is waiting to be executed
    - STARTED: Task has been started
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed
    - RETRY: Task is being retried
    """
    logger.info(f"Task status request: {task_id}")

    try:
        orchestrator = get_orchestrator()
        status_info = orchestrator.get_task_status(task_id)

        if status_info["status"] == "PENDING":
            # Could be pending or non-existent
            pass

        return TaskStatusResponse(**status_info)

    except Exception as e:
        logger.error(f"Task status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete(
    "/{task_id}",
    summary="Revoke task",
    description="Attempt to revoke/cancel a pending task.",
)
async def revoke_task(task_id: str):
    """
    Attempt to revoke a pending task.

    Note: Tasks that are already running cannot be revoked.
    """
    from celery.result import AsyncResult
    from src.modules.module3_orchestration.celery_app import celery_app

    logger.info(f"Task revoke request: {task_id}")

    try:
        result = AsyncResult(task_id, app=celery_app)

        if result.ready():
            return {
                "task_id": task_id,
                "message": "Task already completed",
                "revoked": False,
            }

        result.revoke(terminate=True)

        return {
            "task_id": task_id,
            "message": "Task revoke signal sent",
            "revoked": True,
        }

    except Exception as e:
        logger.error(f"Task revoke error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{task_id}/result",
    summary="Get task result",
    description="Get the result of a completed task.",
)
async def get_task_result(task_id: str):
    """
    Get the result of a completed task.

    Raises 404 if task is not found or not ready.
    """
    from celery.result import AsyncResult
    from src.modules.module3_orchestration.celery_app import celery_app

    logger.info(f"Task result request: {task_id}")

    try:
        result = AsyncResult(task_id, app=celery_app)

        if not result.ready():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not yet completed",
            )

        if result.failed():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Task failed: {str(result.result)}",
            )

        return {
            "task_id": task_id,
            "status": "SUCCESS",
            "result": result.get(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task result error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
