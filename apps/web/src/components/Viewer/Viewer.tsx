"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import ElementInspector from "@/components/ElementInspector/ElementInspector";
import NaturalNarration from "@/components/NaturalNarration/NaturalNarration";
import PdfCanvas from "@/components/PdfCanvas/PdfCanvas";
import SemanticOverlay from "@/components/SemanticOverlay/SemanticOverlay";
import { API_URL, api, documentsApi } from "@/lib/api";
import type { DocumentSummary, PageDetail, SdrElement } from "@/types/sdr";

export default function Viewer({ documentId }: { documentId: string }) {
  const [document, setDocument] = useState<DocumentSummary | null>(null);
  const [page, setPage] = useState<PageDetail | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [viewport, setViewport] = useState({ width: 0, height: 0 });
  const [selected, setSelected] = useState<SdrElement | null>(null);
  const [debug, setDebug] = useState(false);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Array<{ page_number: number; snippet: string }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { void documentsApi.get(documentId).then(setDocument).catch((reason) => setError(String(reason))); }, [documentId]);
  useEffect(() => {
    void documentsApi.page(documentId, pageNumber).then((nextPage) => {
      setPage(nextPage);
      setSelected(null);
    }).catch((reason: unknown) => {
      setPage(null);
      setError(reason instanceof Error ? reason.message : String(reason));
    });
  }, [documentId, pageNumber]);
  const setPdfViewport = useCallback((next: { width: number; height: number }) => setViewport(next), []);

  async function search(event: FormEvent) { event.preventDefault(); if (!query.trim()) { setHits([]); return; } const result = await api<{ hits: Array<{ page_number: number; snippet: string }> }>(`/api/documents/${documentId}/search?q=${encodeURIComponent(query)}`); setHits(result.hits); }
  const maxPage = document?.page_count ?? 1;
  return <main className="viewer-shell">
    <header className="viewer-toolbar"><div className="viewer-title"><Link href="/" className="back-link">← Library</Link><div><h1>{document?.filename ?? "Loading document…"}</h1><p>{page?.classification ?? document?.status ?? "loading"} · page {pageNumber} of {maxPage}</p></div></div>
      <form className="viewer-search" onSubmit={(event) => void search(event)}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search text or LaTeX" aria-label="Search document"/><button>Search</button></form>
      <label className="toggle"><input type="checkbox" checked={debug} onChange={(event) => setDebug(event.target.checked)} /><span />Show semantic regions</label>
    </header>
    <NaturalNarration documentId={documentId} pageNumber={pageNumber} selected={selected} />
    {hits.length > 0 && <div className="search-results"><strong>{hits.length} result{hits.length === 1 ? "" : "s"}</strong>{hits.slice(0, 8).map((hit, index) => <button key={`${hit.page_number}-${index}`} onClick={() => { setPageNumber(hit.page_number); setHits([]); }}>{hit.page_number}<span>{hit.snippet}</span></button>)}</div>}
    {error && <div className="viewer-error">{error}</div>}
    <div className="viewer-grid">
      <aside className="page-rail"><button disabled={pageNumber <= 1} onClick={() => setPageNumber((value) => value - 1)}>↑<span>Previous</span></button><div className="page-input"><input type="number" min={1} max={maxPage} value={pageNumber} onChange={(event) => setPageNumber(Math.min(maxPage, Math.max(1, Number(event.target.value))))}/><small>/ {maxPage}</small></div><button disabled={pageNumber >= maxPage} onClick={() => setPageNumber((value) => value + 1)}>↓<span>Next</span></button><a className="rail-selectable" href={`${API_URL}/api/documents/${documentId}/exports/pdf`} target="_blank" rel="noreferrer" aria-label="Open visually identical PDF with selectable text"><b aria-hidden="true">PDF</b><span>Select &amp; copy</span></a><a className="rail-download" href={`${API_URL}/api/documents/${documentId}/exports/html`} target="_blank" rel="noreferrer" aria-label="Open accessible HTML for screen readers"><b aria-hidden="true">A11Y</b><span>Screen reader</span></a><a className="rail-json" href={`${API_URL}/api/documents/${documentId}/sdr`} target="_blank" rel="noreferrer" aria-label="Open canonical SDR JSON">{`{ }`}<span>SDR JSON</span></a></aside>
      <section className="document-stage"><div className="page-stack" style={viewport.width ? { width: viewport.width, height: viewport.height } : undefined}><PdfCanvas url={documentsApi.fileUrl(documentId)} pageNumber={pageNumber} onViewport={setPdfViewport}/>{page && viewport.width > 0 && <SemanticOverlay page={page} viewport={viewport} debug={debug} selected={selected?.id ?? null} onSelect={setSelected}/>}</div></section>
      <ElementInspector element={selected} pageNumber={pageNumber} onClose={() => setSelected(null)} />
    </div>
  </main>;
}
