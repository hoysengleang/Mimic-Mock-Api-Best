# Contributing to Mimic

Thanks for helping. This document is short on purpose — the parts that are
easy to get wrong are written down, and nothing else.

---

## Getting set up

```bash
cp .env.example .env && docker compose up --build
```

Or without Docker, in two terminals:

```bash
cd src/Mimic.API && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/uvicorn app.main:app --reload --port 5000
```

```bash
cd src/Mimic.UI && yarn install && yarn dev
```

---

## Before you open a pull request

All three must pass.

```bash
cd src/Mimic.API && .venv/bin/python -m pytest
```

```bash
cd src/Mimic.UI && yarn typecheck && yarn vite build
```

```bash
cd src/Mimic.UI && yarn test:e2e
```

The end-to-end suite needs the API running on port 5000. It drives the real
UI against the real backend — nothing is stubbed, because the bugs worth
catching live in the seam between them.

---

## Backend conventions

**Structure.** Routers in `app/api/routes`, Pydantic schemas in
`app/schemas`, SQLAlchemy models in `app/db/models.py`, and anything with
logic in `app/services`. A route function should read as: validate, call a
service, return. If a route is making decisions, that logic belongs in a
service where it can be unit-tested.

**Style.** `snake_case`, type hints on anything public, `from __future__
import annotations` at the top.

**Things that will get a PR sent back:**

- **Adding `eval`, `exec`, or any user-supplied code execution.** Assertions
  are deliberately declarative data. A collection someone downloads must
  never be able to run anything. If a feature seems to need scripting,
  open an issue first — the answer is usually a new declarative operator.
- **Sending an outbound request that bypasses
  `app/core/security.py`.** Every URL, including every redirect hop, goes
  through `validate_outbound_url`. This is what stops Mimic being an SSRF
  proxy.
- **Writing credentials to the database unredacted.** Anything persisted
  passes through `redact_headers` first.
- **Unbounded work.** New loops, fetches and queries need a limit. The
  existing ones are in `app/core/config.py`.

**Performance.** The mock responder is a hot path. If you touch
`app/api/routes/serve.py`, `app/services/matcher.py`, or
`app/services/mock_registry.py`, run the benchmark before and after:

```bash
cd src/Mimic.API && .venv/bin/python -m tests.benchmark
```

Claims about performance should come with numbers. Two optimisations in this
codebase were reverted because measuring showed they made things slower.

---

## Frontend conventions

**Structure.** Views in `src/views` (one per screen), reusable pieces in
`src/components`, state in `src/stores` (Pinia), and all HTTP through
`src/services/api.ts`. Components should not call `fetch` directly.

**Style.** `<script setup lang="ts">`, TypeScript everywhere, no `any`.

**Design.** Read [the design system](../design/DESIGN-SYSTEM.md) before
adding UI. The short version:

- Monospace for data, Inter for prose.
- Colour only for HTTP methods, state, and the one accent.
- Semantic tokens only — no raw hex, no magic pixel values.
- No emoji as icons; add SVGs to `components/common/icons.ts`.
- Check all three themes. Terminal catches hard-coded assumptions.

---

## Commits and pull requests

Use a conventional prefix — `feat:`, `fix:`, `docs:`, `refactor:`,
`test:`, `perf:`.

In the pull request, say what changed and why. If it touches security or
performance, say how you verified it. Link the issue (`Closes #12`).

Questions: [open an issue](https://github.com/hoysengleang/Mimic-Mock-Api-Best/issues).
