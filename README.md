<div align="center">

# Mimic

**An API client, a mock server, and a test runner — in one app you run yourself.**

Build requests, send them, assert on the responses, and loop whole collections
to catch the failures that only happen sometimes. Fake the endpoints that do
not exist yet. No account, no cloud, no telemetry.

</div>

---

## What it does

| | |
|---|---|
| **Send requests** | Any method, any URL. Headers, query params, JSON/XML/text/form bodies, and Bearer / Basic / API-key auth. Requests go out from the server, so there is no CORS to fight and timings are real. |
| **Assert on responses** | Check the status, a JSON field, a header, the body, or how long it took. Assertions are built from dropdowns — they are data, never code, so a shared collection can never execute anything. |
| **Run collections in a loop** | Run every request in a collection, N times over. This is how you catch flaky endpoints, intermittent timeouts, and rate limits that a single request hides. |
| **Mock endpoints** | Define a path and the JSON it should return. Supports `:id` path parameters, `*` wildcards, custom status codes, headers, and artificial delay for testing spinners and timeouts. |
| **Environments** | Keep `{{baseUrl}}`, `{{token}}` and friends in named sets. Switch environments to point the same requests at local, staging, or production. |
| **History** | Every request you send is recorded with its response and timing. Credentials are masked before anything is written to disk. |

---

## Quick start

