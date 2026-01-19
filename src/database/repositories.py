"""
Repository pattern implementation for database operations.
Provides clean abstraction layer for data access.
"""

from typing import List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .models import Base, Vehicle, Personne, Comment

T = TypeVar("T", bound=Base)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[T]):
        self.model = model

    async def get_by_id(
        self, session: AsyncSession, id_value: UUID
    ) -> Optional[T]:
        """Get entity by primary key."""
        result = await session.execute(
            select(self.model).where(self.model.id == id_value)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get all entities with pagination."""
        result = await session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, session: AsyncSession, entity: T) -> T:
        """Create new entity."""
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def delete(self, session: AsyncSession, entity: T) -> bool:
        """Delete entity."""
        await session.delete(entity)
        await session.flush()
        return True


class VehicleRepository(BaseRepository):
    """Repository for Vehicle operations."""

    def __init__(self):
        super().__init__(Vehicle)

    async def get_by_id(
        self, session: AsyncSession, vehicle_id: UUID
    ) -> Optional[Vehicle]:
        """Get vehicle by ID."""
        result = await session.execute(
            select(Vehicle).where(Vehicle.vehicle_id == vehicle_id)
        )
        return result.scalar_one_or_none()

    async def get_available(
        self, session: AsyncSession, limit: int = 100
    ) -> List[Vehicle]:
        """Get all available vehicles."""
        result = await session.execute(
            select(Vehicle)
            .where(Vehicle.disponible == True)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_location(
        self, session: AsyncSession, localisation: str
    ) -> List[Vehicle]:
        """Get vehicles by location."""
        result = await session.execute(
            select(Vehicle).where(
                Vehicle.localisation.ilike(f"%{localisation}%")
            )
        )
        return list(result.scalars().all())

    async def get_by_brand(
        self, session: AsyncSession, brand: str
    ) -> List[Vehicle]:
        """Get vehicles by brand."""
        result = await session.execute(
            select(Vehicle).where(Vehicle.brand.ilike(f"%{brand}%"))
        )
        return list(result.scalars().all())

    async def get_all_for_vectorization(
        self, session: AsyncSession
    ) -> List[Vehicle]:
        """Get all vehicles for initial vectorization."""
        result = await session.execute(select(Vehicle))
        return list(result.scalars().all())

    async def update_availability(
        self, session: AsyncSession, vehicle_id: UUID, disponible: bool
    ) -> bool:
        """Update vehicle availability."""
        await session.execute(
            update(Vehicle)
            .where(Vehicle.vehicle_id == vehicle_id)
            .values(disponible=disponible)
        )
        await session.flush()
        return True

    def get_by_id_sync(self, session: Session, vehicle_id: UUID) -> Optional[Vehicle]:
        """Sync version for Celery tasks."""
        result = session.execute(
            select(Vehicle).where(Vehicle.vehicle_id == vehicle_id)
        )
        return result.scalar_one_or_none()

    def get_all_sync(self, session: Session) -> List[Vehicle]:
        """Sync version for getting all vehicles."""
        result = session.execute(select(Vehicle))
        return list(result.scalars().all())


class CommentRepository(BaseRepository):
    """Repository for Comment operations."""

    def __init__(self):
        super().__init__(Comment)

    async def get_by_product(
        self, session: AsyncSession, product_id: str, product_type: str
    ) -> List[Comment]:
        """Get all comments for a product."""
        result = await session.execute(
            select(Comment)
            .where(Comment.product_id == product_id)
            .where(Comment.product_type == product_type)
            .order_by(Comment.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_client(
        self, session: AsyncSession, client_id: str
    ) -> List[Comment]:
        """Get all comments by a client."""
        result = await session.execute(
            select(Comment)
            .where(Comment.client_id == client_id)
            .order_by(Comment.created_at.desc())
        )
        return list(result.scalars().all())


# Repository instances
vehicle_repository = VehicleRepository()
comment_repository = CommentRepository()
