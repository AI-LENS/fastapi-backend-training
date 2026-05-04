"""Domain exceptions. Routes never catch these — the global handler translates them."""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code: str = "domain_error"
    status_code: int = 500

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404


class ConflictError(DomainError):
    code = "conflict"
    status_code = 409


class ValidationError(DomainError):
    code = "validation_failed"
    status_code = 422


class Unauthorized(DomainError):
    code = "unauthorized"
    status_code = 401


class Forbidden(DomainError):
    code = "forbidden"
    status_code = 403


class ScreeningNotFound(NotFoundError):
    code = "screening_not_found"


class SiteNotFound(NotFoundError):
    code = "site_not_found"


class InvalidSite(ValidationError):
    code = "invalid_site"


class IneligibleScreening(ValidationError):
    code = "ineligible_screening"


class CannotDelete(ConflictError):
    code = "cannot_delete"


class AlreadyEnrolled(ConflictError):
    code = "already_enrolled"


class AlreadyDecided(ConflictError):
    code = "already_decided"


class InvalidCredentials(Unauthorized):
    code = "invalid_credentials"


class NoPipelineRunning(ConflictError):
    code = "no_pipeline_running"
