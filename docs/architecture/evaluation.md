# Evaluation

The evaluation package measures character error rate (CER), word error rate (WER), exact and normalized LaTeX matches, token similarity, bounding-box IoU/precision/recall/F1, runtime, seconds per page, and process RSS where available.

Routing statistics answer a different but equally important question: how many elements were solved natively, by OCR, by formula recognition, after escalation, or not at all? The system reports those measured counts and never converts them into an accuracy claim without ground truth.

Gold annotations should transcribe the visible source, including scientific errors. Record text/equation strings and page bboxes. Separate anomaly notes from transcription. Evaluate representative easy native, raster, math-heavy, two-column, figure, poor-quality, and unusual-symbol pages. Pin the source SHA-256, configuration hash, pipeline/model versions, device, time, RAM, and GPU metrics with every report.
