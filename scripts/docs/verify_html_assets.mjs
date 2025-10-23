#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import url from "node:url";
import puppeteer from "puppeteer";

const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..", "..");

const args = new Map(Object.entries({
  "--in": null,
  "--timeout": "60000"
}));

for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i];
  const value = process.argv[i + 1] ?? null;
  if (args.has(key)) args.set(key, value);
}

const inFile = path.resolve(args.get("--in") ?? path.join(ROOT, "docs/build/TDD.html"));
const timeout = Number.parseInt(args.get("--timeout") ?? "60000", 10);

await fs.access(inFile);
const inUrl = url.pathToFileURL(inFile).href;

const failures = new Map();
const responses = [];

const browser = await puppeteer.launch({
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
});

try {
  const page = await browser.newPage();

  page.on("requestfailed", (request) => {
    failures.set(request.url(), request.failure()?.errorText ?? "request failed");
  });

  page.on("response", (response) => {
    const status = response.status();
    if (status >= 400) {
      responses.push({
        url: response.url(),
        status,
        statusText: response.statusText()
      });
    }
  });

  await page.goto(inUrl, { waitUntil: ["load", "networkidle2"], timeout });

  const brokenImages = await page.$$eval("img", (nodes) => nodes
    .filter((img) => !img.complete || typeof img.naturalWidth === "undefined" || img.naturalWidth === 0)
    .map((img) => ({
      src: img.getAttribute("src") ?? "",
      alt: img.getAttribute("alt") ?? ""
    }))
  );

  const stylesheetIssues = await page.$$eval(
    'link[rel~="stylesheet"]',
    (links) => links
      .filter((link) => !link.sheet || link.sheet.disabled)
      .map((link) => link.getAttribute("href") || link.href || "(inline stylesheet)")
  );

  const problems = [];

  if (failures.size > 0) {
    for (const [failedUrl, reason] of failures.entries()) {
      problems.push(`request failed: ${failedUrl} (${reason})`);
    }
  }

  for (const resp of responses) {
    problems.push(`HTTP ${resp.status} ${resp.statusText || ""} loading ${resp.url}`);
  }

  for (const img of brokenImages) {
    problems.push(`broken image src="${img.src}" alt="${img.alt}"`);
  }

  for (const sheetHref of stylesheetIssues) {
    problems.push(`stylesheet could not be loaded: ${sheetHref}`);
  }

  if (problems.length > 0) {
    console.error("Asset verification failed:");
    for (const problem of problems) {
      console.error(`  - ${problem}`);
    }
    process.exitCode = 1;
  } else {
    console.log(`All assets loaded for ${inFile}`);
  }
} finally {
  await browser.close();
}
