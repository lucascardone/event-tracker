import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.model import Event


class EventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, job_name: str, source: str | None, metadata: dict | None) -> Event:
        """Crea un nuevo evento con estado 'started'."""
        event = Event(
            job_name=job_name,
            source=source,
            metadata_=metadata,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get(self, event_id: uuid.UUID) -> Event | None:
        """Busca un evento por su ID. Devuelve None si no existe."""
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def get_last_by_job(self, job_name: str) -> Event | None:
        """Devuelve el último evento registrado para un job, ordenado por fecha de inicio."""
        result = await self.db.execute(
            select(Event)
            .where(Event.job_name == job_name)
            .order_by(Event.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def finish(self, event: Event, status: str, error_message: str | None, metadata: dict | None) -> Event:
        """
        Finaliza un evento calculando la duración automáticamente.
        Si ya había metadata, la mergea con la nueva.
        """
        finished_at = datetime.now(timezone.utc)
        started_at = (
            event.started_at.replace(tzinfo=timezone.utc)
            if event.started_at.tzinfo is None
            else event.started_at
        )

        event.status = status
        event.finished_at = finished_at
        event.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        event.error_message = error_message

        if metadata:
            event.metadata_ = {**(event.metadata_ or {}), **metadata}

        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def list(
        self,
        job_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[Event]]:
        """
        Lista eventos con filtros opcionales.
        Devuelve una tupla (total, items) para facilitar la paginación.
        """
        query = select(Event)
        count_query = select(func.count()).select_from(Event)

        if job_name:
            query = query.where(Event.job_name == job_name)
            count_query = count_query.where(Event.job_name == job_name)

        if status:
            query = query.where(Event.status == status)
            count_query = count_query.where(Event.status == status)

        query = query.order_by(Event.started_at.desc()).limit(limit).offset(offset)

        total = (await self.db.execute(count_query)).scalar_one()
        events = (await self.db.execute(query)).scalars().all()
        return total, list(events)