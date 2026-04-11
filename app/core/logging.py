import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(settings.APP_NAME)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %Z"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logging()


def log_with_context(logger: logging.Logger, level: int, message: str, **kwargs: Any) -> None:
    context_parts = [f"{k}={v}" for k, v in kwargs.items() if v is not None]
    full_message = f"{message} | {', '.join(context_parts)}" if context_parts else message
    logger.log(level, full_message)