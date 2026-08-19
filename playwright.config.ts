import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 120_000,
  use: { baseURL, trace: "retain-on-failure" },
  webServer: [
    { command: ".venv/bin/uvicorn scidoc_api.main:app --host 127.0.0.1 --port 8000", port: 8000, reuseExistingServer: true },
    { command: "npm run dev", port: 3000, reuseExistingServer: true },
  ],
});
