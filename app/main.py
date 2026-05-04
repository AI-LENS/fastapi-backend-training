"""Subject Enrollment Service — entry point.

Module 01: Hello FastAPI.

This file grows over the next few modules:
  - Module 02 adds Pydantic schemas (replace dicts with models)
  - Module 03 splits routes into APIRouters
  - Module 04 introduces the app factory + lifespan

For now, keep it tiny on purpose.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Subject Enrollment Service",
    description="Clinical trial enrollment training app",
    version="0.1.0",
)


@app.get("/")
def root():
    """Service banner — also acts as a basic liveness check."""
    return {
        "service": "Subject Enrollment Service",
        "version": "0.1.0",
        "status": "ok",
    }


# ─────────────────────────────────────────────────────────────
# YOUR EXERCISE GOES HERE.
#
# Add a GET /sites/{site_id} endpoint that returns:
#   {"site_id": "<echoed>", "name": "Example Hospital", "active": true}
#
# See docs/modules/01-hello-fastapi.mdx for the full task.
# Reveal the solution at docs/exercises/01-solution.mdx after you've tried.
# ─────────────────────────────────────────────────────────────
