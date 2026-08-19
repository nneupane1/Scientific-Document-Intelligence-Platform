import type {
  DocumentSummary,
  NarrationCapabilities,
  NarrationVoice,
  PageDetail,
} from "@/types/sdr";

// Empty by default: Next.js proxies /api to the loopback-only FastAPI service.
// An explicit public URL remains available for deployments with a separate API origin.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? "GET";
  const attempts = method === "GET" ? 2 : 1;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
      if (response.ok) return (await response.json()) as T;
      const payload = (await response.json().catch(() => ({}))) as { detail?: string };
      if (response.status >= 500 && attempt + 1 < attempts) {
        await new Promise((resolve) => setTimeout(resolve, 180));
        continue;
      }
      throw new ApiError(payload.detail ?? `Request failed (${response.status})`, response.status);
    } catch (error) {
      if (error instanceof ApiError || attempt + 1 >= attempts) throw error;
      await new Promise((resolve) => setTimeout(resolve, 180));
    }
  }
  throw new ApiError("Could not reach the document service", 0);
}

export async function apiBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  if (response.ok) return response.blob();
  const payload = (await response.json().catch(() => ({}))) as { detail?: string };
  throw new ApiError(payload.detail ?? `Request failed (${response.status})`, response.status);
}

export const documentsApi = {
  list: () => api<DocumentSummary[]>("/api/documents"),
  get: (id: string) => api<DocumentSummary>(`/api/documents/${id}`),
  page: (id: string, page: number) => api<PageDetail>(`/api/documents/${id}/pages/${page}`),
  fileUrl: (id: string) => `${API_URL}/api/documents/${id}/file`,
  narrationCapabilities: () =>
    api<NarrationCapabilities>("/api/narration/capabilities"),
  narrate: (
    id: string,
    request: { page_number: number; element_id?: string; voice: NarrationVoice },
  ) =>
    apiBlob(`/api/documents/${id}/narration`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),
};
