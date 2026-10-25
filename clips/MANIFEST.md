# Clip manifest

All clips are 1920 x 1080, 30 fps, H.264, silent, recorded from the app with the fictional sample data by `record.mjs`.
**The app clips (C03 to C12) were recorded with `LLM_MODE=scripted`: the AI outputs are hand written stand ins from `data/demo_outputs.json`, not real Claude outputs.** The app, scoring, review gate, dedupe and citation checks are the real code. The C16 cost is estimated from prompt sizes. Re-record after the real run with an API key.
Cards and close ups are rendered at full resolution, not upscaled. The terminal clips are styled replays of prompts used in the build, with no keys, emails or personal paths.

| Clip | File | Duration | What it shows | Script section |
|---|---|---|---|---|
| C01 | C01_before_card.mp4 (still: C01_before_card.png) | 8.0s | Before card: a crowded inbox and enquiries copied into a CRM by hand | Problem |
| C02 | C02_flow_card.mp4 (still: C02_flow_card.png) | 10.0s | Flow card: form and inbox, AI sorts, scores, draft reply, you approve, CRM and reply | How it works |
| C03 | C03_contact_form.mp4 | 10.7s | A new enquiry submitted through the website contact form | How it works |
| C04 | C04_inbox_tags.mp4 | 11.1s | Inbox filling with colour tags as the AI sorts each enquiry: Sales, Support, Spam, Other | How it works |
| C05 | C05_lead_card_closeup.mp4 | 6.6s | Close up of a lead card: score, extracted fields with confidence, one line reason | How it works |
| C06 | C06_leads_by_score.mp4 | 8.8s | Lead list sorted by score, strongest at the top | Demo |
| C07 | C07_crm_duplicate_merged.mp4 | 10.3s | Qualified lead approved into the CRM, duplicate from the same company merged into one record | Demo |
| C08 | C08_sales_draft_edit_approve.mp4 | 12.7s | Sales reply draft opened in the review queue, edited, then approved | Demo |
| C09 | C09_support_citation_closeup.mp4 | 10.4s | Support email answered from the help docs, close up on the citation | Demo |
| C10 | C10_amber_low_confidence.mp4 | 7.6s | Amber flag on a low confidence item, held for a person | What could go wrong |
| C11 | C11_injection_flagged.mp4 | 6.8s | Email with hidden instructions, treated as data and flagged | What could go wrong |
| C12 | C12_weekly_summary.mp4 | 6.0s | Weekly summary panel (time saved is a labelled placeholder) | Business value |
| C13 | C13_prompt_plan.mp4 | 10.2s | Prompt moment: the planning prompt typed in a terminal replay, the plan appears | How I built it |
| C14 | C14_prompt_review_queue.mp4 | 8.8s | Prompt moment: the review queue prompt and the result | How I built it |
| C15 | C15_safeguards_card.mp4 (still: C15_safeguards_card.png) | 8.0s | Safeguards card: approval before send, confidence flags, injection guard | What could go wrong |
| C16 | C16_value_cost_card.mp4 (still: C16_value_cost_card.png) | 8.0s | Business value and cost card, labelled as an estimate | Business value |

Proposal cut (silent, UI only): `proposal_cut_silent.mp4`, 50.1s, clips C01, C04, C07, C08, C16. The brief asks for 60 to 90 seconds; the remaining time comes from the talking head.

