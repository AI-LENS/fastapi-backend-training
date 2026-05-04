# Backend Training — Subject Enrollment Service

Learn production FastAPI architecture by building a clinical-trial **Subject Enrollment Service**, one concept at a time. Documentation lives in a Mintlify site under `docs/` with interactive exercises, Q&A, and step-by-step walkthroughs.

## Setup (one time)

This project uses [**uv**](https://docs.astral.sh/uv/) for Python — a single fast tool that handles Python versions, virtualenvs, and dependencies. Install it once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv  (macOS)
```

Then:

```bash
cd /Users/chaitanyapradeeprepaka/Desktop/Training/backend

# Mintlify CLI for the docs site (requires Node 18+)
npm i -g mintlify
```

The Python project itself doesn't need a venv created manually — `uv run` and `uv sync` create one as needed.

## Two terminals, two servers

You'll typically have two things running:

```bash
# Terminal 1 — the working reference app
cd final-app
uv sync --group dev
ENROLLMENT_SECRET_KEY=$(openssl rand -hex 32) uv run uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs   (Swagger UI)

# Terminal 2 — the training docs (Mintlify)
cd docs && mintlify dev
# → http://localhost:3000
```

## Where the training lives

Once `mintlify dev` is running, open [http://localhost:3000](http://localhost:3000). Recommended path:

1. **Introduction** — what you're building and how this works
2. **Quickstart** — verify your environment
3. **Problem statement** — the domain in one page
4. **Learning path** — see all 36 modules at once
5. **Module 01: Hello FastAPI** — start coding

Each module follows the same shape:

- **Concept** — what + why (skim, don't memorize)
- **Walkthrough** — the code we add
- **Try it** — runnable steps
- **Quick check** — Q&A you can expand to verify understanding
- **Exercise** — 5–15 lines *you* write
- **Verify** — exact commands and expected output
- **Next** — link to the next module

> **Don't skip exercises.** They are where the concepts stick. Reading code feels productive but is forgotten in a week. Writing it locks it in.

## Repo layout

```
backend/
├── README.md                   ← you are here
├── .gitignore
│
├── app/                        ← YOUR workspace (Module 01 starter)
│   ├── __init__.py
│   └── main.py
│
├── final-app/                  ← THE WORKING REFERENCE — run it, study it
│   ├── pyproject.toml          ← uv-managed dependencies
│   ├── uv.lock                 ← reproducible lockfile
│   ├── app/                    ← every module's code, integrated
│   ├── tests/                  ← unit + integration tests (44 passing)
│   └── README.md
│
├── docs/                       ← Mintlify training site
│   ├── mint.json               ← navigation config
│   ├── introduction.mdx
│   ├── quickstart.mdx
│   ├── problem-statement.mdx
│   ├── learning-path.mdx
│   ├── modules/                ← all 36 modules
│   ├── exercises/              ← exercise solutions
│   └── reference/              ← architecture, glossary, cheatsheet, FAQ
│
└── logs/                       ← runtime logs (gitignored)
```

## Two ways to use this training

**See it work first:**
```bash
cd final-app
uv sync --group dev
ENROLLMENT_SECRET_KEY=$(openssl rand -hex 32) uv run uvicorn app.main:app --port 8000
# Hit http://localhost:8000/docs and try the Swagger UI
uv run pytest tests/ -v   # 44 tests pass
```

**Then build it yourself:**
```bash
# Your workspace is the top-level app/ — currently a hello-world endpoint.
# Follow Module 01 in the Mintlify docs to start adding code.
```

## uv quick reference

| Task | Command |
|---|---|
| Install all deps + dev deps | `uv sync --group dev` |
| Add a new dep | `uv add fastapi` |
| Add a dev dep | `uv add --group dev pytest` |
| Run a command in the venv | `uv run pytest` (no activation needed) |
| Update the lockfile | `uv lock` |
| Remove the venv | `rm -rf .venv` (then `uv sync` again) |

## Reference codebase

When a pattern is easier to grasp via real-world code, we also point at:

```
/Users/chaitanyapradeeprepaka/Desktop/Final CRF Annotation/annotate-hub-api/
```

A working clinical-trial app with the same architecture you'll build.

---

**Ready?** Start `mintlify dev` from `docs/`, open [http://localhost:3000](http://localhost:3000), and head to **Introduction**.
