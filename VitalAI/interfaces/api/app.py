from fastapi import FastAPI

from VitalAI.interfaces.api.routers.agents import router as agents_router
from VitalAI.interfaces.api.routers.health import router as health_router
from VitalAI.interfaces.api.routers.interactions import router as interactions_router
from VitalAI.interfaces.api.routers.typed_flows import router as typed_flow_router


def init_http_interfaces(app: FastAPI) -> None:
    app.include_router(agents_router, prefix="/vitalai", tags=["VitalAI Agents"])
    app.include_router(health_router, prefix="/vitalai", tags=["VitalAI"])
    app.include_router(interactions_router, prefix="/vitalai", tags=["VitalAI Interactions"])
    app.include_router(typed_flow_router, prefix="/vitalai", tags=["VitalAI Typed Flows"])
