# Demo clips

`record.mjs` records every clip in the shot list as a 1920 x 1080, 30 fps, H.264 MP4 with no audio, then writes `MANIFEST.md` and a silent proposal cut (C01, C04, C07, C08, C16).

```bash
# 1. Run the app with the recorded sample outputs (see docs/SETUP.md), DEMO_MODE=1
# 2. Record
cd clips && npm install && node record.mjs          # all clips
node record.mjs C07 C08                             # just some
node record.mjs --finalize                          # rebuild MANIFEST.md and the proposal cut
```

- App clips (C03 to C12) are driven by Playwright at a human pace, with a visible cursor and a highlight ring on every click (`cursor.js`).
- Close ups (C05, C09) are rendered zoomed in the browser, so text stays sharp.
- Cards (C01, C02, C15, C16) are animated HTML in `cards/`, recorded as video plus a PNG still each. C16 reads its cost per enquiry from the recorded Claude calls and is labelled as an estimate.
- Prompt moments (C13, C14) are terminal style replays in `terminal/`. They contain no keys, emails or personal paths.
- Frames come from Chrome's screencast at JPEG quality 95 and are encoded with ffmpeg (libx264, CRF 17). The MP4s are small (under 1 MB each), so they are stored as normal Git files.
