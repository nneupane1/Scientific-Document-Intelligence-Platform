# Storage and persistence

PostgreSQL stores document/page/element/job/run metadata and JSON fields used for querying. Binary and canonical artifacts remain under the configured `LocalStorage` root. The interface supports future S3/MinIO adapters without leaking object-store concepts into processing.

Storage keys are relative, normalized, and verified to remain below the root. The API never accepts a user-provided local path. Source PDFs are copied once and never modified. Temporary uploads are bounded and removed after validation/ingestion.

Each page result is committed independently to a deterministic path and database row. Processing can resume after a crash if the result exists and its recorded configuration hash matches. A changed pipeline policy naturally invalidates that resume check.

PostgreSQL and Redis use named Docker volumes. Redis contains queue/ephemeral state only; canonical scientific results never depend on Redis persistence.
