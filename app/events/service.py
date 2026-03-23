import uuid

from app.events.model import Event
from app.events.repository import EventRepository
from app.events.schemas import EventListResponse, EventResponse, FinishRequest, StartRequest


def _to_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        job_name=event.job_name,
        source=event.source,
        status=event.status,
        started_at=event.started_at,
        finished_at=event.finished_at,
        duration_ms=event.duration_ms,
        error_message=event.error_message,
        metadata=event.metadata_,
    )


async def start(repo: EventRepository, payload: StartRequest) -> EventResponse:
    """Registra el inicio de un job."""
    event = await repo.create(payload.job_name, payload.source, payload.metadata)
    return _to_response(event)


async def finish(
    repo: EventRepository,
    event_id: uuid.UUID,
    payload: FinishRequest,
) -> EventResponse | None:
    """
    Finaliza un evento calculando la duración automáticamente.
    Devuelve None si el evento no existe.
    """
    event = await repo.get(event_id)
    if not event:
        return None

    event = await repo.finish(event, payload.status, payload.error_message, payload.metadata)
    return _to_response(event)


async def get_one(repo: EventRepository, event_id: uuid.UUID) -> EventResponse | None:
    """Busca un evento por ID."""
    event = await repo.get(event_id)
    return _to_response(event) if event else None


async def get_list(
    repo: EventRepository,
    job_name: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> EventListResponse:
    """Lista eventos con filtros y paginación."""
    total, events = await repo.list(job_name, status, limit, offset)
    return EventListResponse(total=total, items=[_to_response(e) for e in events])


async def get_job_status(repo: EventRepository, job_name: str) -> EventResponse | None:
    """
    Devuelve el último evento registrado para un job.
    Útil para saber rápidamente si la última ejecución fue exitosa o falló.
    """
    event = await repo.get_last_by_job(job_name)
    return _to_response(event) if event else None