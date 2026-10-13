# TactiFrame

TactiFrame is a dark sports-tech product concept for opposition analysis.

> See the match. Reason over evidence. Approve the plan.

## Included

- `/` — TactiFrame product landing page
- `/workspace` — desktop-first opposition-analysis workspace
- Clickable event timeline with evidence state changes
- Mock Agent Vision chat and coach approval flow
- Generated product visuals in `client/public/assets/`
- Research-demo data only; no real CV processing yet

## Codex / engineering handoff

This repository is intentionally independent from Tactivision.ai and ready for the next implementation layer:

1. OpenCV / computer-vision event extraction
2. AWS storage and processing jobs
3. Agentic reasoning over event and clip evidence
4. Coach review, edits, and approval persistence

## Run locally

```bash
pnpm install
pnpm dev
```

Open `http://localhost:3000/` and `http://localhost:3000/workspace`.

## Build checks

```bash
pnpm run check
pnpm run build
```

## Brand tokens

- Background: `#0B0F14`
- Panels: `#121821`
- Borders: `#1E2633`
- Text: `#F3F5F7`
- Muted: `#9AA3B2`
- Signal green: `#3DFF8A`
