# Event Tracker

Microservicio para trackear el estado de jobs, cronjobs y eventos de código.
Se comunica con cualquier proyecto via HTTP y expone un cliente pip instalable.

## Estructura
```
event-tracker/
├── app/                  ← microservicio FastAPI
│   ├── events/           ← dominio (model, repository, service, schemas)
│   ├── config.py         ← lee config.yaml
│   └── main.py           ← rutas y ciclo de vida
├── client/               ← paquete pip instalable en otros proyectos
│   ├── event_tracker/
│   │   ├── __init__.py
│   │   └── client.py
│   └── pyproject.toml
├── config.yaml.example   ← plantilla de configuración
└── requirements.txt
```

## Configuración
```bash
cp config.yaml.example config.yaml
```

Completar `config.yaml` con las credenciales reales:
```yaml
db:
  host: localhost
  name: event_tracker
  user: 
  passwd: 
  port: 5432
```

## Levantar en desarrollo
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```

Documentación interactiva: `http://127.0.0.1:8001/docs`

## Levantar en la VM como servicio

Crear el archivo `/etc/systemd/system/event-tracker.service`:
```ini
[Unit]
Description=Event Tracker
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/opt/event-tracker
ExecStart=/opt/event-tracker/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload
systemctl enable event-tracker
systemctl start event-tracker
```

## Instalar el cliente en otro proyecto

Desde la VM (recomendado):
```bash
pip install /opt/event-tracker/client
```

Desde GitHub:
```bash
pip install git+https://github.com/tu-org/event-tracker.git#subdirectory=client
```

En `requirements.txt` del proyecto:
```
event-tracker-client @ file:///opt/event-tracker/client
```

## Uso en Django

En `config.yaml` de Django agregar:
```yaml
event_tracker:
  url: http://127.0.0.1:8001
```

En `settings.py`:
```python
EVENT_TRACKER_URL = _config["event_tracker"]["url"]
```

En cualquier función que quieras trackear:
```python
from django.conf import settings
from event_tracker import track_job

@track_job("sync_users", source="cronjob", base_url=settings.EVENT_TRACKER_URL)
def handle(self, *args, **kwargs):
    # tu código sin cambios
    ...
```

## Endpoints

| Método | Path | Descripción |
|--------|------|-------------|
| `POST` | `/events/start` | Inicia un evento, devuelve `event_id` |
| `POST` | `/events/{event_id}/finish` | Finaliza un evento (success/failed) |
| `GET`  | `/events` | Lista eventos con filtros opcionales |
| `GET`  | `/events/{event_id}` | Obtiene un evento por ID |
| `GET`  | `/jobs/{job_name}/status` | Último estado de un job |
| `GET`  | `/health` | Health check |