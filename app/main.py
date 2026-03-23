import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.events import service
from app.events.model import Base
from app.events.repository import EventRepository
from app.events.schemas import EventListResponse, EventResponse, FinishRequest, StartRequest

# ── Base de datos ──────────────────────────────────────────

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# ── Ciclo de vida de la app ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Event Tracker", lifespan=lifespan)


# ── Dependencias ───────────────────────────────────────────

def get_repo(db: AsyncSession = Depends(get_db)) -> EventRepository:
    return EventRepository(db)


# ── Rutas ──────────────────────────────────────────────────

@app.post("/events/start", response_model=EventResponse, status_code=201)
async def start_event(
    payload: StartRequest,
    repo: EventRepository = Depends(get_repo),
):
    """Registra el inicio de un job. Devuelve el event_id para llamar a /finish."""
    return await service.start(repo, payload)


@app.post("/events/{event_id}/finish", response_model=EventResponse)
async def finish_event(
    event_id: uuid.UUID,
    payload: FinishRequest,
    repo: EventRepository = Depends(get_repo),
):
    """Finaliza un evento con success o failed. Calcula la duración automáticamente."""
    event = await service.finish(repo, event_id, payload)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


@app.get("/events", response_model=EventListResponse)
async def list_events(
    job_name: str | None = Query(None),
    status: str | None = Query(None, pattern="^(started|success|failed)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: EventRepository = Depends(get_repo),
):
    """Lista eventos con filtros opcionales. Paginado."""
    return await service.get_list(repo, job_name, status, limit, offset)


@app.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    repo: EventRepository = Depends(get_repo),
):
    """Obtiene un evento por ID."""
    event = await service.get_one(repo, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


@app.get("/jobs/{job_name}/status", response_model=EventResponse)
async def job_status(
    job_name: str,
    repo: EventRepository = Depends(get_repo),
):
    """Último evento registrado para un job — directo desde Postgres."""
    event = await service.get_job_status(repo, job_name)
    if not event:
        raise HTTPException(status_code=404, detail=f"No hay registros para el job '{job_name}'")
    return event


@app.get("/health")
async def health():
    return {"status": "ok"}