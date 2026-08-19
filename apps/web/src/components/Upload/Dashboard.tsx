"use client";

import Image from "next/image";
import Link from "next/link";
import { ChangeEvent, CSSProperties, DragEvent, useCallback, useEffect, useRef, useState } from "react";
import JobProgress from "@/components/JobProgress/JobProgress";
import { API_URL, api, documentsApi } from "@/lib/api";
import type { DocumentSummary } from "@/types/sdr";
import brandArtwork from "../../../../../image.png";

interface DashboardProps { title?: string }

interface RuntimeEngine {
  name: string;
  version: string;
  capabilities: string[];
  devices: string[];
  available: boolean;
  reason: string | null;
}

interface RuntimeCapabilities {
  pipeline_version: string;
  schema_version: string;
  processing_mode: string;
  queue_mode: string;
  deterministic_core: boolean;
  llm_in_evidence_path: boolean;
  vlm_policy_enabled: boolean;
  vlm_adapter_configured: boolean;
  feature_flags: Record<string, boolean>;
  engines: RuntimeEngine[];
}

const processingStages = [
  { title: "Inspect", detail: "Page geometry", art: "/ai-assets/semantic-inspection-transparent.png" },
  { title: "Extract", detail: "Native evidence", art: "/ai-assets/structured-data-crystal-transparent.png" },
  { title: "Route", detail: "Specialist only if needed", art: "/ai-assets/data-export-transparent.png" },
  { title: "Validate", detail: "Confidence gates", art: "/ai-assets/ai-observability-transparent.png" },
  { title: "Publish", detail: "Canonical SDR", art: "/ai-assets/structured-data-crystal-transparent.png" },
];

const intelligenceRows = [
  { signal: "Native PDF text", descriptor: "Embedded evidence", glyph: "Aa", tone: "native", route: "PyMuPDF text spans + page geometry", intelligence: "Deterministic", boundary: "No OCR, LLM, or VLM" },
  { signal: "Scans and image text", descriptor: "Raster recognition", glyph: "OCR", tone: "vision", route: "RapidOCR/Tesseract; PaddleOCR adapter", intelligence: "OCR / optional DL", boundary: "Word boxes and confidence retained" },
  { signal: "Mathematical equations", descriptor: "Symbolic notation", glyph: "∑", tone: "math", route: "Native notation, optional pix2tex, OCR fallback", intelligence: "Rules + optional DL", boundary: "Uncertain symbols require review" },
  { signal: "Tables", descriptor: "Cell topology", glyph: "▦", tone: "table", route: "Cell geometry, rows, columns, then OCR if needed", intelligence: "Geometry first", boundary: "No generative row completion" },
  { signal: "Charts, diagrams, chemistry", descriptor: "Visual structures", glyph: "CV", tone: "visual", route: "Vector/CV preservation + OCR; VLM adapter escalation", intelligence: "CV + gated VLM", boundary: "VLM output is never silent evidence" },
  { signal: "Braille", descriptor: "Accessible encoding", glyph: "⠿", tone: "access", route: "Unicode Grade-1 decode + visual dot geometry", intelligence: "Deterministic", boundary: "Unknown cells are preserved, never guessed" },
];

const domains = [
  ["Mathematics", "LaTeX, MathML, Unicode"], ["Physics", "symbols, vectors, units"],
  ["Engineering", "schematics and equations"], ["Computer science", "code, algorithms, diagrams"],
  ["AI & machine learning", "notation, tables, architectures"], ["Medicine", "papers, tables, annotated figures"],
  ["Biological sciences", "captions, labels, microscopy"], ["Chemistry", "regions, notation, model escalation"],
  ["Natural & life sciences", "mixed scientific layouts"], ["Finance", "statements, formulas, disclosures"],
  ["Quantitative trading", "time-series charts and models"], ["Accessibility", "Unicode and visual Braille evidence"],
];

const engineLabels: Record<string, string> = {
  lightweight_ocr: "Local OCR", paddleocr: "PaddleOCR", formula_small: "pix2tex Formula DL",
  formula_ocr_fallback: "Formula OCR fallback", formula_large: "Large formula adapter",
};

