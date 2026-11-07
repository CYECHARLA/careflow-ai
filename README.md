# CareFlow AI

A **synthetic-data-only** healthcare administrative workflow portfolio prototype. FastAPI + SQLAlchemy backend, React/TypeScript frontend, PDF/image uploads, OCR, deterministic document classification, referral completeness checks, follow-up tasks, human review, audit events, and mock integrations.

![Status](https://img.shields.io/badge/status-portfolio%20prototype-teal)

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Visit http://localhost:5173 and sign in with `admin` / `DemoPass123!`. API documentation: http://localhost:8000/docs.

**Only synthetic documents may be uploaded.** Do not expose the demo password or development environment to the public internet.

## Demo document

Use a text-based PDF containing:

```
ABA Referral
Patient Name: Alex Johnson
DOB: 2019-04-15
Provider: Dr. Sarah Miller
Signature: missing
```

Create a referral, link the PDF during upload, process it, inspect the review queue, and validate completeness to generate follow-up tasks.

## Features implemented

- JWT login, role checks, password hashing
- PDF/PNG/JPEG uploads with size/type/magic-byte validation
- PDF text extraction and Tesseract OCR for images
- Deterministic mock classification and field extraction (no paid API)
- Human review approval/rejection with audit events
- Referral creation, validation and task generation
- API-driven dashboard, status visualization and audit history
- Idempotent mock integration sync logs

## Limitations and roadmap

This is a working **partial implementation**, not a complete production deployment. It does **not yet** include a Celery worker, Redis job queue integration, real OpenAI structured-output adapter, Alembic migrations, comprehensive RBAC, automatic referral generation from extraction, full signature verification, webhook receiver, retry/backoff, seed dataset, or comprehensive test coverage. Some UI pages are minimal and editing extracted fields is currently API-only. Do not represent this as HIPAA-compliant or production-ready.

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

See [architecture](docs/architecture.md), [database](docs/database.md), [workflows](docs/workflows.md), [security](docs/security.md), and [API](docs/api.md).
