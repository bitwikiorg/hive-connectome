# Browser Lab

A browser can be a useful **data environment**, but it should be an optional experimental module.

## Recommended signal hierarchy

```text
1. DOM / accessibility tree / network response
2. structured page metadata
3. screenshot
4. OCR
5. local LLM vision/text interpretation
```

Do not OCR text that the browser already exposes structurally.

## Two deployment modes

### Disposable browser container

Use Playwright Chromium in a separate optional service/profile.

Advantages:

- reproducible;
- isolated cookies;
- easy screenshot capture;
- safe to reset;
- suitable for eval fixtures.

### Host Brave

Brave is Chromium-based. A later connector can attach via Chrome DevTools Protocol when the user explicitly launches a dedicated Brave profile with remote debugging.

Do **not** connect HIVE to the user's everyday authenticated browser profile by default.

Use a dedicated profile/container for automated experiments.

## Worker path

```text
page
→ DOM extractor
→ Larvaᵢ
→ Beeᵢ
→ JEV: bounded relevance / routing decisions
→ optional OCR if required
→ optional LLM if semantics remain open-ended
→ evidence receipt
```

## First browser tests

Use local static fixtures before the open web:

- normal article
- table
- dashboard with changing number
- canvas chart
- image containing text
- deliberately misleading hidden DOM
- inaccessible/timeout page

Only after those pass should HIVE browse changing public pages.
