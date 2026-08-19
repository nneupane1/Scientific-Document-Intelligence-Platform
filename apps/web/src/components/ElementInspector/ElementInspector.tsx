"use client";

import katex from "katex";
import type { SdrElement } from "@/types/sdr";

export default function ElementInspector({ element, pageNumber, onClose }: { element: SdrElement | null; pageNumber: number; onClose: () => void }) {
  if (!element) return <aside className="inspector inspector-empty"><p className="eyebrow">Inspector</p><h2>Select a semantic region</h2><p>Click text, equations, or figures on the source page to inspect evidence and copy recognized content.</p></aside>;
  const latex = element.content.latex ?? element.content.normalized_latex;
  return <aside className="inspector">
    <div className="inspector-heading"><div><p className="eyebrow">Page {pageNumber}</p><h2>{element.element_type.replaceAll("_", " ")}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close inspector">×</button></div>
    {latex && <div className="rendered-math" dangerouslySetInnerHTML={{ __html: safeKatex(latex) }} />}
    {element.content.text && <InspectorValue label="Transcription" value={element.content.text} />}
    {element.content.alt_text && <InspectorValue label="Accessible interpretation" value={element.content.alt_text} copy />}
    {latex && <InspectorValue label="LaTeX" value={latex} copy />}
    {element.content.unicode && <InspectorValue label="Unicode" value={element.content.unicode} copy />}
    {element.content.mathml && <InspectorValue label="MathML" value={element.content.mathml} copy collapsed />}
    <dl className="metadata-list"><div><dt>Confidence</dt><dd>{element.confidence === null ? "Unavailable" : `${(element.confidence * 100).toFixed(1)}%`}<small>{element.confidence_source}</small></dd></div><div><dt>Status</dt><dd><span className={`status status-${element.review_status}`}>{element.review_status}</span></dd></div><div><dt>Engine</dt><dd>{element.provenance.engine}<small>{element.provenance.engine_version ?? "version unavailable"}</small></dd></div><div><dt>Method</dt><dd>{element.provenance.method}</dd></div><div><dt>Bounding box</dt><dd className="mono">[{element.bbox.map((value) => value.toFixed(1)).join(", ")}]</dd></div><div><dt>Element ID</dt><dd className="mono wrap">{element.id}</dd></div></dl>
    {element.warnings.length > 0 && <div className="warnings"><strong>Processing notes</strong><ul>{element.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
  </aside>;
}

function safeKatex(value: string) { try { return katex.renderToString(value, { throwOnError: false, displayMode: true, strict: false }); } catch { return "<span>Unable to render formula</span>"; } }

function InspectorValue({ label, value, copy = false, collapsed = false }: { label: string; value: string; copy?: boolean; collapsed?: boolean }) {
  return <section className="inspector-value"><div><strong>{label}</strong>{copy && <button className="copy-button" onClick={() => void navigator.clipboard.writeText(value)}>Copy</button>}</div><pre className={collapsed ? "collapsed" : ""}>{value}</pre></section>;
}
