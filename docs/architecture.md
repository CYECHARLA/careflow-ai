# Architecture

```mermaid
flowchart TD
 React[React TypeScript] --> API[FastAPI RBAC]
 API --> DB[(PostgreSQL)]
 API --> Storage[(Local document storage)]
 API --> OCR[PyMuPDF / Tesseract]
 OCR --> Rules[Deterministic demo classification]
 Rules --> Validation[Completeness validation]
 Validation --> Tasks[Follow-up tasks]
 API --> Integrations[Mock integration adapters]
```

This initial implementation processes documents synchronously. Redis/Celery are planned for asynchronous processing, and an external LLM adapter is not yet implemented. Do not use with real PHI.
