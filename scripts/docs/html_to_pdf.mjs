#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import url from "node:url";
import puppeteer from "puppeteer";

// Resolve repo root (two levels up from this script)
const __filename = url.fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..", "..");

// Parse CLI args
const args = new Map(Object.entries({
  "--in": null,
  "--out": null,
  "--size": "Letter",
  "--landscape": "false"
}));

for (let i = 2; i < process.argv.length; i += 2) {
  if (args.has(process.argv[i])) args.set(process.argv[i], process.argv[i + 1] ?? null);
}

const inFile = path.resolve(args.get("--in") ?? path.join(ROOT, "docs/TDD.html"));
const outFile = path.resolve(args.get("--out") ?? path.join(ROOT, "docs/TDD.pdf"));
const format = args.get("--size") || "Letter";
const landscape = (args.get("--landscape") || "false") === "true";

// Inline header/footer templates
const header = `
<style>
  .head { font-family: system-ui, "DejaVu Sans", sans-serif; font-size:10px;
          width:100%; padding:4px 12px; border-bottom:1px solid #ccc; color:#555; }
  .head .title { font-weight:600; }
</style>
<div class="head">
  <span class="title">uDocket — Technical Design Document</span>
  <span> — Platform Architecture &amp; Compliance Specification</span>
</div>`;

const footer = `
<style>
  .foot { font-family: system-ui, "DejaVu Sans", sans-serif; font-size:9px;
          width:100%; padding:4px 12px; border-top:1px solid #ccc; color:#777;
          display:flex; justify-content:center; gap:8px;}
</style>
<div class="foot">
  <span>Confidential · Last updated 2025-10-23</span>
  <span>· Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>`;

// Ensure the source HTML exists before handing off to Puppeteer
await fs.access(inFile);
const inUrl = url.pathToFileURL(inFile).href;

const browser = await puppeteer.launch({
  // Use bundled Chromium, or set executablePath if you installed system chromium
  // executablePath: "/usr/bin/chromium",
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
});
const page = await browser.newPage();
console.log(`Loading HTML: ${inUrl}`);
await page.goto(inUrl, { waitUntil: ["load", "networkidle2"], timeout: 0 });
await page.emulateMediaType("screen");

await page.pdf({
  path: outFile,
  format,
  landscape,
  margin: { top: "1in", right: "0.5in", bottom: "1in", left: "0.5in" },
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: header,
  footerTemplate: footer,
  timeout: 0
});
await browser.close();
console.log(`✅ Wrote ${outFile}`);
