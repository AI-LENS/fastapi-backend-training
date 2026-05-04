"""End-to-end integration tests."""
from __future__ import annotations

import asyncio

import pytest


VALID_SCREENING = {
    "site_id": "SITE-001",
    "candidate_initials": "AA",
    "age": 40,
    "sex": "F",
    "diagnosis": "Type 2 Diabetes",
    "medications": ["metformin"],
    "is_pregnant": False,
    "has_liver_disease": False,
    "in_other_trial": False,
}


@pytest.mark.asyncio
async def test_health_live(client):
    r = await client.get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_login_returns_tokens(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "pwd"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_login_failure(client):
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "WRONG"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_anonymous_cannot_list_screenings(client):
    r = await client.get("/api/v1/screenings")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_alice_can_submit_for_her_site(client, alice_auth):
    r = await client.post(
        "/api/v1/screenings",
        headers=alice_auth,
        json=VALID_SCREENING,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["site_id"] == "SITE-001"
    assert body["status"] == "submitted"


@pytest.mark.asyncio
async def test_alice_cannot_submit_for_another_site(client, alice_auth):
    r = await client.post(
        "/api/v1/screenings",
        headers=alice_auth,
        json={**VALID_SCREENING, "site_id": "SITE-002"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


@pytest.mark.asyncio
async def test_sponsor_cannot_submit(client, admin_auth):
    """Sponsor has admin override usually, but submit is strict-coordinator-only."""
    r = await client.post(
        "/api/v1/screenings",
        headers=admin_auth,
        json=VALID_SCREENING,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_object_level_isolation(client, alice_auth, bob_auth):
    """Bob's screening must not be visible to Alice."""
    # Bob submits at his site
    bob_post = await client.post(
        "/api/v1/screenings",
        headers=bob_auth,
        json={**VALID_SCREENING, "site_id": "SITE-002", "candidate_initials": "BB"},
    )
    assert bob_post.status_code == 201
    sid = bob_post.json()["id"]

    # Alice tries to read it — must get 404 (no info leak)
    r = await client.get(f"/api/v1/screenings/{sid}", headers=alice_auth)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_endpoint_requires_sponsor(client, alice_auth, admin_auth):
    r1 = await client.get("/api/v1/admin/jobs", headers=alice_auth)
    assert r1.status_code == 403

    r2 = await client.get("/api/v1/admin/jobs", headers=admin_auth)
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_validation_error_for_bad_body(client, alice_auth):
    r = await client.post(
        "/api/v1/screenings", headers=alice_auth, json={"site_id": "SITE-001"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_404_envelope_shape(client, alice_auth):
    r = await client.get(
        "/api/v1/screenings/00000000-0000-0000-0000-000000000000",
        headers=alice_auth,
    )
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "screening_not_found"
    assert body["error"]["message"]
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_full_flow_submit_to_eligible(client, alice_auth, session_factory):
    """End-to-end: submit → run pipeline directly → verify API returns updated state.

    The background-worker dispatcher is exercised by unit tests for the
    pipeline + the in-process runner; here we simulate its work synchronously
    so the test isn't racy.
    """
    from uuid import UUID

    from app.cache import screenings as screening_cache
    from app.pipelines.eligibility import run_pipeline
    from app.repositories import screening_repository as repo

    submit = await client.post(
        "/api/v1/screenings",
        headers=alice_auth,
        json={**VALID_SCREENING, "candidate_initials": "FF"},
    )
    assert submit.status_code == 201
    sid = UUID(submit.json()["id"])

    # Simulate the worker
    async with session_factory() as db:
        screening = await repo.get_by_id(db, sid)
        outcome = await run_pipeline(screening)
        await repo.update_status(
            db,
            screening,
            status="eligible" if outcome.eligible else "ineligible",
            eligibility_result="eligible" if outcome.eligible else "ineligible",
            failed_criteria=outcome.failed_criteria,
        )
        await db.commit()
    screening_cache.invalidate_screening(sid)

    r = await client.get(f"/api/v1/screenings/{sid}", headers=alice_auth)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "eligible"
    assert body["eligibility_result"] == "eligible"
    assert body["failed_criteria"] == []


@pytest.mark.asyncio
async def test_enroll_after_eligible(client, alice_auth, session_factory):
    """Enroll converts an eligible screening into an enrolled subject."""
    from uuid import UUID

    from app.cache import screenings as screening_cache
    from app.repositories import screening_repository as repo

    submit = await client.post(
        "/api/v1/screenings",
        headers=alice_auth,
        json={**VALID_SCREENING, "candidate_initials": "EN"},
    )
    sid = UUID(submit.json()["id"])

    async with session_factory() as db:
        screening = await repo.get_by_id(db, sid)
        await repo.update_status(
            db, screening, status="eligible", eligibility_result="eligible"
        )
        await db.commit()
    screening_cache.invalidate_screening(sid)

    r = await client.post(f"/api/v1/screenings/{sid}/enroll", headers=alice_auth)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "enrolled"
    assert body["subject_id"].startswith("S-")


@pytest.mark.asyncio
async def test_audit_records_submission(client, alice_auth, admin_auth):
    submit = await client.post(
        "/api/v1/screenings",
        headers=alice_auth,
        json={**VALID_SCREENING, "candidate_initials": "AU"},
    )
    sid = submit.json()["id"]

    audit = await client.get(
        "/api/v1/admin/audit?action=screening.submitted",
        headers=admin_auth,
    )
    assert audit.status_code == 200
    entries = audit.json()
    assert any(e["resource_id"] == sid for e in entries)


@pytest.mark.asyncio
async def test_audit_chain_intact(client, alice_auth, admin_auth):
    # Generate a few audit-worthy actions
    for i in range(3):
        await client.post(
            "/api/v1/screenings",
            headers=alice_auth,
            json={**VALID_SCREENING, "candidate_initials": f"C{i}"},
        )

    r = await client.post("/api/v1/admin/audit/verify", headers=admin_auth)
    assert r.status_code == 200
    body = r.json()
    assert body["chain_intact"] is True
    assert body["broken_at_seq"] is None


@pytest.mark.asyncio
async def test_idempotency_key_dedupes_submit(client, alice_auth):
    headers = {**alice_auth, "Idempotency-Key": "test-key-123"}
    body = {**VALID_SCREENING, "candidate_initials": "II"}
    r1 = await client.post("/api/v1/screenings", headers=headers, json=body)
    r2 = await client.post("/api/v1/screenings", headers=headers, json=body)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_x_request_id_echoed(client, alice_auth):
    r = await client.get(
        "/api/v1/screenings",
        headers={**alice_auth, "X-Request-ID": "test-rid-abc"},
    )
    assert r.headers.get("x-request-id") == "test-rid-abc"
