AGENTS.md

Project context: Python 3.11 • FastAPI backend • PEP 8 • Type hints everywhere • Async-first.

This file is the single source of truth for how automated agents (and human contributors) propose, implement, and verify changes in this repository. Agents must follow the protocol below.

⸻

1) Mission & Scope
	•	Make small, reviewable changes with clear intent.
	•	Prefer plan → change → verify.
	•	Keep public APIs stable unless the task explicitly authorizes breaking changes.
	•	All code targets Python 3.11; use typing and PEP 8.

⸻

2) House Rules (Style & Quality)

2.1 Language & Formatting
	•	Python version: 3.11 (use | union types, typing.Self, typing.Literal, typing.TypedDict, dataclasses, enum).
	•	Formatting: Ruff (line-length 100). No manual alignment.
	•	Lint: Ruff (fix auto-fixable issues). Treat warnings as errors in CI.
	•	Docstrings: Google style. Public functions/classes must have docstrings and type hints.
	•	Imports: absolute where possible; group stdlib / third-party / local with blank lines.
	•	Logging: logging module; no print in library code. Use structured messages.
	•	Dependency managagement: use uv whenever possible, inside dockerfiles too.
	•	Run code with uv run not python command directly.
	•	Docs: add definition of every endpoint to README.md so user knows what kind of request should be sent.
	•	Prepare testing scripts in scripts/ but don't create pytest tests.


2.2 FastAPI Conventions
	•	Async-first: prefer async def routes and I/O.
	•	Schemas: Pydantic v2 models in schemas/ with explicit field types and constraints.
	•	Dependency Injection: use FastAPI Depends for services/config/DB sessions.
	•	Error handling: raise HTTPException with precise status codes; centralize handlers in api/errors.py.
	•	OpenAPI: every endpoint documented via response models and status codes.
	•	Validation: validate query/path/body via Pydantic models; avoid ad‑hoc dict access.
	•	Security: prefer OAuth2 bearer (JWT) or API keys via dependencies; add CORS config.
	•	Pagination: limit/offset or cursor-based; document defaults and maximums.
	•	Versioning: path-based (/api/v1/...), keep backward compatibility within the same major.

⸻

1) Repository Layout (expected)

repo/
├─ src/
│  ├─ app/
│  │  ├─ main.py                 # FastAPI app factory + routers
│  │  ├─ api/                    # Routers (v1/...)
│  │  ├─ services/               # Business logic (pure, testable)
│  │  ├─ repositories/           # DB/data-access layer
│  │  ├─ schemas/                # Pydantic v2 models
│  │  ├─ core/                   # settings, logging, security, errors
│  │  └─ utils/                  # small helpers (no I/O side effects)
│  └─ cli/
├─ docs/
│  └─ STYLE.md (optional, this file supersedes where conflicting)
├─ pyproject.toml
├─ .pre-commit-config.yaml
└─ AGENTS.md (this file)


⸻

4) Change Protocol (for Agents)
	1.	Plan
	•	Create a short plan (bullets) with: goal, touched files, risk class, test plan.
	•	Confirm the change type (see §5).
	2.	Change
	•	Keep diffs small; one logical change per PR.
	•	Respect module boundaries: API ↔ service ↔ repository.
	•	If editing public APIs, update schemas, OpenAPI, and version notes.
	3.	Verify (must pass locally before opening
