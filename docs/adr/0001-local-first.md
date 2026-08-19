# ADR 0001: Local-first execution

Status: accepted.

The initial system runs the API, database, queue, workers, models, and storage locally. This makes privacy, reproducibility, offline operation, and cost measurement explicit before cloud complexity is introduced. Storage, queue, and database boundaries permit later managed services without changing SDR or engine contracts.
