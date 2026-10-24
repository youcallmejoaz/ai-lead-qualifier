// Records every demo clip as a 1920x1080 H.264 MP4.
//
//   cd clips && npm install && node record.mjs            # all clips
//   node record.mjs C04 C08                               # some clips
//   node record.mjs --finalize                            # manifest + proposal cut only
//
// The app must be running with the sample data and DEMO_MODE=1 (APP_URL, default
// http://127.0.0.1:8000). Frames come from the Chrome screencast at high JPEG quality
// and are resampled to a constant 30 fps, then encoded with ffmpeg (libx264).

import { execFileSync, spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const BASE = process.env.APP_URL ?? "http://127.0.0.1:8000";
const FPS = 30;
const W = 1920;
const H = 1080;
const CURSOR_JS = fs.readFileSync(path.join(HERE, "cursor.js"), "utf8");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------- app API
async function api(p, opts = {}) {
  const res = await fetch(BASE + p, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) throw new Error(`${opts.method ?? "GET"} ${p}: ${res.status} ${await res.text()}`);
  return res.json();
}
const reset = (process = true) => api(`/api/admin/reset?process=${process}`, { method: "POST" });
const pending = () => api("/api/review?status=pending");
const approveItem = (id) => api(`/api/review/${id}/approve`, { method: "POST", body: "{}" });
async function itemFor(extId) {
  return (await pending()).find((i) => i.message.external_id === extId);
}
async function waitIdle() {
  for (let i = 0; i < 600; i++) {
    const h = await api("/api/health");
    if (!h.processing && h.unprocessed === 0) return;
    await sleep(200);
  }
  throw new Error("inbox never finished processing");
}

// ---------------------------------------------------------------- recording
class Recorder {
  constructor(page, cdp) {
    this.page = page;
    this.cdp = cdp;
    this.frames = [];
    this.mouse = { x: W * 0.62, y: H * 0.55 };
    cdp.on("Page.screencastFrame", async ({ data, metadata, sessionId }) => {
      if (this.recording) this.frames.push({ t: metadata.timestamp, buf: Buffer.from(data, "base64") });
      await cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
    });
  }

  async start() {
    await this.page.mouse.move(this.mouse.x, this.mouse.y);
    await sleep(150);
    this.recording = true;
    this.t0 = Date.now() / 1000;
    await this.cdp.send("Page.startScreencast", { format: "jpeg", quality: 95, maxWidth: W, maxHeight: H });
    // Nudge a repaint so the first frame arrives straight away.
    await this.page.evaluate(() => document.body.offsetHeight);
  }

  async stop() {
    this.t1 = Date.now() / 1000;
    await this.cdp.send("Page.stopScreencast").catch(() => {});
    this.recording = false;
  }

  // Human paced cursor movement with ease in and out.
  async moveTo(x, y, ms) {
    const from = { ...this.mouse };
    const dist = Math.hypot(x - from.x, y - from.y);
    const duration = ms ?? Math.min(900, 280 + dist * 0.45);
    const steps = Math.max(8, Math.round(duration / 16));
    for (let i = 1; i <= steps; i++) {
      const k = i / steps;
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      await this.page.mouse.move(from.x + (x - from.x) * e, from.y + (y - from.y) * e);
      await sleep(duration / steps);
    }
    this.mouse = { x, y };
  }

  async center(selector, { scroll = true } = {}) {
    const loc = this.page.locator(selector).first();
    if (scroll) await loc.scrollIntoViewIfNeeded();
    const box = await loc.boundingBox();
    if (!box) throw new Error(`not visible: ${selector}`);
    return { x: box.x + box.width / 2, y: box.y + box.height / 2, box };
  }

  async hover(selector, pause = 500) {
    const { x, y } = await this.center(selector);
    await this.moveTo(x, y);
    await sleep(pause);
  }

  async click(selector, { pause = 700, offset } = {}) {
    let { x, y, box } = await this.center(selector);
    if (offset) {
      x = box.x + offset.x;
      y = box.y + offset.y;
    }
    await this.moveTo(x, y);
    await sleep(220);
    await this.page.mouse.down();
    await sleep(90);
    await this.page.mouse.up();
    await sleep(pause);
  }

  async type(text, delay = 45) {
    for (const ch of text) {
      await this.page.keyboard.type(ch);
      await sleep(ch === " " ? delay * 0.6 : delay + Math.random() * 25);
    }
  }

  async scrollBy(dy, ms = 900) {
    const steps = Math.round(ms / 30);
    for (let i = 0; i < steps; i++) {
      await this.page.mouse.wheel(0, dy / steps);
      await sleep(30);
    }
  }

  async encode(outFile) {
    if (!this.frames.length) throw new Error("no frames captured");
    const frames = this.frames.sort((a, b) => a.t - b.t);
    const start = Math.max(this.t0, frames[0].t);
    const total = Math.max(1, Math.round((this.t1 - start) * FPS));
    const ff = spawn("ffmpeg", [
      "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
      "-vf", `scale=${W}:${H}:flags=lanczos,format=yuv420p`, "-c:v", "libx264", "-preset", "slow", "-crf", "17",
      "-r", String(FPS), "-movflags", "+faststart", "-an", outFile,
    ], { stdio: ["pipe", "inherit", "inherit"] });
    let idx = 0;
    for (let k = 0; k < total; k++) {
      const t = start + k / FPS;
      while (idx + 1 < frames.length && frames[idx + 1].t <= t) idx++;
      if (!ff.stdin.write(frames[idx].buf)) await new Promise((r) => ff.stdin.once("drain", r));
    }
    ff.stdin.end();
    await new Promise((resolve, reject) => ff.on("close", (code) => (code === 0 ? resolve() : reject(new Error(`ffmpeg exit ${code}`)))));
  }
}

async function record(browser, clip) {
  const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  if (clip.cursor !== false) await context.addInitScript(CURSOR_JS);
  if (clip.init) await context.addInitScript(clip.init.fn, clip.init.arg);
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  const rec = new Recorder(page, cdp);
  const out = path.join(HERE, clip.file);
  try {
    await clip.run(rec, page);
    await rec.stop();
    if (clip.still) await page.screenshot({ path: out.replace(/\.mp4$/, ".png") });
  } finally {
    await context.close();
  }
  await rec.encode(out);
  console.log(`${clip.id}  ${clip.file}  ${duration(out).toFixed(1)}s`);
}

function duration(file) {
  return Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", file]).toString());
}

// Zoom the page for close ups so text is rendered large, not upscaled.
async function closeUp(page, css) {
  await page.addStyleTag({ content: css });
  await sleep(300);
}

// ---------------------------------------------------------------- cards
function cardClip(id, file, html, section, what, init) {
  return {
    id, file, section, what, cursor: false, still: true, init,
    async run(rec, page) {
      await page.goto("file://" + path.join(HERE, html));
      await page.waitForLoadState("networkidle");
      await page.evaluate(() => document.getAnimations().forEach((a) => { a.pause(); a.currentTime = 0; }));
      await rec.start();
      await page.evaluate(() => document.getAnimations().forEach((a) => a.play()));
      await sleep(await page.evaluate(() => window.__duration ?? 8000));
    },
  };
}

function terminalClip(id, file, html, section, what) {
  return {
    id, file, section, what, cursor: false,
    async run(rec, page) {
      await rec.start();
      await page.goto("file://" + path.join(HERE, html));
      await page.waitForFunction(() => document.body.dataset.done === "1", null, { timeout: 60000 });
      await sleep(1800);
    },
  };
}

function costValues() {
  // Cost per enquiry from the recorded Claude calls (list prices, an estimate).
  const prices = { "claude-haiku-5-5": [0.1, 0.5], "claude-sonnet-5-5": [2, 10] };
  const cachePath = path.join(ROOT, "data", "llm_cache.json");
  let cost = null;
  if (fs.existsSync(cachePath)) {
    const entries = Object.values(JSON.parse(fs.readFileSync(cachePath, "utf8")));
    let total = 0;
    for (const e of entries) {
      const key = Object.keys(prices).find((m) => (e.model ?? "").startsWith(m));
      if (key) total += (e.input_tokens / 1e6) * prices[key][0] + (e.output_tokens / 1e6) * prices[key][1];
    }
    if (entries.length >= 80) cost = total / 80;
  }
  return { per_week: 100, minutes: 6, cost_per_enquiry: cost };
}

// ---------------------------------------------------------------- app scenes
const strongLead = async () => (await api("/api/leads")).find((l) => l.qualified && !l.amber && l.source === "form") ?? (await api("/api/leads"))[0];

const CLIPS = [
  cardClip("C01", "C01_before_card.mp4", "cards/C01_before.html", "Problem", "Before card: a crowded inbox and enquiries copied into a CRM by hand"),
  cardClip("C02", "C02_flow_card.mp4", "cards/C02_flow.html", "How it works", "Flow card: form and inbox, AI sorts, scores, draft reply, you approve, CRM and reply"),
  {
    id: "C03", file: "C03_contact_form.mp4", section: "How it works", what: "A new enquiry submitted through the website contact form",
    async run(rec, page) {
      await reset(true);
      await page.goto(BASE + "/contact");
      await page.waitForSelector('[data-testid="contact-form"]');
      await rec.start();
      await sleep(600);
      await rec.click('input[name="name"]', { pause: 120 });
      await rec.type("Maria Lopez", 28);
      for (const [text, delay] of [["maria@crestwayfreight.example", 12], ["Crestway Freight", 20], ["Sorting customer emails", 16],
        ["150 person logistics firm. Can AI sort our customer emails? Budget about $30k, start next month.", 7]]) {
        await page.keyboard.press("Tab");
        await sleep(160);
        await rec.type(text, delay);
      }
      await sleep(300);
      await rec.click('[data-testid="form-submit"]', { pause: 300 });
      await page.waitForSelector('[data-testid="form-sent"]', { timeout: 120000 });
      await sleep(1600);
    },
  },
  {
    id: "C04", file: "C04_inbox_tags.mp4", section: "How it works", what: "Inbox filling with colour tags as the AI sorts each enquiry: Sales, Support, Spam, Other",
    async run(rec, page) {
      await reset(false);
      await page.goto(BASE + "/?delay=70");
      await page.waitForSelector('[data-testid="inbox-row"]');
      await rec.start();
      await sleep(700);
      await rec.click('[data-testid="process-inbox"]', { pause: 200 });
      await rec.moveTo(W * 0.42, H * 0.6, 900);
      await waitIdle();
      await sleep(1500);
    },
  },
  {
    id: "C05", file: "C05_lead_card_closeup.mp4", section: "How it works", what: "Close up of a lead card: score, extracted fields with confidence, one line reason",
    async run(rec, page) {
      const lead = await strongLead();
      await page.goto(BASE + "/");
      await page.click('[data-testid="filter-Sales"]');
      await page.click(`[data-testid="inbox-row"][data-id="${lead.external_id}"]`);
      await page.waitForSelector('[data-testid="lead-card"]');
      await closeUp(page, `.sidebar, .page-head, .toolbar, .card.list { display: none !important; }
        .app { grid-template-columns: 1fr !important; } .split { grid-template-columns: 1fr !important; }
        .sticky > .row, .sticky > .card.pad:last-child { display: none !important; }
        .main { padding-top: 14px; } .sticky { position: static; width: 700px; margin: 0 auto; zoom: 1.68; }`);
      await page.evaluate(() => window.scrollTo(0, 0));
      await rec.start();
      await sleep(500);
      await rec.hover('[data-testid="lead-score"]', 700);
      await rec.hover('[data-testid="lead-reason"]', 900);
      await rec.hover('[data-testid="lead-fields"]', 1400);
      await sleep(600);
    },
  },
  {
    id: "C06", file: "C06_leads_by_score.mp4", section: "Demo", what: "Lead list sorted by score, strongest at the top",
    async run(rec, page) {
      await page.goto(BASE + "/leads");
      await page.waitForSelector('[data-testid="lead-row"]');
      await rec.start();
      await sleep(800);
      await rec.hover('[data-testid="lead-row"]:nth-child(1) [data-testid="score"]', 500);
      await rec.hover('[data-testid="lead-row"]:nth-child(2) [data-testid="score"]', 350);
      await rec.hover('[data-testid="lead-row"]:nth-child(3) [data-testid="score"]', 350);
      await rec.scrollBy(900, 1300);
      await sleep(400);
      await rec.scrollBy(-900, 900);
      await sleep(500);
    },
  },
  {
    id: "C07", file: "C07_crm_duplicate_merged.mp4", section: "Demo", what: "Qualified lead approved into the CRM, duplicate from the same company merged into one record",
    async run(rec, page) {
      await reset(true);
      // Earlier enquiries from the same company, approved off camera.
      for (const ext of ["E001", "E013"]) {
        const item = await itemFor(ext);
        if (item) await approveItem(item.id);
      }
      const target = (await itemFor("E050")) ?? (await itemFor("E013"));
      if (!target) throw new Error("no Harbourline duplicate in the review queue");
      await page.goto(`${BASE}/review?item=${target.id}`);
      await page.waitForSelector('[data-testid="crm-preview"]');
      await rec.start();
      await sleep(700);
      await rec.hover('[data-testid="crm-preview"]', 900);
      await rec.click('[data-testid="approve"]', { pause: 300 });
      await page.waitForSelector('[data-testid="view-crm"]');
      await sleep(1000);
      await rec.click('[data-testid="view-crm"]', { pause: 400 });
      await page.waitForSelector('[data-testid="merged-badge"]');
      await sleep(700);
      await rec.hover('[data-testid="merged-badge"]', 1800);
    },
  },
  {
    id: "C08", file: "C08_sales_draft_edit_approve.mp4", section: "Demo", what: "Sales reply draft opened in the review queue, edited, then approved",
    async run(rec, page) {
      const items = (await pending()).filter((i) => i.kind === "sales" && !i.amber);
      const lead = await strongLead();
      const item = items.find((i) => i.message.external_id === lead.external_id) ?? items[0];
      await page.goto(`${BASE}/review?item=${item.id}`);
      await page.waitForSelector('[data-testid="draft-text"]');
      await rec.start();
      await sleep(900);
      await rec.hover('[data-testid="draft-text"]', 1200);
      await rec.click('[data-testid="edit"]', { pause: 300 });
      const { box } = await rec.center('[data-testid="draft-text"]');
      await rec.click('[data-testid="draft-text"]', { pause: 200, offset: { x: box.width * 0.5, y: box.height - 30 } });
      await page.keyboard.press("Control+End");
      await rec.type("\n\nP.S. Happy to show you a short demo of a similar setup on the call.", 28);
      await sleep(500);
      await rec.click('[data-testid="approve"]', { pause: 300 });
      await page.waitForSelector('[data-testid="toast"]');
      await sleep(1800);
    },
  },
  {
    id: "C09", file: "C09_support_citation_closeup.mp4", section: "Demo", what: "Support email answered from the help docs, close up on the citation",
    async run(rec, page) {
      const items = (await pending()).filter((i) => i.kind === "support" && i.citations.some((c) => c.verified) && !i.amber);
      const item = items.find((i) => i.message.external_id === "E047") ?? items[0];
      await page.goto(`${BASE}/review?item=${item.id}`);
      await page.waitForSelector('[data-testid="citation"]');
      await closeUp(page, `.sidebar, .page-head, .review-list, .actions, .crm-preview { display: none !important; }
        .app, .review-grid { grid-template-columns: 1fr !important; }
        .main { padding-top: 14px; } [data-testid="review-detail"] { width: 1080px; margin: 0 auto; zoom: 1.55; }
        .email-box { max-height: none; } .draft { min-height: 230px; }`);
      await page.evaluate(() => window.scrollTo(0, 0));
      await rec.start();
      await sleep(600);
      await rec.hover('[data-testid="original-email"]', 1100);
      await rec.hover('[data-testid="draft-text"]', 1200);
      await rec.scrollBy(520, 1100);
      await rec.hover('[data-testid="citation"] .citation-head', 900);
      await rec.hover('[data-testid="citation"] .citation-quote', 2200);
    },
  },
  {
    id: "C10", file: "C10_amber_low_confidence.mp4", section: "What could go wrong", what: "Amber flag on a low confidence item, held for a person",
    async run(rec, page) {
      const items = (await pending()).filter((i) => i.amber && !i.flags.includes("injection"));
      const item = items.find((i) => i.kind === "sales") ?? items.find((i) => i.flags.includes("low_confidence")) ?? items[0];
      await page.goto(`${BASE}/review?item=${item.id}`);
      await page.waitForSelector('[data-testid="amber-banner"]');
      await rec.start();
      await sleep(700);
      await rec.hover(`[data-testid="review-item"][data-id="${item.message.external_id}"]`, 700);
      await rec.hover('[data-testid="amber-banner"]', 1900);
      await rec.hover('[data-testid="approve"]', 800);
    },
  },
  {
    id: "C11", file: "C11_injection_flagged.mp4", section: "What could go wrong", what: "Email with hidden instructions, treated as data and flagged",
    async run(rec, page) {
      const item = (await pending()).find((i) => i.flags.includes("injection"));
      if (!item) throw new Error("no injection item in the queue");
      await page.goto(`${BASE}/review?item=${item.id}`);
      await page.waitForSelector('[data-testid="amber-banner"]');
      await rec.start();
      await sleep(700);
      await rec.hover('[data-testid="amber-banner"]', 1800);
      await rec.hover('[data-testid="original-email"]', 2400);
      await sleep(500);
    },
  },
  {
    id: "C12", file: "C12_weekly_summary.mp4", section: "Business value", what: "Weekly summary panel (time saved is a labelled placeholder)",
    async run(rec, page) {
      await page.goto(BASE + "/summary");
      await page.waitForSelector('[data-testid="summary"]');
      await rec.start();
      await sleep(600);
      await rec.hover(".tile:nth-child(2)", 500);
      await rec.hover(".tile:nth-child(4) .placeholder", 1300);
      await rec.moveTo(W * 0.72, H * 0.62, 600);
      await sleep(500);
    },
  },
  terminalClip("C13", "C13_prompt_plan.mp4", "terminal/C13_plan_prompt.html", "How I built it", "Prompt moment: the planning prompt typed in a terminal replay, the plan appears"),
  terminalClip("C14", "C14_prompt_review_queue.mp4", "terminal/C14_review_queue_prompt.html", "How I built it", "Prompt moment: the review queue prompt and the result"),
  cardClip("C15", "C15_safeguards_card.mp4", "cards/C15_safeguards.html", "What could go wrong", "Safeguards card: approval before send, confidence flags, injection guard"),
  cardClip("C16", "C16_value_cost_card.mp4", "cards/C16_value.html", "Business value", "Business value and cost card, labelled as an estimate",
    { fn: (v) => { window.VALUES = v; }, arg: costValues() }),
];

// ---------------------------------------------------------------- manifest + proposal cut
const PROPOSAL = ["C01", "C04", "C07", "C08", "C16"];

function finalize() {
  const rows = CLIPS.filter((c) => fs.existsSync(path.join(HERE, c.file))).map((c) => {
    const d = duration(path.join(HERE, c.file));
    const still = c.still ? ` (still: ${c.file.replace(/\.mp4$/, ".png")})` : "";
    return `| ${c.id} | ${c.file}${still} | ${d.toFixed(1)}s | ${c.what} | ${c.section} |`;
  });
  const cutFiles = PROPOSAL.map((id) => CLIPS.find((c) => c.id === id)).map((c) => path.join(HERE, c.file));
  let cut = "";
  if (cutFiles.every((f) => fs.existsSync(f))) {
    const list = path.join(HERE, "tmp_concat.txt");
    fs.writeFileSync(list, cutFiles.map((f) => `file '${f}'`).join("\n"));
    const out = path.join(HERE, "proposal_cut_silent.mp4");
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", "-movflags", "+faststart", out]);
    fs.rmSync(list);
    cut = `\nProposal cut (silent, UI only): \`proposal_cut_silent.mp4\`, ${duration(out).toFixed(1)}s, clips ${PROPOSAL.join(", ")}. ` +
      "The brief asks for 60 to 90 seconds; the remaining time comes from the talking head.\n";
  }
  const md = [
    "# Clip manifest",
    "",
    "All clips are 1920 x 1080, 30 fps, H.264, silent, recorded from the app with the fictional sample data by `record.mjs`.",
    "Cards and close ups are rendered at full resolution, not upscaled. The terminal clips are styled replays of prompts used in the build, with no keys, emails or personal paths.",
    "",
    "| Clip | File | Duration | What it shows | Script section |",
    "|---|---|---|---|---|",
    ...rows,
    cut,
  ].join("\n");
  fs.writeFileSync(path.join(HERE, "MANIFEST.md"), md + "\n");
  console.log(`wrote MANIFEST.md (${rows.length} clips)`);
}

// ---------------------------------------------------------------- main
const args = process.argv.slice(2);
if (!args.includes("--finalize")) {
  const wanted = args.length ? CLIPS.filter((c) => args.includes(c.id)) : CLIPS;
  const browser = await chromium.launch();
  try {
    for (const clip of wanted) await record(browser, clip);
  } finally {
    await browser.close();
  }
}
finalize();
