import logging

import structlog

from app.core.config import settings


def setup_logging():
    renderer = (
        structlog.dev.ConsoleRenderer()
        if settings.ENV == "development"
        else structlog.processors.JSONRenderer()
    )

    processors = [  # type: ignore
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        renderer,
    ]

    structlog.configure(
        processors=processors,  # type: ignore
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # Make standard logging follow the same setup
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO if settings.ENV != "development" else logging.DEBUG,
    )
