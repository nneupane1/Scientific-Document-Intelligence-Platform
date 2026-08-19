"use client";

import { CSSProperties } from "react";
import { bboxToCss } from "@/lib/coordinates";
import type { PageDetail, SdrElement } from "@/types/sdr";

export default function SemanticOverlay({ page, viewport, debug, selected, onSelect }: { page: PageDetail; viewport: { width: number; height: number }; debug: boolean; selected: string | null; onSelect: (element: SdrElement) => void }) {
  return <div className={`semantic-layer ${debug ? "debug" : ""}`} style={{ width: viewport.width, height: viewport.height }}>{page.elements.map((element) => {
    const box = bboxToCss(element.bbox, page, viewport);
    const style = { left: box.left, top: box.top, width: box.width, height: box.height, "--region-color": color(element.element_type) } as CSSProperties;
    const isText = !["equation", "figure", "table", "molecule", "circuit", "chart", "diagram"].includes(element.element_type);
    return <button key={element.id} type="button" className={`semantic-region ${isText ? "text-region" : "object-region"} ${selected === element.id ? "selected" : ""}`} style={style} onClick={() => { window.dispatchEvent(new Event("scidoc:narration-gesture")); onSelect(element); }} aria-label={`Select and read ${element.element_type.replaceAll("_", " ")} ${element.reading_order + 1}`} aria-pressed={selected === element.id} title={`${element.element_type} ${element.confidence?.toFixed(2) ?? "—"}`}>
      {debug && <span className="region-label">{element.element_type.toUpperCase()} {element.confidence?.toFixed(2) ?? "—"}</span>}
      {isText && element.content.text && <span className="selectable-text">{element.content.text}</span>}
    </button>;
  })}</div>;
}

function color(type: string) {
  if (["equation", "chemical_equation", "molecule"].includes(type)) return "#a45d70";
  if (["figure", "diagram", "circuit"].includes(type)) return "#756d9c";
  if (["table", "chart"].includes(type)) return "#43877f";
  if (type === "braille") return "#635c9a";
  return "#52756f";
}
