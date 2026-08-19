import { describe, expect, it } from "vitest";
import { API_URL, documentsApi } from "@/lib/api";

describe("same-origin API routing", () => {
  it("uses the Next.js API proxy by default", () => {
    expect(API_URL).toBe("");
    expect(documentsApi.fileUrl("doc_example")).toBe("/api/documents/doc_example/file");
  });
});
