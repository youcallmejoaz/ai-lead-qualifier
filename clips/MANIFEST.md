# Clip manifest

All clips are 1920 x 1080, 30 fps, H.264, silent, recorded from the app with the fictional sample data by `record.mjs`.
Cards and close ups are rendered at full resolution, not upscaled. The terminal clips are styled replays of prompts used in the build, with no keys, emails or personal paths.

| Clip | File | Duration | What it shows | Script section |
|---|---|---|---|---|
| C01 | C01_before_card.mp4 (still: C01_before_card.png) | 8.0s | Before card: a crowded inbox and enquiries copied into a CRM by hand | Problem |
| C02 | C02_flow_card.mp4 (still: C02_flow_card.png) | 10.0s | Flow card: form and inbox, AI sorts, scores, draft reply, you approve, CRM and reply | How it works |
| C13 | C13_prompt_plan.mp4 | 10.2s | Prompt moment: the planning prompt typed in a terminal replay, the plan appears | How I built it |
| C14 | C14_prompt_review_queue.mp4 | 8.8s | Prompt moment: the review queue prompt and the result | How I built it |
| C15 | C15_safeguards_card.mp4 (still: C15_safeguards_card.png) | 8.0s | Safeguards card: approval before send, confidence flags, injection guard | What could go wrong |


## Still to record

C03 to C12 (the app in use) and C16 (cost card) need the real Claude outputs for the 80 sample enquiries, which requires `ANTHROPIC_API_KEY`. Run `scripts/run_pipeline.py`, start the app, then `node record.mjs C03 C04 C05 C06 C07 C08 C09 C10 C11 C12 C16`.
