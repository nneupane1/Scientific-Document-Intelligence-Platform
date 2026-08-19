export interface ViewportSize {
  width: number;
  height: number;
}

export function bboxToCss(
  bbox: [number, number, number, number],
  source: ViewportSize,
  viewport: ViewportSize,
) {
  if (source.width <= 0 || source.height <= 0) throw new Error("source dimensions must be positive");
  const scaleX = viewport.width / source.width;
  const scaleY = viewport.height / source.height;
  return {
    left: bbox[0] * scaleX,
    top: bbox[1] * scaleY,
    width: (bbox[2] - bbox[0]) * scaleX,
    height: (bbox[3] - bbox[1]) * scaleY,
  };
}
