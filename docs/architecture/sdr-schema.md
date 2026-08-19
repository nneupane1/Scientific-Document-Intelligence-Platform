# Scientific Document Representation

`packages/schema/jsonschema/sdr.schema.json` is the language-neutral contract. Pydantic runtime models live under `packages/schema/python`; TypeScript types live under `packages/schema/typescript` and the web app's API types.

SDR 0.1.0 contains document identity/hash/page count, ordered pages, semantic elements, processing statistics, pipeline/config versions, and model versions. Every element requires an ID, type, top-left page-coordinate bbox, reading order, typed content object, nullable confidence, confidence source, provenance, review status, and warnings.

Element types cover paragraphs, titles, headings, multidisciplinary equations, figures, captions, tables, page numbers, footnotes, Braille, chemistry, molecules, circuits, charts, diagrams, code, references, and unknown content. Braille elements preserve the original Unicode cells and may include a deterministic uncontracted transcription without discarding the source notation.

Equation content keeps raw/normalized LaTeX, MathML, Unicode, and a separate label where available. Text remains source transcription. Candidate attempts and append-only provenance history retain reprocessing evidence. Interpretation and human correction are separate future records; they do not overwrite original recognition.
