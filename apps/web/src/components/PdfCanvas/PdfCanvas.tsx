"use client";

import { useEffect, useRef, useState } from "react";
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from "pdfjs-dist";

export default function PdfCanvas({ url, pageNumber, onViewport }: { url: string; pageNumber: number; onViewport: (size: { width: number; height: number }) => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const host = useRef<HTMLDivElement>(null);
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let loadingTask: PDFDocumentLoadingTask | null = null;
    void (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
        loadingTask = pdfjs.getDocument({ url });
        const loaded = await loadingTask.promise;
        if (active) setDocument(loaded);
      } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : "Could not load PDF"); }
    })();
    return () => {
      active = false;
      if (loadingTask) void loadingTask.destroy();
    };
  }, [url]);

  useEffect(() => {
    if (!document || !canvas.current || !host.current) return;
    let task: RenderTask | null = null; let cancelled = false;
    void (async () => {
      const page = await document.getPage(pageNumber);
      const base = page.getViewport({ scale: 1 });
      const available = Math.max(320, Math.min(host.current?.clientWidth ?? 900, 1100));
      const viewport = page.getViewport({ scale: available / base.width });
      const outputScale = Math.min(window.devicePixelRatio || 1, 2);
      const target = canvas.current;
      if (!target || cancelled) return;
      target.width = Math.floor(viewport.width * outputScale); target.height = Math.floor(viewport.height * outputScale);
      target.style.width = `${viewport.width}px`; target.style.height = `${viewport.height}px`;
      task = page.render({
        canvas: target,
        viewport,
        transform: outputScale === 1 ? undefined : [outputScale, 0, 0, outputScale, 0, 0],
      });
      await task.promise; if (!cancelled) onViewport({ width: viewport.width, height: viewport.height });
    })().catch((reason) => { if (!cancelled && reason?.name !== "RenderingCancelledException") setError(String(reason)); });
    return () => { cancelled = true; task?.cancel(); };
  }, [document, pageNumber, onViewport]);

  return <div ref={host} className="pdf-host">{error ? <div className="pdf-error">{error}</div> : <canvas ref={canvas} aria-label={`PDF page ${pageNumber}`} />}</div>;
}
