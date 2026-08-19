# Architecture overview

The platform treats a scientific PDF as compiler input and SDR as its intermediate representation. The original PDF is immutable visual truth; SDR supplies structure, coordinates, content, evidence, and downstream interoperability.

## Boundaries

```text
core + schema
    ↑
PDF / layout / preprocessing / engines / validation
    ↑
routing
    ↑
document / page / region pipelines
    ↑
jobs / API / CLI
    ↑
web viewer
```

Engines never import the API. The frontend never reads storage paths. PostgreSQL owns queryable state; the storage backend owns bytes and canonical artifacts. Exporters consume SDR, not database rows.

## Runtime topology

The infrastructure-backed local topology is Next.js → FastAPI → PostgreSQL/Redis → Dramatiq workers → local PDF/OCR/model processes and filesystem. A SQLite/background mode supports simple development without changing business logic.

The worker model separates CPU, OCR, GPU, and export resource concepts. V0's deterministic document orchestrator processes pages serially but commits each page and exposes granular page/reprocess actors. This limits accidental model fan-out on laptops and leaves safe parallelism as a policy decision.

## Graceful degradation

PyMuPDF alone provides inspection, native extraction, rendering, SDR, API, viewer, search, and export. OCR adapters activate only when their dependencies are installed. Formula model absence marks an equation `engine_unavailable`; formula confidence absence marks it `needs_review`. Optional failures do not prevent native pages from completing.
