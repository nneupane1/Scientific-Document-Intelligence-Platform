export type ElementType =
  | "paragraph" | "title" | "heading" | "equation" | "figure" | "caption"
  | "table" | "page_number" | "footnote" | "unknown" | "chemical_equation"
  | "molecule" | "circuit" | "chart" | "diagram" | "braille" | "code" | "reference";

export type ReviewStatus =
  | "accepted" | "uncertain" | "rejected" | "needs_review" | "engine_unavailable";

export interface ProvenanceEvent {
  method: string;
  engine: string;
  engine_version?: string | null;
  model?: string | null;
  model_version?: string | null;
  pipeline_version: string;
  source_page?: number | null;
  created_at?: string;
  details?: Record<string, string | number | boolean | null>;
}

export interface Provenance extends Omit<ProvenanceEvent, "created_at" | "details"> {
  cache_hit: boolean;
  cache_key?: string | null;
  history: ProvenanceEvent[];
}

export interface ElementContent {
  text?: string | null;
  latex?: string | null;
  raw_latex?: string | null;
  normalized_latex?: string | null;
  mathml?: string | null;
  unicode?: string | null;
  label?: string | null;
  columns?: string[] | null;
  rows?: Array<Array<string | number | null>> | null;
  alt_text?: string | null;
  words: Array<Record<string, unknown>>;
  spans: Array<Record<string, unknown>>;
  candidates: Array<Record<string, unknown>>;
}

export interface SdrElement {
  id: string;
  type: ElementType;
  bbox: [number, number, number, number];
  reading_order: number;
  content: ElementContent;
  confidence: number | null;
  confidence_source: string;
  provenance: Provenance;
  review_status: ReviewStatus;
  warnings: string[];
}

export interface SdrPage {
  number: number;
  width: number;
  height: number;
  classification: "native" | "raster" | "hybrid" | "vector_heavy" | "unknown";
  elements: SdrElement[];
  metrics: Record<string, unknown>;
}

export interface SdrDocument {
  schema_version: "0.1.0";
  document: { id: string; filename: string; sha256: string; page_count: number; title?: string | null };
  pages: SdrPage[];
  processing: Record<string, number>;
  pipeline_version: string;
  config_hash: string;
  model_versions: Record<string, string>;
}
