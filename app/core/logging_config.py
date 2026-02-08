from __future__ import annotations

import logging
from logging.config import dictConfig

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    log_format = (
        "%(levelname)s %(asctime)s %(name)s %(message)s"
        if not settings.log_json
        else "%(message)s"
    )

    handlers: dict[str, dict[str, object]] = {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    }

    formatters: dict[str, dict[str, object]] = {
        "standard": {
            "format": log_format,
        }
    }

    if settings.log_json:
        formatters["standard"]["format"] = (
            '{"level":"%(levelname)s","time":"%(asctime)s","logger":"%(name)s","message":"%(message)s"}'
        )

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatters,
            "handlers": handlers,
            "root": {
                "level": settings.log_level,
                "handlers": ["default"],
            },
        }
    )

    logging.getLogger("uvicorn.error").setLevel(settings.log_level)