You need [Docker](https://docs.docker.com/get-docker/). Nothing else.

```bash
git clone https://github.com/hoysengleang/Mimic-Mock-Api-Best.git
```

```bash
cd Mimic-Mock-Api-Best && cp .env.example .env
```

```bash
docker compose up --build
```

Then open **<http://localhost:3000>**.

The first run seeds a working example — a few mock endpoints and a collection
that calls them — so you can press **Send** immediately and see it work. To
start empty instead, set `SEED_DEMO_DATA=false` in `.env`.

| | |
|---|---|
| App | <http://localhost:3000> |
| API docs (interactive) | <http://localhost:5000/docs> |
| Your mock endpoints | `http://localhost:5000/mock/...` |

### Production-style run

Serves built assets through nginx, with no autoreload and only one port open:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

---

## A first walkthrough

1. Open the app. The sidebar has a **Getting started** collection.
2. Click **List users**, then **Send**. You get `200 OK`, the timing, the size,
   and `3/3 tests` passing.
3. Open the **Tests** tab to see the assertions that just ran. Change one to
   expect something wrong and send again — it turns red and tells you what it
   got instead.
4. Go to **Runner**, set **Iterations** to `5`, and press **Run collection**.
   It sends every request five times and reports each iteration separately.
5. Go to **Mocks** to see the fake endpoints being called, and edit what they
   return.

Keyboard: `Ctrl/Cmd + Enter` sends, `Ctrl/Cmd + S` saves.

---

## Running without Docker

<details>
<summary>Backend</summary>

```bash
cd src/Mimic.API && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/uvicorn app.main:app --reload --port 5000
```
</details>

<details>
<summary>Frontend</summary>

```bash
cd src/Mimic.UI && yarn install && yarn dev
```

The dev server proxies `/api` and `/mock` to `http://localhost:5000`. Override
with `VITE_PROXY_TARGET` if your backend is elsewhere.
</details>

---

## Project layout

```
src/
├── Mimic.API/                  FastAPI backend
│   ├── app/
│   │   ├── core/               settings, SSRF policy, middleware
│   │   ├── db/                 SQLAlchemy models, engine, demo seed
│   │   ├── schemas/            Pydantic request/response models
│   │   ├── services/           executor, assertions, runner, matcher
│   │   ├── api/routes/         the HTTP endpoints
│   │   └── main.py             app wiring
│   └── tests/                  pytest suite
│
└── Mimic.UI/                   Vue 3 + TypeScript frontend
    ├── src/
    │   ├── components/         UI building blocks
    │   ├── views/              one per screen
    │   ├── stores/             Pinia state
    │   ├── services/api.ts     typed API client
    │   └── styles/main.css     design tokens
    └── e2e/                    Playwright tests
```

### Endpoints

The API is documented interactively at `/docs`. In short:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/send` | Execute one request |
| `POST` | `/api/run` | Run a collection, optionally looped |
| `GET` | `/api/collections` | Every collection **with its folders and requests**, in one call |
| `POST` | `/api/collections` | Create a collection |
| `GET/POST` | `/api/mocks` | Mock definitions |
| `GET/POST` | `/api/environments` | Variable sets |
| `GET` | `/api/history` | Past executions |
| `ANY` | `/mock/{path}` | Your configured mocks |

---

## Design

The interface follows a written system rather than per-screen taste — see
[docs/design/DESIGN-SYSTEM.md](docs/design/DESIGN-SYSTEM.md). Three rules
drive everything:

1. **Monospace carries the interface.** Anything that is data — headings,
   labels, paths, status codes, counts — is set in JetBrains Mono. Inter is
   for prose only.
2. **Colour means something, or it is not there.** Colour appears on HTTP
   methods, pass/fail state, and the single accent. Nothing is tinted for
   decoration.
3. **State is a tinted chip, not a border.** Borders are for structure.

Three themes ship, switchable from the header:

| Theme | Character |
|---|---|
| **Paper** | Light and airy. The default. |
| **Slate** | The same design, dark. |
| **Terminal** | Near-black with a green cast, amber accent, denser controls. |

---

## Performance

The hot paths are benchmarked rather than assumed. Run it yourself:

```bash
cd src/Mimic.API && .venv/bin/python -m tests.benchmark
```

With 200 mocks and 10 collections of 20 requests:

| Operation | Before | After |
|---|---|---|
| Serve one mock | 5.16 ms | **1.54 ms** (648 ops/s) |
| Load the sidebar | 35.7 ms | **9.9 ms** |

Two changes did most of that:

- **Mock definitions are cached in memory**, pre-split into path segments,
  and hit counters are buffered and written in one bulk statement. Serving a
  mock previously cost two database round trips *per request* — one to load
  every mock, one to commit the counter.
- **Collections load in a single call** with eager-loaded relations. The UI
  used to fetch an index and then each collection separately.

Note: a union `response_model` and GZip middleware were both tried here and
removed — they made things slower. Details are in the code comments.

---

## Security

Mimic sends HTTP requests from the server on your behalf. That is a useful
feature and a dangerous one, so it is fenced in:

- **Only `http` and `https`.** `file://`, `gopher://` and the rest are refused.
- **Cloud metadata is always blocked** — `169.254.169.254` and the IPv6
  equivalent, in every configuration. That endpoint hands out cloud
  credentials and there is no legitimate reason to reach it from here.
- **Every redirect hop is re-checked.** A `302` pointing at a blocked address
  is caught, not followed. This is the step most tools miss.
- **Private networks are configurable.** Allowed by default because your dev
  API is on localhost; set `ALLOW_PRIVATE_NETWORK=false` when hosting Mimic
  where other people can reach it.
- **Assertions are data, not code.** There is no `eval` anywhere, so importing
  someone else's collection cannot execute anything.
- **Credentials are masked in history** before they are written to disk.
- **Rate limits, body-size caps, response-size caps, and timeouts** bound what
  any single request or run can cost.

Mimic has no login. It is built to run on your own machine or your own
network. If you expose it publicly, put it behind your own authentication and
set `ALLOW_PRIVATE_NETWORK=false`.

---

## Tests

```bash
cd src/Mimic.API && .venv/bin/python -m pytest
```

```bash
cd src/Mimic.UI && yarn test:e2e
```

The backend suite covers the SSRF policy, the assertion engine, mock matching,
every endpoint, and the runner. The Playwright suite drives the real UI against
the real API — nothing is stubbed, because the bugs worth catching live in the
seam between them.

---

## Configuration

Everything is set through environment variables or `.env`; see
[`.env.example`](.env.example) for the full annotated list. The defaults are
chosen to work with no configuration at all.

---

## Contributing

See [docs/developer/CONTRIBUTING.md](docs/developer/CONTRIBUTING.md).
