import logging

from fastapi import FastAPI

from Base.Config.logConfig import setup_logging
from VitalAI.interfaces.api.app import init_http_interfaces
from VitalAI.interfaces.web.bootstrap import init_web_interfaces

setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    logger.info("Starting VitalAI module")
    app = FastAPI(title="VitalAI")
    init_web_interfaces(app=app)
    init_http_interfaces(app=app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="127.0.0.1", port=8124)
