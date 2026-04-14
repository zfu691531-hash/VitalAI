from fastapi import FastAPI

from VitalAI.interfaces.api.routers.health import router as health_router
from VitalAI.interfaces.api.routers.typed_flows import router as typed_flow_router


def init_http_interfaces(app: FastAPI) -> None:
    app.include_router(health_router, prefix="/vitalai", tags=["VitalAI"])
    app.include_router(typed_flow_router, prefix="/vitalai", tags=["VitalAI Typed Flows"])
