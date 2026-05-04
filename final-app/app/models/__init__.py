"""Importing this package registers every model with the metadata.

Used by `Base.metadata.create_all` and Alembic autogenerate.
"""
from app.models.base import Base
from app.models import (  # noqa: F401  side-effect imports
    audit_log,
    idempotency,
    job_record,
    outbox,
    screening,
    site,
    user,
)

__all__ = ["Base"]
