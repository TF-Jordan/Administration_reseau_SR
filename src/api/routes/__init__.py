from fastapi import APIRouter

from .recommendations import router as recommendations_router
from .sentiment import router as sentiment_router
from .tasks import router as tasks_router
from .health import router as health_router
from .admin import router as admin_router

api_router = APIRouter()

api_router.include_router(
    recommendations_router,
    prefix="/recommendations",
    tags=["Recommendations"],
)

api_router.include_router(
    sentiment_router,
    prefix="/sentiment",
    tags=["Sentiment Analysis"],
)

api_router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["Async Tasks"],
)

api_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Administration"],
)
