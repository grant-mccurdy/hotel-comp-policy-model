#!/usr/bin/env node
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";

const projectRoot = path.resolve(import.meta.dirname, "..");
const requireFromHere = createRequire(import.meta.url);

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (originalError) {
    const candidates = [
      process.env.PLAYWRIGHT_MODULE_DIR,
      path.resolve(projectRoot, "..", "grant-mccurdy.github.io", "node_modules"),
      ...(process.env.NODE_PATH ? process.env.NODE_PATH.split(path.delimiter) : []),
    ].filter(Boolean);
    for (const candidate of candidates) {
      for (const specifier of [path.join(candidate, "playwright"), candidate]) {
        try {
          return requireFromHere(specifier);
        } catch {
          // Try the next local module path.
        }
      }
    }
    throw originalError;
  }
}

function embeddedHtml() {
  const source = fs.readFileSync(path.join(projectRoot, "cloudflare", "src", "ui.py"), "utf8");
  const match = source.match(/^DECISION_DESK_HTML = r'''([\s\S]*)'''\s*$/);
  if (!match) throw new Error("Could not read the embedded Worker UI module.");
  return match[1];
}

const sampleDecision = {
  recommendation: {
    comp_code: "late_checkout",
    comp_label: "Late checkout + personal manager note",
    guest_facing_value: 100,
    internal_cost_low: 8,
    internal_cost_high: 45,
    delivery_timing: "Offer during the current stay after confirming operational availability.",
    hospitality_note_template: "Acknowledge the room-readiness delay and confirm the recovery gesture personally.",
  },
  alternatives: [
    { comp_label: "Palma credit", guest_facing_value: 75, internal_cost_low: 25, internal_cost_high: 45 },
    { comp_label: "In-room amenity", guest_facing_value: 60, internal_cost_low: 18, internal_cost_high: 35 },
  ],
  reasoning: { plain_language: ["The serious hotel-responsible delay establishes the recovery floor.", "Late checkout clears the configured fit and availability checks."] },
  required_confirmations: ["Confirm late-checkout availability before offering the gesture."],
  confidence: { input_sensitivity_stability: 0.91, level: "high", meaning: "The selected gesture is stable across nearby synthetic inputs." },
  approval: { approval_path: "Manager" },
};

const server = http.createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");
  if (url.pathname === "/v1/recommend" && request.method === "POST") {
    response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify(sampleDecision));
    return;
  }
  if (url.pathname === "/" || url.pathname === "/index.html") {
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    response.end(embeddedHtml());
    return;
  }
  response.writeHead(404).end();
});

await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const address = server.address();
const baseUrl = `http://127.0.0.1:${address.port}`;
const { chromium } = await loadPlaywright();
const browser = await chromium.launch({ headless: true });
const failures = [];
const results = [];
const screenshotDir = path.join(projectRoot, "tmp", "worker-ui-smoke");
fs.mkdirSync(screenshotDir, { recursive: true });

try {
  for (const [label, width, height] of [["desktop", 1440, 1000], ["mobile", 390, 844]]) {
    const page = await browser.newPage({ viewport: { width, height } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    const sampleButton = page.locator("#sample-button");
    const firstView = await sampleButton.evaluate((button) => {
      const rect = button.getBoundingClientRect();
      return rect.top >= 0 && rect.bottom <= window.innerHeight;
    });
    const assumptionsClosed = !(await page.locator(".advanced-inputs").getAttribute("open"));
    await sampleButton.click();
    await page.getByText("Late checkout + personal manager note").waitFor({ state: "visible", timeout: 3000 });
    const overflow = await page.evaluate(() =>
      Array.from(document.querySelectorAll("body *"))
        .filter((element) => {
          if (element.closest("table")) return false;
          const rect = element.getBoundingClientRect();
          return rect.width && rect.height && (rect.right > document.documentElement.clientWidth + 2 || rect.left < -2);
        })
        .map((element) => String(element.className))
        .slice(0, 5)
    );
    const resultText = await page.locator("#result").innerText();
    await page.evaluate(() => {
      document.documentElement.style.scrollBehavior = "auto";
      window.scrollTo(0, 0);
    });
    const screenshotPath = path.join(screenshotDir, `${label}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const result = {
      label,
      firstView,
      assumptionsClosed,
      recommendationRendered: resultText.includes("Closest feasible alternatives") && resultText.includes("Manager"),
      overflow,
      errors,
      screenshot: path.relative(projectRoot, screenshotPath),
    };
    results.push(result);
    if (!firstView || !assumptionsClosed || !result.recommendationRendered || overflow.length || errors.length) failures.push(result);
    await page.close();
  }
} finally {
  await browser.close();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}

console.log(JSON.stringify(results, null, 2));
if (failures.length) process.exit(1);
