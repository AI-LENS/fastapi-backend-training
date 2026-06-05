"""Application logging configuration (Module 20)."""
from __future__ import annotations

import logging


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(message)s",
        handlers=[
            logging.FileHandler("app.log", encoding="utf-8"),
            # logging.StreamHandler(),
        ],
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name)
