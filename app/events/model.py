import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nombre lógico del job — siempre el mismo para el mismo proceso
    job_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # De dónde se disparó: "cronjob", "celery", "django-view", etc.
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Estado: started | success | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Calculado automáticamente al finalizar
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Datos extra en formato libre — resultados, parámetros, contexto
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
