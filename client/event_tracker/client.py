import functools
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Generator

import httpx

logger = logging.getLogger("event_tracker")


class EventTrackerClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 5.0,
        raise_on_error: bool = False,
    ):
        """
        Args:
            base_url: URL del microservicio.
                      Si no se pasa, lee EVENT_TRACKER_URL del entorno.
                      Default: http://127.0.0.1:8001
            timeout: Timeout en segundos. Bajo a propósito — el tracker
                     no debe ralentizar tu app.
            raise_on_error: Si True, propaga errores del tracker.
                            Si False (default), loguea y continúa.
        """
        self.base_url = (
            base_url
            or os.getenv("EVENT_TRACKER_URL", "http://127.0.0.1:8001")
        ).rstrip("/")
        self.timeout = timeout
        self.raise_on_error = raise_on_error
        self._client: httpx.Client | None = None

    # ── HTTP lifecycle ─────────────────────────────────────

    def __enter__(self) -> "EventTrackerClient":
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        return self

    def __exit__(self, *_) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _post(self, path: str, json: dict) -> dict | None:
        """HTTP POST — nunca revienta el proceso principal."""
        owned = self._client is None
        client = self._client or httpx.Client(base_url=self.base_url, timeout=self.timeout)
        try:
            resp = client.post(path, json=json)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            msg = f"[event_tracker] Error en POST {path}: {exc}"
            if self.raise_on_error:
                raise RuntimeError(msg) from exc
            logger.warning(msg)
            return None
        finally:
            if owned:
                client.close()

    # ── API pública ────────────────────────────────────────

    def start(
        self,
        job_name: str,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Inicia un evento. Devuelve el event_id para pasarle a finish()."""
        result = self._post("/events/start", {
            "job_name": job_name,
            "source": source,
            "metadata": metadata,
        })
        return result["id"] if result else None

    def finish(
        self,
        event_id: str | None,
        success: bool,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Finaliza un evento con éxito o fallo."""
        if not event_id:
            return
        self._post(f"/events/{event_id}/finish", {
            "status": "success" if success else "failed",
            "error_message": error,
            "metadata": metadata,
        })

    # ── Context manager ────────────────────────────────────

    @contextmanager
    def track(
        self,
        job_name: str,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Generator[None, None, None]:
        """Trackea automáticamente inicio, fin y errores."""
        event_id = self.start(job_name, source=source, metadata=metadata)
        try:
            yield
            self.finish(event_id, success=True)
        except Exception as exc:
            self.finish(event_id, success=False, error=str(exc))
            raise


# ── Decoradores ────────────────────────────────────────────

def track_job(
    job_name: str,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
    base_url: str | None = None,
):
    """Decorador para funciones síncronas."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = EventTrackerClient(base_url=base_url)
            event_id = client.start(job_name, source=source, metadata=metadata)
            try:
                result = func(*args, **kwargs)
                # Si la función retorna un dict, se guarda como metadata del evento
                extra = result if isinstance(result, dict) else None
                client.finish(event_id, success=True, metadata=extra)
                return result
            except Exception as exc:
                client.finish(event_id, success=False, error=str(exc))
                raise
        return wrapper
    return decorator


def track_job_async(
    job_name: str,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
    base_url: str | None = None,
):
    """Decorador para funciones async."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            url = (base_url or os.getenv("EVENT_TRACKER_URL", "http://127.0.0.1:8001")).rstrip("/")
            event_id: str | None = None

            async with httpx.AsyncClient(base_url=url, timeout=5.0) as http:
                try:
                    r = await http.post("/events/start", json={
                        "job_name": job_name,
                        "source": source,
                        "metadata": metadata,
                    })
                    r.raise_for_status()
                    event_id = r.json()["id"]
                except Exception as e:
                    logger.warning(f"[event_tracker] start error: {e}")

                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    try:
                        if event_id:
                            await http.post(f"/events/{event_id}/finish", json={
                                "status": "failed",
                                "error_message": str(exc),
                            })
                    except Exception as e:
                        logger.warning(f"[event_tracker] finish error: {e}")
                    raise

                try:
                    if event_id:
                        await http.post(f"/events/{event_id}/finish", json={"status": "success"})
                except Exception as e:
                    logger.warning(f"[event_tracker] finish error: {e}")

                return result
        return wrapper
    return decorator