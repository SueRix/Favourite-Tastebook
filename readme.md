# Favourite Tastebook

A Django application for finding, composing and keeping recipes. It combines a
curated recipe catalogue with three independent search engines (SQL keyword,
semantic vector search over Pinecone, and an ingredient-centric variant of it),
a personal taste profile that re-ranks every result, an AI image analyzer that
turns a photo of your fridge into an ingredient selection, and a cooking agent
that composes a dish when the catalogue has nothing to offer.

🟢 **Live deployment:** [https://50-116-58-232.sslip.io/home/](https://50-116-58-232.sslip.io/home/)

---

## Features

### Recipe Builder (`/home/`)
Pick the ingredients you actually have; recipes are scored by how well they
match. Required / secondary / optional ingredients carry different weights, and
missing required ones are penalised (`recipe_manager/domain/enums.py` holds the
weights, `infrastructure/orm/scoring.py` applies them as ORM annotations).

### Taste profile (`/home/tastes/`)
Rate ingredients and cuisines on a five-point scale (Love … Hate). The scores
become a sparse user vector, and results are re-ranked by cosine similarity
between that vector and each recipe's ingredient/cuisine features
(`domain/services/taste_vector_engine.py`). `Hate` is a hard exclusion — a taboo
enforced everywhere, including on recipes the AI composes. The whole ranking can
be switched off per session from the UI.

### AI image analyzer
Upload a photo; Gemini extracts the visible ingredients, they are matched
against the catalogue and selected in the builder. The call runs as a Celery
task and the page polls for the result, so a slow model never blocks a request
(`tasks.py`, `application/use_cases/ai_task_orchestrator.py`,
`infrastructure/ai_adapters/gemini_adapter.py`).

### Recipes Database (`/home/database/`)
One search box, three modes behind a strategy interface
(`domain/recipe_selection_strategy.py`):

| Mode | Strategy | What it does |
| --- | --- | --- |
| **Keyword** | `KeywordSelectionStrategy` | SQL `ILIKE` over titles and descriptions. |
| **Semantic** | `VectorSelectionStrategy` | The query is POSTed to a self-hosted n8n webhook, which embeds it and runs a Pinecone similarity search; Postgres only hydrates the returned ids, preserving Pinecone's ranking. |
| **Ingredient** | `VectorSelectionStrategy` | Same engine, query re-phrased as "recipes made with X" to steer the embedding towards ingredient-centric matches. |

Similarity scores are calibrated (`VECTOR_SCORE_FLOOR` / `CEILING` / `CURVE`)
before being drawn as the match thermometer, so the difference between a strong
and a weak match stays visible and comparable across searches.

### Recipe Studio (`/home/studio/`)
A chat with a self-hosted n8n cooking agent on the left, an editable recipe
draft on the right. The agent can search the catalogue, read your taste profile,
save a catalogue recipe, and compose a new dish out of the known ingredient
catalogue. Proposed dishes land in a draft you can edit and keep; kept ones are
stored as `GeneratedRecipe` — a separate table, so composed dishes never mix
into the curated catalogue, the home feed or the search index.

A settings panel controls the assistant, and the switches are **enforced
server-side**, not merely described in the prompt:

- `recipe_source = ai` — the two catalogue search tools refuse outright.
- `use_tastes = false` — the tastes tool answers empty (the `never_use` taboo
  list still travels, because it carries allergies).
- `autosave_drafts = false` — a proposal stays a card in the chat instead of
  dropping into the editor.

### Saved recipes, accounts, profile
Bookmark catalogue recipes (`/home/saved/`), register / log in / change password
/ delete account (`/accounts/`), upload an avatar (`/profile/`).

---

## Architecture

The `recipe_manager` app is layered, and the dependency direction points inwards:

```
recipe_manager/
├── domain/            # Framework-free core
│   ├── enums.py                         scoring weights, units, taste levels
│   ├── recipe_selection_strategy.py     abstract search contract
│   ├── services/taste_vector_engine.py  cosine similarity ranking
│   ├── parsers/                         untrusted agent input -> validated data
│   └── exceptions/                      typed domain errors
├── application/use_cases/   # Orchestration: search, dashboard, agent chat,
│                            # agent settings, generated recipes, AI tasks
├── infrastructure/          # Everything that talks to the outside world
│   ├── orm/                 keyword strategy, scoring annotations
│   ├── vector_search/       n8n/Pinecone client + vector strategy
│   ├── agent/               chat client, signed context token, rate limiter,
│   │                        draft store, chat session
│   ├── ai_adapters/         Gemini
│   ├── selectors/           read-side queries
│   ├── presentation/        presenters shaping data for templates and JSON
│   └── task_queue/          Celery adapter
├── views/                   thin HTTP layer (pages, HTMX partials, JSON)
├── urls.py / agent_urls.py  browser surface / agent tool surface
└── tests/                   ~230 tests
```

**Front end:** server-rendered Django templates plus HTMX partials, with plain
JS per page. No SPA build step.

---

## Tech stack

Django 5.1 · PostgreSQL 15 · Redis (Celery broker + cache) · Celery ·
n8n (agent workflow + Pinecone gateway) · Pinecone · Google Gemini · HTMX ·
Gunicorn · WhiteNoise · Caddy · Docker Compose · Python 3.12

---

## Running it

Everything below runs from the `favourite_tastebook/` directory — the one that
holds `manage.py` and the compose files.

### With Docker (recommended)

```bash
git clone https://github.com/SueRix/Favourite-Tastebook.git
cd Favourite-Tastebook/favourite_tastebook

cp .env.prod.example .env      # then fill it in - see the table below
docker compose up --build
```

This starts Postgres, Redis, n8n and the Django dev server. Migrations run on
start, and migration `0002_load_initial_data` seeds the cuisines, ingredients
and four recipe collections from `recipe_manager/fixtures/`.

- App: http://localhost:8000/home/
- n8n editor: http://localhost:5678/

```bash
docker compose exec web python manage.py createsuperuser
```

### Without Docker

You still need a reachable PostgreSQL and Redis.

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Celery (needed for the image analyzer) runs separately:

```bash
celery -A favourite_tastebook worker -l INFO
```

Vector search and the cooking agent need a self-hosted n8n with the two
workflows imported. Without the webhook URLs configured those features report
that they are switched off instead of failing somewhere in the transport.

### Tests

```bash
python manage.py test                       # everything
python manage.py test recipe_manager        # one app
python manage.py test recipe_manager.tests.test_recipe_studio   # one module
```

---

## Configuration

`.env` lives next to `manage.py`; `.env.prod.example` is the template. Avoid `$`
inside secrets — docker compose reads it as the start of a variable reference.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | — | Django secret key (required). |
| `DEBUG` | `False` | Cast to bool, so `False` really is off. |
| `ALLOWED_HOSTS` | `localhost` | Comma-separated. Must include `web`, since n8n reaches the tool API at `http://web:8000` over the compose network. |
| `CSRF_TRUSTED_ORIGINS` | *(empty)* | Comma-separated, e.g. `https://1-2-3-4.sslip.io`. |
| `DB_ENGINE` | `django.db.backends.postgresql` | |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | — | Required. |
| `DB_HOST` / `DB_PORT` | — / `5432` | `db` inside compose. |
| `GEMINI_API_KEY` | — | Image analyzer. |
| `REDIS_CACHE_URL` | `redis://redis:6379/1` | Rate-limit counters and draft store (DB 0 is the Celery broker). |
| `N8N_PINECONE_WEBHOOK_URL` | *(empty)* | Vector search webhook; empty disables semantic search. |
| `N8N_AGENT_WEBHOOK_URL` | *(empty)* | Cooking agent webhook; empty disables the chat. |
| `N8N_WEBHOOK_AUTH_TOKEN` | *(empty)* | Bearer token sent to n8n. |
| `N8N_WEBHOOK_TIMEOUT` | `5` | Seconds, vector search. |
| `VECTOR_SEARCH_TOP_K` | `20` | Candidates requested from Pinecone. |
| `VECTOR_SCORE_FLOOR` / `CEILING` / `CURVE` | `0.45` / `0.71` / `1.4` | Calibration of the match percentage. |
| `AGENT_SERVICE_TOKEN` | *(empty)* | Shared secret for the tool API. Empty means the tool API refuses every call (fail closed). |
| `AGENT_CONTEXT_MAX_AGE` | `3600` | Lifetime (s) of the signed user context handed to n8n. |
| `AGENT_TOOL_MAX_RESULTS` / `AGENT_TOOL_RESULT_CEILING` | `5` / `10` | Rows per tool call, and the ceiling the agent cannot argue past. |
| `AGENT_CHAT_TIMEOUT` | `60` | Seconds for one agent turn. |
| `AGENT_CHAT_MAX_MESSAGE` | `500` | Characters; longer messages are truncated, not rejected. |
| `AGENT_CHAT_RATE_PER_MINUTE` / `_PER_DAY` | `6` / `100` | Per user. |
| `AGENT_DRAFT_TTL` | `3600` | How long an unsaved proposal waits. |
| `SITE_ADDRESS` | — | Production only: the hostname Caddy gets a certificate for. |
| `N8N_ENCRYPTION_KEY` | — | Production only: pins n8n's credential encryption key. |

---

## URL reference

`APPEND_SLASH` is **off** — the trailing slash is part of every URL.

### Pages

| URL | Method | Description |
| --- | --- | --- |
| `/home/` | GET | Recipe Builder (ingredient picker + ranked recipes). |
| `/home/database/` | GET | Recipes Database search page. |
| `/home/studio/` | GET | Recipe Studio (agent chat + draft editor). Login required. |
| `/home/tastes/` | GET | Taste preferences. Login required. |
| `/home/saved/` | GET | Saved recipes. Login required. |
| `/profile/` | GET, POST | Edit profile / avatar. |
| `/accounts/login/`, `/accounts/register/` | GET, POST | Authentication. |
| `/accounts/logout/`, `/accounts/delete/` | POST | Log out / delete account. |
| `/accounts/password-change/` | GET, POST | Change password. |
| `/admin/` | — | Django admin. |

### HTMX partials

`/home/partials/ingredients/` · `/home/partials/recipes/` ·
`/home/partials/database/search/` · `/home/partials/database/card/<recipe_id>/` ·
`/home/partials/tastes/rated/` · `/home/partials/tastes/search/`

### Image analyzer

| URL | Method | Description |
| --- | --- | --- |
| `/home/ai/upload-form/` | GET | Upload form partial. |
| `/home/ai/process/` | POST | Queues the Celery analysis task. |
| `/home/ai/status/<task_id>/` | GET | Polled until the task finishes. |

### Taste & saved API (JSON, login required)

| URL | Method | Description |
| --- | --- | --- |
| `/home/api/tastes/recipe/<recipe_id>/like/` | POST, DELETE | Like / undo. |
| `/home/api/tastes/recipe/<recipe_id>/dislike/` | POST, DELETE | Dislike / undo. |
| `/home/api/tastes/ingredient/update/` | POST | Set an ingredient score. |
| `/home/api/taste/cuisine/update/` | POST | Set a cuisine score. |
| `/home/api/tastes/toggle-global/` | POST | Switch taste ranking on/off for the session. |
| `/home/saved/<recipe_id>/` | POST, DELETE | Save / unsave a recipe. |

### Studio & chat (JSON, login required)

| URL | Method | Description |
| --- | --- | --- |
| `/home/chat/` | POST | Send one message, get the agent's reply (and a draft, if it proposed one). |
| `/home/chat/reset/` | POST | Start a new conversation. |
| `/home/chat/settings/` | GET, POST | Read / update the assistant switches. |
| `/home/studio/preview/` | POST | Render a draft as a recipe card. |
| `/home/studio/save/` | POST | Store the edited draft as a generated recipe. |
| `/home/studio/creations/` | GET | List the user's generated recipes. |
| `/home/studio/creations/<recipe_id>/` | DELETE | Delete one. |

### Agent tool API (`/api/agent/`)

Server-to-server only — deliberately mounted off the browser-facing prefixes so
the whole surface can be firewalled as a single path. Every endpoint is
POST-only, JSON in / JSON out, and requires two headers:

- `X-Agent-Token` — the shared `AGENT_SERVICE_TOKEN`.
- `X-Agent-Context` — a signed `{uid, sid}` minted by the chat view. Never a
  body field: the model must not be able to choose whose profile it reads.

| Endpoint | Request | Response |
| --- | --- | --- |
| `tools/tastes/` | `{}` | loved / liked / disliked / never_use |
| `tools/search-recipes/` | `{query, mode?, limit?}` | matching recipes |
| `tools/by-ingredients/` | `{ingredients[], limit?}` | the same, plus `missing_required` |
| `tools/recipe-detail/` | `{recipe_id}` | steps + grouped ingredients |
| `tools/save-recipe/` | `{recipe_id}` | `{saved, already_saved}` |
| `tools/ingredient-catalog/` | `{}` | `{ingredients, units, importance}` |
| `tools/propose-recipe/` | the composed recipe | the checked draft, unsaved |
| `tools/save-generated-recipe/` | `{title, cook_time_minutes, steps[], ingredients[]}` | the stored recipe |

---

## Deployment

The production stack is its own compose file — it runs standalone, not layered
on top of the development one:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

What it changes versus development:

- **Gunicorn** (3 workers × 2 threads) instead of `runserver`; `migrate` and
  `collectstatic` run on start.
- **No source bind-mount** — the image is the deployment unit. Media and static
  files live in named volumes.
- **Caddy** terminates TLS on :80/:443. With an `sslip.io` hostname
  (`1-2-3-4.sslip.io`) it obtains a real Let's Encrypt certificate without a
  domain of your own. It serves `/media/` straight off disk; everything else,
  `/static/` included (WhiteNoise), is proxied to `web:8000` with
  `X-Forwarded-Proto` set, which is what `SECURE_PROXY_SSL_HEADER` relies on.
- **Postgres, Redis and n8n are not published.** The n8n editor is bound to
  loopback; reach it through an SSH tunnel —
  `ssh -L 5678:localhost:5678 root@<server-ip>`, then http://localhost:5678
- **Redis** runs cache-only (`--save ""`, `allkeys-lru`), and Celery recycles a
  worker every 100 tasks, because Pillow and the Gemini client hold on to memory.

n8n workflow exports are not committed — they carry the agent's system prompt
and the exporting account's details, and are imported into the volume on setup.

---

## Contributing

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.
