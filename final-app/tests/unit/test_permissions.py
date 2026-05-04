"""Unit tests for permission policies."""
from __future__ import annotations

from types import SimpleNamespace

from app.services.permission_service import (
    _can_access_screening,
    _can_modify_screening,
    _can_view_audit_log,
)


def _user(**fields):
    defaults = {"id": "u1", "role": "coordinator", "site_id": "SITE-001"}
    return SimpleNamespace(**{**defaults, **fields})


def _screening(site_id="SITE-001"):
    return SimpleNamespace(id="s1", site_id=site_id)


def test_sponsor_sees_all():
    assert _can_access_screening(_user(role="sponsor", site_id=None), _screening("SITE-002")) is True


def test_coordinator_sees_own_site():
    assert _can_access_screening(_user(site_id="SITE-001"), _screening("SITE-001")) is True


def test_coordinator_blocked_from_other_site():
    assert _can_access_screening(_user(site_id="SITE-001"), _screening("SITE-002")) is False


def test_sponsor_cannot_modify():
    assert _can_modify_screening(_user(role="sponsor", site_id=None), _screening()) is False


def test_coordinator_modifies_own_site():
    assert _can_modify_screening(_user(site_id="SITE-001"), _screening("SITE-001")) is True


def test_only_sponsor_views_audit():
    assert _can_view_audit_log(_user(role="sponsor")) is True
    assert _can_view_audit_log(_user(role="coordinator")) is False