export default function Dashboard({ title = "Scientific documents, made machine-readable." }: DashboardProps) {
  const input = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [runtime, setRuntime] = useState<RuntimeCapabilities | null>(null);
  const [selected, setSelected] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try { setDocuments(await documentsApi.list()); } catch (error) { setMessage(error instanceof Error ? error.message : "Could not load documents"); }
  }, []);
  const handleJobComplete = useCallback(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    void Promise.all([documentsApi.list(), api<RuntimeCapabilities>("/api/capabilities")])
      .then(([documentList, capabilityStatus]) => { setDocuments(documentList); setRuntime(capabilityStatus); })
      .catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Could not connect to the local service"));
  }, []);

  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => {
        if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); }
      }),
      { rootMargin: "0px 0px -9% 0px", threshold: 0.12 },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  function choose(file?: File) {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) { setMessage("Choose a PDF file."); return; }
    setSelected(file); setMessage(null);
  }

  function drop(event: DragEvent<HTMLDivElement>) { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]); }

  async function upload() {
    if (!selected) return;
    setUploading(true); setMessage("Uploading…");
    const form = new FormData(); form.append("file", selected);
    try {
      const response = await fetch(`${API_URL}/api/documents`, { method: "POST", body: form });
      const payload = (await response.json()) as { job_id?: string; detail?: string };
      if (!response.ok || !payload.job_id) throw new Error(payload.detail ?? "Upload failed");
      setJobId(payload.job_id); setMessage(null); setSelected(null);
      if (input.current) input.current.value = "";
      await refresh();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Upload failed"); }
    finally { setUploading(false); }
  }

  const pageCount = documents.reduce((total, document) => total + document.page_count, 0);
  const completedCount = documents.filter((document) => document.status === "completed").length;
  const availableEngines = runtime?.engines.filter((engine) => engine.available).length ?? 0;
  const enabledDomains = runtime ? Object.values(runtime.feature_flags).filter(Boolean).length : 0;

  return (
    <main className="shell dashboard">
      <section
        className="hero"
        onPointerMove={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          event.currentTarget.style.setProperty("--hero-x", `${((event.clientX - bounds.left) / bounds.width) * 100}%`);
          event.currentTarget.style.setProperty("--hero-y", `${((event.clientY - bounds.top) / bounds.height) * 100}%`);
        }}
        onPointerLeave={(event) => {
          event.currentTarget.style.setProperty("--hero-x", "78%");
          event.currentTarget.style.setProperty("--hero-y", "26%");
        }}
      >
        <p className="eyebrow hero-kicker"><span /> Evidence-first document intelligence</p>
        <div className="hero-copy">
          <h1>{title}</h1>
          <p className="lede">Turn complex scientific PDFs into structured, reviewable data—without losing the source page, coordinates, confidence, or the exact recognition path behind each element.</p>
          <div className="hero-actions">
            <button className="hero-primary" onClick={() => input.current?.click()}>Process a document <span>↗</span></button>
            <a className="hero-secondary" href="#intelligence">Explore the intelligence stack</a>
          </div>
          <div className="trust-row" aria-label="Product attributes">
            <span><i>01</i> Local-first</span><span><i>02</i> Verifiable output</span><span><i>03</i> No silent fabrication</span>
          </div>
        </div>
        <div className="hero-route-visual" aria-label="Scientific document transforming into validated machine-readable data">
          <span className="hero-route-packet packet-a" aria-hidden /><span className="hero-route-packet packet-b" aria-hidden /><span className="hero-route-packet packet-c" aria-hidden />
          <Image className="hero-route-art" src="/ai-assets/document-transformer-transparent.png" alt="A scientific PDF passing through an evidence-gated intelligence router and emerging as typed machine-readable data" width={1774} height={887} priority sizes="(max-width: 900px) 92vw, 680px" />
          <div className="hero-route-states" aria-hidden>
            <span><i>01</i><b>Source locked</b></span><span><i>02</i><b>Evidence routed</b></span><span><i>03</i><b>SDR validated</b></span>
          </div>
        </div>
      </section>

      <section className="proof-strip" aria-label="Live platform status" data-reveal>
        <div><span className="status-beacon" /><strong>Runtime connected</strong><small>{runtime?.processing_mode ?? "Connecting…"}</small></div>
        <div><strong>{runtime?.pipeline_version ?? "—"}</strong><small>pipeline version</small></div>
        <div><strong>{availableEngines}</strong><small>recognition routes online</small></div>
        <div><strong>{enabledDomains}/6</strong><small>capability policies enabled</small></div>
        <div><strong>{runtime?.llm_in_evidence_path ? "Enabled" : "None"}</strong><small>LLM in evidence path</small></div>
      </section>

      <section className="pipeline-band" aria-labelledby="pipeline-title" data-reveal>
        <div className="pipeline-header">
          <div><p className="pipeline-kicker">Adaptive processing pipeline</p><h2 id="pipeline-title">From source page to canonical SDR</h2></div>
          <p className="pipeline-summary">The cheapest reliable route wins. Escalation happens only when the evidence calls for it.</p>
        </div>
        <ol>{processingStages.map((stage, index) => (
          <li key={stage.title}>
            <span className="pipeline-number pipeline-ai-node">
              <Image src={stage.art} alt="" width={56} height={56} sizes="56px" />
              <b>{String(index + 1).padStart(2, "0")}</b>
            </span>
            <div className="pipeline-stage-copy"><strong>{stage.title}</strong><small>{stage.detail}</small></div>
            {index < processingStages.length - 1 && <span className="pipeline-arrow" aria-hidden>→</span>}
          </li>
        ))}</ol>
      </section>

      <section id="platform" className="enterprise-section platform-section" data-reveal>
        <SectionHeading label="Document layers" title="One document. Every machine-readable layer." copy="A single pipeline preserves the original artifact and publishes the text, layout, equations, tables, visual regions, accessibility signals, confidence, and provenance that downstream systems need." />
        <div className="feature-bento">
          <article className="bento-card bento-primary">
            <div className="bento-copy"><span className="card-index">01 / STRUCTURE</span><h3>Canonical scientific document representation</h3><p>Page-aware JSON with typed elements, normalized coordinates, reading order, review state, warnings, and source-linked provenance.</p></div>
            <div className="bento-visual structure-visual"><Image className="bento-ai-art structured-art" src="/ai-assets/structured-data-crystal-transparent.png" alt="A scientific document transforming into structured data layers" width={1254} height={1254} sizes="(max-width: 820px) 70vw, 360px" /></div>
            <div className="schema-window" aria-label="Example structured document fields">
              <span><i>element_type</i><b>equation</b></span><span><i>bbox</i><b>[x₀, y₀, x₁, y₁]</b></span><span><i>content</i><b>LaTeX · MathML · Unicode</b></span><span><i>review_status</i><b>accepted | needs_review</b></span><span><i>provenance</i><b>engine · version · source page</b></span>
            </div>
          </article>
          <article className="bento-card bento-inspect"><div className="bento-copy"><span className="card-index">02 / INSPECT</span><h3>Evidence you can see</h3><p>Open the original PDF beside selectable semantic overlays. Inspect every bounding box and every extracted value.</p></div><div className="bento-visual inspect-visual"><Image className="bento-ai-art inspect-art" src="/ai-assets/semantic-inspection-transparent.png" alt="A magnifying lens inspecting semantic regions on a scientific page" width={1254} height={1254} sizes="(max-width: 820px) 70vw, 280px" /></div></article>
          <article className="bento-card bento-export"><div className="bento-copy"><span className="card-index">03 / EXPORT</span><h3>Built for people and systems</h3><p>Download a visually identical PDF with selectable OCR text, use semantic HTML with screen readers, or send canonical SDR to software and APIs.</p></div><div className="bento-visual export-visual"><Image className="bento-ai-art export-art" src="/ai-assets/data-export-transparent.png" alt="Structured scientific data flowing to selectable documents, assistive technology, APIs, and databases" width={1254} height={1254} sizes="(max-width: 820px) 70vw, 260px" /><div className="format-row"><span>SELECT PDF</span><span>A11Y HTML</span><span>JSON</span><span>API</span></div></div></article>
          <article className="bento-card bento-wide bento-operate"><div className="bento-copy"><span className="card-index">04 / OPERATE</span><h3>Asynchronous processing with document-level observability</h3><p>Background jobs expose stage, progress, page count, error state, and completion while content remains available in the local library.</p></div><div className="bento-visual operate-visual"><Image className="bento-ai-art observe-art" src="/ai-assets/ai-observability-transparent.png" alt="An AI observability core supervising charts, confidence, and runtime health" width={1180} height={1333} sizes="(max-width: 820px) 55vw, 310px" /></div><div className="telemetry-line"><span>queued</span><span>inspecting</span><span>recognizing</span><span>validating</span><span className="active">published</span></div></article>
        </div>
      </section>

      <section id="intelligence" className="enterprise-section intelligence-section" data-reveal>
        <SectionHeading label="Model routing" title="AI where recognition helps. Determinism where truth matters." copy="This is not an LLM wrapper. The router inspects each page and uses native extraction first, specialist recognition second, and an explicitly configured vision-language model only as a bounded escalation for unresolved visual regions." />
        <div className="escalation-board" aria-label="Evidence-gated model escalation contract">
          <div className="escalation-budget">
            <p className="eyebrow">Escalation budget</p>
            <div className="budget-dial" aria-hidden><span><b>Native</b><small>default</small></span></div>
            <strong>Use the least powerful reliable method.</strong>
            <p>Cost and model complexity increase only when source evidence cannot be recovered deterministically.</p>
          </div>
          <div className="escalation-ladder">
            <div className="escalation-rail" aria-hidden><i /></div>
            <article className="tier-native"><span>00</span><div><strong>Native extraction</strong><small>Text spans · vectors · page geometry</small></div><b>Always first</b></article>
            <article className="tier-specialist"><span>01</span><div><strong>Specialist recognition</strong><small>OCR · formula DL · table geometry</small></div><b>Signal required</b></article>
            <article className="tier-vlm"><span>02</span><div><strong>Bounded visual model</strong><small>Unresolved charts · diagrams · chemistry</small></div><b>Explicit gate</b></article>
          </div>
          <div className="release-gates">
            <p className="eyebrow">Release contract</p>
            <article><span>✓</span><div><strong>Evidence attached</strong><small>Page, coordinates and engine retained</small></div></article>
            <article><span>✓</span><div><strong>Confidence checked</strong><small>Uncertainty becomes review state</small></div></article>
            <article><span>✓</span><div><strong>No silent repair</strong><small>Missing content stays explicitly missing</small></div></article>
            <div className="release-status"><i /> Publish gate armed</div>
          </div>
        </div>
        <div className="boundary-panel">
          <div className="boundary-head"><div><p className="eyebrow">Decision ledger</p><h3>Exactly where models are—and are not—used</h3></div><span className="truth-pill"><i /> Evidence policy active</span></div>
          <div className="ledger-metrics" aria-label="Evidence routing safeguards">
            <article><span>06</span><div><strong>Signal classes</strong><small>Independently routed</small></div></article>
            <article><span>04</span><div><strong>Deterministic gates</strong><small>Before model escalation</small></div></article>
            <article><span>00</span><div><strong>Silent generations</strong><small>Permitted in evidence</small></div></article>
          </div>
          <div className="boundary-table" role="table" aria-label="Intelligence boundaries by document content">
            <div className="boundary-row boundary-labels" role="row"><span>Document signal</span><span>Processing route</span><span>Method</span><span>Hard boundary</span></div>
            {intelligenceRows.map((row, index) => (
              <div className={`boundary-row boundary-row--${row.tone}`} role="row" key={row.signal} style={{ "--ledger-delay": `${index * -1.6}s` } as CSSProperties}>
                <div className="boundary-signal"><span className="signal-glyph" aria-hidden>{row.glyph}</span><div><strong>{row.signal}</strong><small>{row.descriptor}</small></div></div>
                <span className="boundary-route"><span>{row.route}</span></span>
                <em><i aria-hidden />{row.intelligence}</em>
                <small className="boundary-guard"><i aria-hidden>✓</i><span>{row.boundary}</span></small>
              </div>
            ))}
          </div>
          <div className="llm-policy"><span className="llm-mark"><i aria-hidden /><b>LLM</b></span><div><strong>Not present in the core evidence path</strong><p>No language model rewrites native text, invents table cells, repairs equations, or silently describes figures. Future summarization or semantic enrichment can sit downstream as a separately labeled, source-cited layer.</p><div className="llm-policy-tags"><span>Source locked</span><span>Evidence immutable</span><span>Downstream only</span></div></div><span className="llm-boundary-state"><i aria-hidden /> Core path isolated</span></div>
        </div>
      </section>

      <section className="enterprise-section runtime-section" data-reveal>
        <div className="runtime-console">
          <div className="runtime-topline"><span><i /> LIVE RUNTIME</span><code>pipeline/{runtime?.pipeline_version ?? "connecting"}</code></div>
          <div className="runtime-grid">
            {(runtime?.engines ?? []).map((engine) => <article key={engine.name} className={engine.available ? "online" : "standby"} title={engine.reason ?? engine.version}><span className="engine-signal" /><div><strong>{engineLabels[engine.name] ?? engine.name}</strong><small>{engine.capabilities.join(" · ")} / {engine.devices.join(" · ")}</small></div><b>{engine.available ? "ONLINE" : "ON DEMAND"}</b></article>)}
            {!runtime && <p className="runtime-loading">Reading the local engine registry…</p>}
          </div>
          <div className="runtime-policies">
            <span><i>ROUTER</i><b>DETERMINISTIC POLICY</b></span>
            <span><i>VLM</i><b>{runtime?.vlm_adapter_configured ? "LOCAL ADAPTER ONLINE" : runtime?.vlm_policy_enabled ? "POLICY READY · NO ADAPTER" : "DISABLED"}</b></span>
            <span><i>LLM</i><b>{runtime?.llm_in_evidence_path ? "EVIDENCE PATH ACTIVE" : "NO EVIDENCE-PATH USE"}</b></span>
          </div>
          <p className="runtime-note">Optional engines are transparent: “on demand” means the adapter is registered but its local model package is not installed. Processing continues through the available, confidence-gated route.</p>
        </div>
      </section>

      <section className="enterprise-section domain-section" data-reveal>
        <SectionHeading label="Multidisciplinary by design" title="One representation across scientific domains." copy="The core models document primitives—not a narrow subject taxonomy—so mixed PDFs can combine prose, notation, code, visuals, tables, and accessibility content on the same page. Domain meaning remains traceable to the source." />
        <div className="domain-grid">{domains.map(([name, detail], index) => <article key={name}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{name}</strong><small>{detail}</small></div></article>)}</div>
      </section>

      <section id="trust" className="enterprise-section trust-section" data-reveal>
        <SectionHeading label="Evidence controls" title="Designed for evidence-sensitive workflows." copy="Machine-readable does not mean unverifiable. Every output is anchored to the document, and every uncertain recognition is surfaced instead of polished into false certainty." />
        <div className="trust-grid">
          <article><span className="trust-icon">⌂</span><h3>Local-first control</h3><p>Files, database, models, and processing stay on the host you operate. The current runtime requires no document upload to a third-party cloud.</p><small>Local storage · LAN-ready · self-operated</small></article>
          <article><span className="trust-icon">◎</span><h3>Element-level provenance</h3><p>Method, engine, version, model, pipeline version, source page, cache state, and processing history travel with the element.</p><small>Traceable · versioned · inspectable</small></article>
          <article><span className="trust-icon">◇</span><h3>Confidence as data</h3><p>Calibrated signals are preserved where engines expose them. Missing confidence is represented honestly and routed to review.</p><small>Accepted · uncertain · needs review</small></article>
          <article><span className="trust-icon">↺</span><h3>Original always available</h3><p>The input PDF is retained intact and identified by SHA-256, while page images and semantic overlays provide a direct visual audit trail.</p><small>Immutable evidence · visual verification</small></article>
        </div>
      </section>

      <section className="enterprise-section deployment-section" data-reveal>
        <div className="deployment-copy"><p className="eyebrow">Deployment foundation</p><h2>From a private workstation to a managed document service.</h2><p>The application already separates the web experience, API, background processing, storage, engine registry, schema, validation, and exporters—ready to be hardened behind your identity, billing, tenant isolation, and operations stack.</p><a href="#workspace">Run the local platform <span>→</span></a></div>
        <div className="deployment-specs"><div><span>Interfaces</span><strong>Web application · REST API · CLI</strong></div><div><span>Compute</span><strong>CPU · CUDA · Apple MPS adapters</strong></div><div><span>Execution</span><strong>Background jobs · synchronous · queue-ready</strong></div><div><span>Storage</span><strong>Local filesystem · SQLite · PostgreSQL-ready</strong></div><div><span>Network</span><strong>Loopback by default · private LAN sharing</strong></div></div>
      </section>

      <section id="workspace" className="workspace" data-reveal>
        <div className="workspace-heading"><div><p className="eyebrow">Live workspace</p><h2>Transform a scientific PDF now</h2></div><p>PDF only · processed locally · original file preserved</p></div>
        <div className="upload-panel panel">
          <div className={`drop-zone${dragging ? " dragging" : ""}${selected ? " selected" : ""}`} onDragEnter={() => setDragging(true)} onDragLeave={() => setDragging(false)} onDragOver={(event) => event.preventDefault()} onDrop={drop} onClick={() => input.current?.click()} role="button" tabIndex={0} onKeyDown={(event) => event.key === "Enter" && input.current?.click()}>
            <input ref={input} type="file" accept="application/pdf,.pdf" hidden onChange={(event: ChangeEvent<HTMLInputElement>) => choose(event.target.files?.[0])} />
            <span className="upload-icon" aria-hidden>{selected ? "✓" : "↑"}</span><div><strong>{selected ? selected.name : "Drop a scientific PDF here"}</strong><small>{selected ? `${(selected.size / 1024 / 1024).toFixed(2)} MB · ready to process` : "Drag and drop, or click anywhere in this area to browse"}</small></div>{!selected && <span className="browse-pill">Browse PDF</span>}
          </div>
          <button className="primary-button" disabled={!selected || uploading} onClick={() => void upload()}>{uploading ? "Uploading…" : "Upload and process"}<span aria-hidden>→</span></button>
          {message && <p className="notice" role="status">{message}</p>}{jobId && <JobProgress jobId={jobId} onComplete={handleJobComplete} />}
        </div>
      </section>

      <section id="library" className="recent" data-reveal>
        <div className="section-title"><div><p className="eyebrow">Local library</p><h2>Recent documents</h2></div><button className="text-button" onClick={() => void refresh()}>Refresh</button></div>
        <div className="library-metrics" aria-label="Library statistics"><span><strong>{documents.length}</strong> documents</span><span><strong>{pageCount}</strong> pages</span><span><strong>{completedCount}</strong> ready</span></div>
        {documents.length === 0 ? <div className="empty-state"><p>No documents yet.</p><span>Your locally processed library will appear here.</span></div> : <div className="document-grid">{documents.map((document, index) => <DocumentCard key={document.id} document={document} index={index} />)}</div>}
      </section>

      <section className="enterprise-cta" data-reveal><div><p className="eyebrow">Evidence in. Intelligence out.</p><h2>Make scientific knowledge computable.</h2><p>Start with the local platform today. Add identity, tenant controls, billing, and managed infrastructure when you are ready to commercialize.</p></div><button onClick={() => { document.querySelector("#workspace")?.scrollIntoView({ behavior: "smooth" }); input.current?.click(); }}>Choose a PDF <span>↗</span></button></section>

      <footer className="site-footer"><div className="footer-brand"><Image src={brandArtwork} alt="" width={40} height={40} /><div><strong>NeetiTech</strong><small>Scientific Document Intelligence</small></div></div><p>Local-first conversion from complex PDFs to verifiable structured data.</p><nav aria-label="Footer navigation"><a href="#workspace">Process PDF</a><a href="#library">Local library</a><Link href="/settings">Settings</Link></nav></footer>
    </main>
  );
}

