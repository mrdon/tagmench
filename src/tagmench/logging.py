import logging
import logging.config
import sys
from datetime import datetime

from pythonjsonlogger.jsonlogger import JsonFormatter


def init_logging():
    formatter = {
        "class": "tagmench.logging.CustomJsonFormatter",
        "format": "%(message)s",
    }

    log_level = "INFO"
    logging_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": formatter},
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {"handlers": ["console"], "level": log_level, "propagate": True},
            "gino.engine": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(logging_dict)


class CustomJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record: logging.LogRecord, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get("timestamp"):
            # this doesn't use record.created, so it is slightly off
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            log_record["timestamp"] = now

        level = record.levelname
        if log_record.get("level"):
            level = log_record["level"].upper()

        log_record["level"] = level

        # useful for comparison queries
        log_record["level_val"] = getattr(logging, level)

        log_record["service"] = "tagmench"
