import logging
import os
from typing import Any

from hypercorn.config import SECONDS
from hypercorn.logging import AccessLogAtoms
from hypercorn.logging import Logger

# import datadog

env = os.getenv("ENV", "production")

use_reloader = True if env == "development" else False

port = os.getenv("PORT", 8080)
bind = f"0.0.0.0:{port}"
keep_alive_timeout = 60 * SECONDS

workers = 1

# datadog.initialize(
#    statsd_host=os.getenv("STATSD_HOST", "dd-agent"),
#    statsd_port=os.getenv("STATSD_PORT", "8125"),
# )


class AccessLogger(logging.Logger):
    def __init__(self, *_, **__) -> None:
        self.logger = logging.getLogger("hypercorn.access")

    def info(self, message: str, data: AccessLogAtoms) -> None:

        if data["U"] in {"/health", "/health/"}:
            return

        request_id = data.get("x-request-id", "")

        method = data.get("m")
        duration = data.get("D")
        data = {
            "method": method,
            "status": data.get("s"),
            "path": data.get("U"),
            "query": data.get("q"),
            "duration": duration,
            "request_id": request_id,
        }

        self.logger.info(
            f'{data["method"]} {data["path"]} - {data["status"]}', extra=data
        )

    #       datadog.statsd.timing(
    #           "hypercorn.request",
    #           duration,
    #           tags=[
    #               f"method:{method}",
    #               f"status:{response['status']}",
    #               "service:tagmench",
    #           ],
    #       )

    def __getattr__(self, name: str) -> Any:
        if self.logger is None:
            return lambda *_: None
        else:
            return getattr(self.logger, name)


accesslog = AccessLogger()
errorlog = logging.getLogger("hypercorn.error")