function SectionHeading({ label, title, copy }: { label: string; title: string; copy: string }) {
  return <div className="section-intro"><p className="eyebrow">{label}</p><div><h2>{title}</h2><p>{copy}</p></div></div>;
}

function DocumentCard({ document, index }: { document: DocumentSummary; index: number }) {
  const progress = document.latest_job?.progress ?? (document.status === "completed" ? 1 : 0);
  return <article className="document-card panel" style={{ "--card-index": index } as CSSProperties}><div className="file-glyph">PDF</div><div className="document-card-main"><div className="card-heading"><h3 title={document.filename}>{document.filename}</h3><span className={`status status-${document.status}`}>{document.status}</span></div><p>{document.page_count} {document.page_count === 1 ? "page" : "pages"} · {document.sha256.slice(0, 10)}…</p><div className="progress-track"><span style={{ width: `${Math.round(progress * 100)}%` }} /></div><div className="card-footer"><span>{document.latest_job?.stage ?? "Stored locally"}</span>{document.status === "completed" ? <div className="card-actions"><a className="selectable-pdf-link" href={`${API_URL}/api/documents/${document.id}/exports/pdf`} target="_blank" rel="noreferrer">Selectable PDF ↗</a><a className="accessible-link" href={`${API_URL}/api/documents/${document.id}/exports/html`} target="_blank" rel="noreferrer">Screen reader HTML ↗</a><Link className="open-link" href={`/viewer/${document.id}`}>Inspect →</Link></div> : <span>{Math.round(progress * 100)}%</span>}</div></div></article>;
}
