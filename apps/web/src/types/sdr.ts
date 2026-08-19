export type ReviewStatus = "accepted" | "uncertain" | "rejected" | "needs_review" | "engine_unavailable";

export interface SdrElement {
  id: string;
  page_id: string;
  element_type: string;
  bbox: [number, number, number, number];
  reading_order: number;
  content: {
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
    words?: Array<Record<string, unknown>>;
    spans?: Array<Record<string, unknown>>;
    candidates?: Array<Record<string, unknown>>;
  };
  confidence: number | null;
  confidence_source: string;
  provenance: {
    method: string;
    engine: string;
    engine_version?: string | null;
    model?: string | null;
    model_version?: string | null;
    pipeline_version: string;
    source_page?: number | null;
    cache_hit: boolean;
    cache_key?: string | null;
    history: Array<Record<string, unknown>>;
  };
  review_status: ReviewStatus;
  warnings: string[];
}

export interface PageDetail {
  id: string;
  document_id: string;
  page_number: number;
  width: number;
  height: number;
  classification: string;
  status: string;
  inspection: Record<string, unknown>;
  elements: SdrElement[];
}

export interface Job {
  id: string;
  document_id: string;
  job_type: string;
  status: string;
  attempts: number;
  progress: number;
  pages_completed: number;
  pages_total: number;
  stage: string;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  sha256: string;
  page_count: number;
  status: string;
  created_at: string;
  updated_at: string;
  latest_job: Job | null;
  summary: Record<string, number> | null;
}

export type NarrationVoice =
  | "alloy"
  | "ash"
  | "ballad"
  | "coral"
  | "echo"
  | "fable"
  | "nova"
  | "onyx"
  | "sage"
  | "shimmer"
  | "verse"
  | "marin"
  | "cedar"
  | "af_heart"
  | "af_bella"
  | "af_nicole"
  | "bf_emma"
  | "samantha"
  | "daniel"
  | "karen"
  | "moira"
  | "rishi"
  | "tessa";

export interface NarrationCapabilities {
  configured: boolean;
  provider: "kokoro" | "macos" | "openai" | "unavailable";
  model: string;
  default_voice: NarrationVoice;
  voices: Array<{ id: NarrationVoice; label: string; recommended: boolean }>;
  ai_generated: boolean;
  remote_processing: boolean;
  privacy_notice: string;
}
