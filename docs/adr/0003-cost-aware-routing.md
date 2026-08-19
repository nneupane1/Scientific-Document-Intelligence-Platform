# ADR 0003: Cost-aware routing is mandatory

Status: accepted.

Scientific books often contain a mix of native and raster regions. Whole-document OCR/model inference wastes compute and can reduce fidelity. Routing therefore escalates per region and must stop as soon as configured evidence is sufficient. Native-short-circuit behavior is protected by a unit test.
