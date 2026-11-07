# Data model

```mermaid
erDiagram
 USERS ||--o{ REFERRALS : assigned
 PATIENTS ||--o{ REFERRALS : has
 REFERRALS ||--o{ DOCUMENTS : includes
 REFERRALS ||--o{ TASKS : generates
 DOCUMENTS ||--o{ REVIEWS : requires
 USERS ||--o{ AUDIT_LOGS : records
```

Current tables: users, patients, referrals, documents, tasks, reviews, audit_logs, integration_logs. The full normalized schema from the specification and Alembic migrations remain future work.
