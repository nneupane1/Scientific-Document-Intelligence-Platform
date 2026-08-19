# Processing pipeline

## Document pipeline

1. Validate the PDF signature, parser behavior, encryption state, page count, MIME, filename, and size.
2. Compute SHA-256 and return an existing document for an exact duplicate.
3. Preserve the input at `original/document.pdf`; create document and job state.
4. Record run versions, configuration hash, available engines, and optional Git commit.
5. Open the document and process each page, resuming matching completed page artifacts.
6. Persist page SDR and normalized database rows after each page.
7. Aggregate pages into canonical `document.sdr.json`, derive statistics, and complete the run/job.

## Page pipeline

Inspection estimates native text and image coverage, counts image/vector objects, records fonts/rotation, and classifies the page. If native text is reliable, PyMuPDF blocks become SDR directly and embedded images become figure geometry. No OCR runs.

If native content is inadequate, the page is rendered at 300 DPI. OpenCV records contrast, blur, skew, noise, and grayscale measures. A classical connected-component layout detector creates text/equation/figure regions and reading order. Each region is cropped and passed to the region pipeline. Low scored visual results may be retried at 450 DPI; maximum 600 DPI is available by policy.

## Region pipeline

The router resolves region capability, sorts engines by estimated relative cost, checks availability, runs the cheapest supported engine, and accepts only evidence meeting policy. Text and LaTeX validators attach warnings without scientific correction. Unavailable output remains an explicit empty recognition with source bbox and review state.

## Idempotency and recovery

Page identity, result path, element IDs, pipeline configuration hash, and deterministic artifact names make retries idempotent. A page rerun deletes/replaces that page's element rows in one unit instead of adding duplicates. Completed page JSON with a matching config hash is loaded during resume.
