import { expect, test } from "@playwright/test";
import path from "node:path";

const formulaPdf = path.resolve(
  __dirname,
  "../../benchmark/datasets/source-documents/input/Formula.pdf",
);

function silentWav(): Buffer {
  const sampleRate = 24_000;
  const samples = 2_400;
  const dataBytes = samples * 2;
  const wav = Buffer.alloc(44 + dataBytes);
  wav.write("RIFF", 0);
  wav.writeUInt32LE(36 + dataBytes, 4);
  wav.write("WAVE", 8);
  wav.write("fmt ", 12);
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(sampleRate, 24);
  wav.writeUInt32LE(sampleRate * 2, 28);
  wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34);
  wav.write("data", 36);
  wav.writeUInt32LE(dataBytes, 40);
  return wav;
}

test("upload a PDF and open the processed viewer", async ({ page }) => {
  const narrationRequests: Array<{ page_number: number; element_id?: string; voice: string }> = [];
  await page.route("**/api/narration/capabilities", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      status: 200,
      body: JSON.stringify({
        configured: true,
        provider: "openai",
        model: "gpt-4o-mini-tts",
        default_voice: "marin",
        voices: [
          { id: "marin", label: "Marin — warm and natural", recommended: true },
          { id: "cedar", label: "Cedar — clear and natural", recommended: true },
        ],
        ai_generated: true,
        remote_processing: true,
        privacy_notice: "Only recovered narration text is sent after selection.",
      }),
    });
  });
  await page.route("**/api/documents/*/narration", async (route) => {
    narrationRequests.push(route.request().postDataJSON());
    await route.fulfill({
      body: silentWav(),
      contentType: "audio/wav",
      status: 200,
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "From source page to canonical SDR" })).toBeVisible();
  await expect(page.locator(".pipeline-band li")).toHaveCount(5);
  const intelligenceHeading = page.getByRole("heading", { name: "AI where recognition helps. Determinism where truth matters." });
  await intelligenceHeading.scrollIntoViewIfNeeded();
  await expect(intelligenceHeading).toBeVisible();
  await expect(page.getByText("Not present in the core evidence path")).toBeVisible();
  await page.getByText("LIVE RUNTIME").scrollIntoViewIfNeeded();
  await expect(page.getByText("LIVE RUNTIME")).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles(formulaPdf);
  await page.getByRole("button", { name: "Upload and process" }).click();
  await expect(page.getByText(/completed/i).first()).toBeVisible({ timeout: 120_000 });
  const formulaCard = page.getByRole("article").filter({ hasText: "Formula.pdf" });
  await formulaCard.getByRole("link", { name: "Inspect →" }).click();
  await expect(page.getByLabel(/PDF page 1/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Natural narration" })).toBeVisible();
  await expect(page.getByText("AI-generated voice", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Listen to page" })).toBeEnabled();
  await expect(page.getByLabel("Read on click")).toBeChecked();
  await page.locator("label.toggle").click();
  await expect(page.getByLabel("Show semantic regions")).toBeChecked();
  const equation = page.locator('.semantic-region[title^="equation"]').first();
  await expect(equation).toBeVisible();
  await equation.click();
  await expect.poll(() => narrationRequests.length).toBe(1);
  expect(narrationRequests[0].page_number).toBe(1);
  expect(narrationRequests[0].element_id).toBeTruthy();
  expect(narrationRequests[0].voice).toBe("marin");
  const audio = page.locator("audio");
  await expect(audio).toBeVisible();
  await expect.poll(() => audio.evaluate((player) => player.currentTime > 0 || player.ended)).toBe(true);
  await expect(page.getByRole("heading", { name: "equation" })).toBeVisible();
  await expect(page.locator(".metadata-list dd").filter({ hasText: /^formula_(recognition|ocr_fallback)$/ })).toBeVisible();

  const paragraph = page.locator('.semantic-region[title^="paragraph"]').first();
  await expect(paragraph).toBeVisible();
  await paragraph.click();
  await expect.poll(() => narrationRequests.length).toBe(2);
  expect(narrationRequests[1].element_id).toBeTruthy();
  expect(narrationRequests[1].element_id).not.toBe(narrationRequests[0].element_id);
  await expect(page.getByRole("heading", { name: "paragraph" })).toBeVisible();

  const selectablePdfLink = page.getByRole("link", {
    name: "Open visually identical PDF with selectable text",
  });
  await expect(selectablePdfLink).toBeVisible();
  const selectablePdfUrl = await selectablePdfLink.getAttribute("href");
  expect(selectablePdfUrl).toBeTruthy();
  const selectablePdf = await page.request.get(selectablePdfUrl!);
  expect(selectablePdf.status()).toBe(200);
  expect(selectablePdf.headers()["content-type"]).toBe("application/pdf");
  expect(selectablePdf.headers()["content-disposition"]).toContain("inline");

  const accessiblePagePromise = page.waitForEvent("popup");
  await page.getByRole("link", { name: "Open accessible HTML for screen readers" }).click();
  const accessiblePage = await accessiblePagePromise;
  await expect(accessiblePage.locator("main#main-content")).toBeVisible();
  await expect(accessiblePage.getByRole("heading", { name: "Source page 1" })).toBeVisible();
  await expect(accessiblePage.locator(".document-element").first()).toBeVisible();

  await accessiblePage.addScriptTag({
    path: path.resolve(__dirname, "../../node_modules/axe-core/axe.min.js"),
  });
  const accessibilityViolations = await accessiblePage.evaluate(async () => {
    const axe = (window as unknown as {
      axe: { run: () => Promise<{ violations: Array<{ id: string }> }> };
    }).axe;
    return (await axe.run()).violations.map((violation) => violation.id);
  });
  expect(accessibilityViolations).toEqual([]);
});
