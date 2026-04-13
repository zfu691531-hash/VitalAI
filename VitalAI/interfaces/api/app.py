from fastapi import FastAPI

from VitalAI.interfaces.api.routers.health import router as health_router


def init_http_interfaces(app: FastAPI) -> None:
    app.include_router(health_router, prefix="/vitalai", tags=["VitalAI"])

