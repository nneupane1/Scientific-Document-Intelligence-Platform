# Benchmarking

The benchmark distinguishes measured recognition fidelity from routing/performance telemetry.

`source-documents.zip` is the canonical supplied corpus. Extract it with `./scripts/extract_sample_corpus.sh`; do not substitute conceptual `physics.pdf` examples. Run `make benchmark` to process both supplied PDFs and write `benchmark/reports/latest.json`.

No production score is included because the supplied files do not include human-verified ground truth. Add gold data under `benchmark/ground_truth/<dataset>/` with source SHA-256, page number, text/equation transcription, element type, bbox, and review notes. Preserve literal source errors.

A useful first gold set is about ten pages covering native text, scans, dense math, complex equations, two columns, figures/captions, low quality, and unusual symbols. Report CER/WER, exact/normalized equation match, token similarity, layout IoU, native/OCR/formula/escalation/review ratios, seconds/page, RAM, and GPU usage.
