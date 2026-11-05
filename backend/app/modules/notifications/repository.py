"""Repository layer for persisting and querying NotificationDelivery entities."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.notifications.enums import NotificationDeliveryStatusEnum
from app.modules.notifications.models import NotificationDelivery


class NotificationRepository:
    """Handles PostgreSQL queries, uniqueness enforcement, and atomic status updates for notifications."""

    async def get_by_id(
        self,
        session: AsyncSession,
        delivery_id: uuid.UUID,
        load_relations: bool = False,
    ) -> NotificationDelivery | None:
        """Fetch a notification delivery by its unique primary key."""
        stmt = select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(NotificationDelivery.job),
                selectinload(NotificationDelivery.job_match),
                selectinload(NotificationDelivery.candidate_profile),
                selectinload(NotificationDelivery.tailored_resume),
            )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_by_job_and_recipient(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        recipient_email: str,
        load_relations: bool = False,
    ) -> NotificationDelivery | None:
        """Query for existing delivery record by candidate email and job ID (idempotency key)."""
        stmt = select(NotificationDelivery).where(
            NotificationDelivery.job_id == job_id,
            func.lower(NotificationDelivery.recipient_email) == recipient_email.lower().strip(),
        )
        if load_relations:
            stmt = stmt.options(
                selectinload(NotificationDelivery.job),
                selectinload(NotificationDelivery.job_match),
                selectinload(NotificationDelivery.candidate_profile),
                selectinload(NotificationDelivery.tailored_resume),
            )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_by_tailored_resume_id(
        self,
        session: AsyncSession,
        tailored_resume_id: uuid.UUID,
    ) -> NotificationDelivery | None:
        """Fetch notification associated with a tailored resume."""
        stmt = select(NotificationDelivery).where(
            NotificationDelivery.tailored_resume_id == tailored_resume_id
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def save(
        self,
        session: AsyncSession,
        delivery: NotificationDelivery,
    ) -> NotificationDelivery:
        """Persist new or modified notification delivery record."""
        session.add(delivery)
        await session.flush()
        return delivery

    async def list_deliveries(
        self,
        session: AsyncSession,
        candidate_profile_id: uuid.UUID | None = None,
        status: NotificationDeliveryStatusEnum | None = None,
        job_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[NotificationDelivery], int]:
        """Query paginated notification deliveries with optional status and candidate filters."""
        base_query = select(NotificationDelivery)
        count_query = select(func.count(NotificationDelivery.id))

        if candidate_profile_id is not None:
            base_query = base_query.where(
                NotificationDelivery.candidate_profile_id == candidate_profile_id
            )
            count_query = count_query.where(
                NotificationDelivery.candidate_profile_id == candidate_profile_id
            )

        if status is not None:
            base_query = base_query.where(NotificationDelivery.status == status)
            count_query = count_query.where(NotificationDelivery.status == status)

        if job_id is not None:
            base_query = base_query.where(NotificationDelivery.job_id == job_id)
            count_query = count_query.where(NotificationDelivery.job_id == job_id)

        # Count total matching records
        total_items = (await session.execute(count_query)).scalar_one()

        # Fetch page items ordered newest first
        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(NotificationDelivery.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(
                selectinload(NotificationDelivery.job),
                selectinload(NotificationDelivery.job_match),
            )
        )
        result = await session.execute(stmt)
        items = list(result.scalars().all())

        return items, total_items
