# Cost-aware routing

The router encodes “cheapest reliable method first” as an executable short circuit and a capability/cost registry.

```text
reliable native content? ── yes → accept and stop
          │ no
          ▼
text region? → lightweight OCR → confidence threshold
equation?    → formula-small  → confidence/evidence threshold
          │ inadequate
          ▼
higher-DPI crop → optional stronger specialist → optional VLM → review
```

Native reliability is based on direct text presence, coverage, printable-character count, and replacement-character diagnostics. Native confidence represents deterministic extraction evidence, not an OCR probability.

OCR engines expose raw and normalized scores with their source. Scores from different engines are never claimed to be calibrated equivalents. Engines with no score return `null`; policy cannot accept them automatically. Disagreement is surfaced through candidates/consensus rather than resolved from scientific prior knowledge.

Routing thresholds and feature flags are configuration. The router is rule-based by design; an ML router would be premature before the benchmark contains enough calibrated examples.
