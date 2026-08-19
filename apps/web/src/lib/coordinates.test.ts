import { describe, expect, it } from "vitest";
import { bboxToCss } from "./coordinates";

describe("bboxToCss", () => {
  it("scales PyMuPDF top-left coordinates into the PDF.js viewport", () => {
    expect(bboxToCss([10, 20, 110, 220], { width: 200, height: 400 }, { width: 400, height: 800 })).toEqual({ left: 20, top: 40, width: 200, height: 400 });
  });
});
