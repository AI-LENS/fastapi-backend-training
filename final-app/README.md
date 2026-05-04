# Final App — Working Reference

This is the **complete working reference** for the training. It implements every layer and pattern taught across the 36 modules.

Run it. Watch it work. Then close it and rebuild your version from scratch by following the docs.

## What's in here

| Layer | Files | Module(s) |
|---|---|---|
| Routers | `app/routers/{auth,screenings,sites,admin,health,metrics}.py` | 03, 16, 17, 26 |
| Schemas | `app/schemas/{screening,site,auth,audit}.py` | 02 |
| Services | `app/services/{auth,screening,permission,progress_manager}.py` | 09, 16, 17b, 18b, 15 |
| Repositories | `app/repositories/{screening,site,user,audit,job_record,outbox}_repository.py` | 08, 17c, 13b, 28 |
| Models | `app/models/{base,screening,site,user,audit_log,job_record,idempotency,outbox}.py` | 06, 16, 17c, 13b, 27, 28 |
| Workers | `app/workers/{task_runner,outbox_drainer}.py` | 13, 28 |
| Pipelines | `app/pipelines/eligibility/{stages,orchestrator}.py` | 14 |
| Middleware | `app/middleware/{request_id,logging,slow,metrics}.py` | 18, 21 |
| Cache | `app/cache/{sites,screenings}.py` | 19 |
| Common | `app/common/{pagination,idempotency}.py` | 27 |
| DB / UoW | `app/database.py`, `app/db/unit_of_work.py` | 05, 10b |
| Core | `app/core/{logging,metrics}.py` | 20, 21 |
| Config | `app/config.py`, `.env.example` | 04, 24 |
| Tests | `tests/unit/`, `tests/integration/` | 22, 23 |

## Quickstart

This project uses [**uv**](https://docs.astral.sh/uv/) — Astral's fast Python package manager. Install it once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv  (macOS)
```

Then:

```bash
cd final-app

# Install dependencies into a fresh .venv (uv handles Python + venv + deps)
uv sync --group dev

# Run the server (uv run picks up the venv automatically — no activation needed)
ENROLLMENT_SECRET_KEY=$(openssl rand -hex 32) uv run uvicorn app.main:app --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

## Try the live API

```bash
# 1. Login as Alice (coordinator at SITE-001)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"alice"}' | jq -r .access_token)

# 2. Submit a screening
SID=$(curl -s -X POST http://localhost:8000/api/v1/screenings \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"site_id":"SITE-001","candidate_initials":"AB","age":40,"sex":"F",
       "diagnosis":"Type 2 Diabetes","medications":["metformin"],
       "is_pregnant":false,"has_liver_disease":false,"in_other_trial":false}' \
  | jq -r .id)

# 3. Watch the outbox drainer kick in — status moves submitted → reviewing → eligible
curl -s http://localhost:8000/api/v1/screenings/$SID -H "Authorization: Bearer $TOKEN" | jq .status
sleep 2
curl -s http://localhost:8000/api/v1/screenings/$SID -H "Authorization: Bearer $TOKEN" | jq .status

# 4. Enroll the eligible screening
curl -s -X POST http://localhost:8000/api/v1/screenings/$SID/enroll \
  -H "Authorization: Bearer $TOKEN" | jq .subject_id

# 5. Bob (different site) can't see it
BOB=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"bob@example.com","password":"bob"}' | jq -r .access_token)
curl -i http://localhost:8000/api/v1/screenings/$SID -H "Authorization: Bearer $BOB"
# 404 — object-level auth in action
```

## Default users (seeded on first start)

| Email | Password | Role | Site |
|---|---|---|---|
| `admin@example.com` | `admin` | sponsor | (all) |
| `alice@example.com` | `alice` | coordinator | SITE-001 |
| `bob@example.com` | `bob` | coordinator | SITE-002 |

## Run the tests

```bash
uv run pytest tests/ -v
```

You should see **44 tests pass**: 27 unit + 17 integration covering every layer.

## Useful endpoints

| URL | What |
|---|---|
| `/` | Service banner |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/metrics` | Prometheus metrics |
| `/api/v1/health/live` | Liveness probe |
| `/api/v1/health/ready` | Readiness probe |
| `/api/v1/health/startup` | Startup probe |
| `/api/v1/auth/login` | Get a JWT |
| `/api/v1/screenings` | List/create screenings |
| `/api/v1/screenings/{id}/progress` | SSE progress stream |
| `/api/v1/admin/jobs` | DLQ view (sponsor only) |
| `/api/v1/admin/audit` | Audit log query (sponsor only) |
| `/api/v1/admin/audit/verify` | Verify audit hash chain |

## Architecture at a glance

```
HTTP
  │
  ▼
[CORS · MetricsMiddleware · SlowRequestMiddleware · AccessLogMiddleware · RequestIDMiddleware]
  │
  ▼
[FastAPI Router]
  │ require_role / get_current_user
  ▼
[Service]
  │ async with UoW:
  │   permission_service.ensure_*  (audit on deny)
  │   repo.* (no commit)
  │   audit_repository.append      (hash-chained)
  │   outbox.append                 (publish-after-commit)
  ▼
[Database (SQLite via aiosqlite)]
  │
  └──> Outbox Drainer ──> BackgroundTaskRunner ──> Pipeline (6 stages)
                                                       │
                                                       ▼
                                          ProgressManager (SSE)
```

## Differences from the docs (deliberate simplifications)

- **No Alembic** — uses `Base.metadata.create_all` on startup. Module 07 teaches Alembic, but for a single-command runnable reference, autocreate is simpler.
- **No JobRecord wrapping in the dispatcher** — Module 13b's full retry/DLQ machinery is taught and the model exists, but the running dispatcher uses a simpler `BackgroundTaskRunner.submit`. The DLQ admin endpoint is wired and queryable.
- **No Redis** — slowapi rate limit and cachetools cache run in-process. Module 19 explains the Redis upgrade path.
- **No Celery / Arq** — the in-process runner + outbox is enough at this scale. Module 28 teaches the upgrade.
- **No CI/CD or external monitoring** — Modules 26b, 26c teach these as ops concerns; they don't need to live inside the runtime app.

## Rebuild from scratch

Once you've explored, the docs in `../docs/` walk you through building this same app **from a single hello-world endpoint to here**, one concept at a time. Start at <http://localhost:3000/modules/01-hello-fastapi> after `mintlify dev` (from `../docs/`).

You can use this folder as a reference when you get stuck — but resist peeking until you've tried each exercise.
