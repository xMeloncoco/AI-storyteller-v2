# FILE_MAP.md — Where things live and what they do

> **AI assistants: skim this every time you start work. Update it whenever a file changes responsibility.**
> If you split a file or add a new module, add it here in the same shape. If a file is deleted, remove its entry.

This map covers the parts a beginner programmer is most likely to touch. Generated boilerplate (Electron scaffolding, package manifests) is summarized in one line.

---

## Top-level

| Path | Role |
|---|---|
| `BUILD_INSTRUCTIONS.md` | **Master doc**. Principles + ordered build checklist. Read every time. |
| `FILE_MAP.md` | This file. Where things live. |
| `REFACTOR_FIRST.md` | Cleanup steps to run before adding new features on top of the current code. |
| `README.md` | User-facing intro, quick start, project structure overview. |
| `AI_SETUP.md` | How to configure Ollama / OpenRouter / Nebius. End-user setup guide. |
| `TESTING.md` | How to run `start-test.sh` / `start-test.bat` for local testing. |
| `start-test.sh` / `start-test.bat` | One-command launchers (backend + frontend + optional test data). |
| `stop-test.sh` / `stop-test.bat` | Counterpart shutdown scripts. |
| `.gitignore` | Standard ignores. |

---

## `backend/` — FastAPI + SQLAlchemy + SQLite + (later) ChromaDB

### `backend/app/main.py`
FastAPI app entry. Lifespan startup/shutdown, CORS, global exception handler, root endpoints (`/`, `/health`, `/info`, `/stats`), dev `/reset-database`. Mounts the routers from `routers/`. **Don't put business logic here.**

### `backend/app/config.py`
Settings via `pydantic-settings`. AI provider, model names, token limits, DB URL, context window size, logging level. All env-overrideable. **Magic numbers belong here, not in code.** (M0.5 will enforce this.)

### `backend/app/database.py`
SQLAlchemy engine + `SessionLocal` + `Base` + `init_db()` + `get_db()` dependency. Nothing else.

### `backend/app/models.py`
Every ORM table. Key models (in current state):

- **Core**: `Story`, `Playthrough`, `Session`, `Conversation`.
- **World**: `Character`, `Location`, `Relationship`.
- **Scene**: `SceneState`, `SceneCharacter`.
- **Character depth**: `CharacterState` (current emotions), `CharacterGoal`, `CharacterMemory` (episodic), `CharacterBelief` (semantic), `CharacterAvoidance`, `CharacterKnowledge`.
- **Story progression**: `StoryArc`, `StoryEpisode`, `StoryFlag`, `MemoryFlag`.
- **Debug**: `Log`.

Pattern: `playthrough_id IS NULL` = template (immutable). `playthrough_id != NULL` = playthrough instance (mutable). Don't break this convention. **When adding tables, follow the same convention and add indexes for the columns we'll filter on.**

### `backend/app/schemas.py`
Pydantic request/response models. Stays separate from `models.py`. **Add a schema here whenever you add an endpoint or return a new shape.**

### `backend/app/crud.py`
Plain functions: `get_x`, `create_x`, `update_x`. Reads & writes for every model. **Routers and pipeline stages should call CRUD, not query the DB directly.** Logging is built into the create/update helpers.

### `backend/app/PIPELINE_STAGES.md`
Per-stage spec: purpose, tasks, AI model, tables touched, code location. **Reference these stage names in code comments.** (M0.3 will make them log tags.)

### `backend/app/ai/` — model interaction

- `ai/llm_manager.py` — `LLMManager`: provider routing (`openrouter` / `nebius` / `local` Ollama / `demo`), `generate_text(...)`, `analyze_character_decision(...)`, `detect_scene_changes(...)`. Demo mode returns mock JSON for offline UI testing. **All LLM calls go through here.** Don't call providers directly elsewhere.
- `ai/prompts.py` — `PromptTemplates`: every prompt is a static method here. **Editing a prompt only ever means editing this file.** Currently holds: `story_generation_prompt`, `character_decision_prompt`, `scene_change_detection_prompt`, `generate_more_prompt`, others.
- `ai/context_builder.py` — `ContextBuilder`: assembles the context string sent to GENERATION. Currently returns one big string (M0.2 / M2.3 will refactor to per-character typed dicts). Pulls story/scene/characters/history/relationships/arcs/flags.
- `ai/validator.py` — `ContentValidator`: regex checks for user-character control, dialogue repetition, contradictions, character-decision consistency. Currently only logs issues. (M3 will give it teeth.)

### `backend/app/routers/` — HTTP endpoints

- `routers/chat.py` — `POST /chat/send` (the main pipeline orchestrator today — see M0.1 to extract), `POST /chat/generate-more`, `GET /chat/history/{session_id}`, `GET /chat/playthrough-history/{playthrough_id}`.
- `routers/stories.py` — story + playthrough listing/creation.
- `routers/admin.py` — Tester panel backend: load test data, view full playthrough, view context window, view grouped logs, reset playthrough.
- `routers/logs.py` — log queries for the log viewer.

### `backend/app/relationships/updater.py`
`RelationshipUpdater.update_relationships_from_interaction(...)` — runs after generation, uses a small-model call to estimate trust/affection/familiarity deltas and writes them to `Relationship`. **Adjust deltas conservatively; runaway relationships break stories.**

### `backend/app/story/progression.py`
`StoryProgressionManager.check_progression(...)` — checks arc/episode/flag conditions after generation, sets flags, activates/completes arcs.

### `backend/app/utils/logger.py`
`AppLogger` (session-scoped) + module-level `log_notification` / `log_error` / `log_edit` etc. Writes to the `logs` table AND prints to console. **Use `AppLogger` when inside a stage; use module-level helpers when you don't have a session yet.** (M0.3 adds a stage-aware context manager.)

### `backend/test_data/`
JSON story templates loaded by the admin `load-test-data` endpoint. `TEMPLATE_story.json` is the canonical shape; `moonweaver_story.json`, `sterling_story.json`, `starling_contract_story.json` are example stories. **New story JSON goes here.**

### `backend/load_test_data.py`
CLI fallback to load test data without going through the API.

### `backend/.env.example`
Copy to `.env` for local config. Default is local Ollama.

### `backend/requirements.txt`
Python deps. Notable: `fastapi`, `sqlalchemy`, `chromadb` (installed but not wired up — M6), `httpx`, `python-dotenv`.

---

## `frontend/` — Electron + plain JS + HTML/CSS

### `frontend/src/main.js`
Electron entry. Window creation, menu, app lifecycle.

### `frontend/src/index.html`
Single-page shell.

### `frontend/src/renderer.js`
Main renderer logic — wires up the chat, stories, settings, tester, logs panels. **App-level state lives here.**

### `frontend/src/api.js`
Thin wrapper around `fetch` to the backend. **All HTTP calls from the renderer go through here.**

### `frontend/src/components/chat.js`
Chat panel: message list + input box + send. Calls `/chat/send`. (M1.2 will add speech / action / thought modes.)

### `frontend/src/components/tester.js`
🧪 Debugger panel. Browses DB entities for the current playthrough, shows the exact context sent to the AI, lets you reset.

### `frontend/src/components/logs.js`
Log viewer. Grouped per turn. Filterable by type/category. **This is the primary debugging surface — keep it informative.**

### `frontend/src/components/settings.js`
Provider/model config, test data loader, system info.

### `frontend/src/styles.css`
All styling. Single file.

### `frontend/package.json`, `frontend/package-lock.json`
Electron + dev deps.

---

## `docs/`

| Path | Role |
|---|---|
| `docs/AI_PROMPT_CONSTRUCTION.md` | How prompts are assembled — read before editing `prompts.py`. |
| `docs/RESPONSE_FLOW.md` | Walk-through of the current `/chat/send` flow, step by step. |
| `docs/STORY_DATA_STRUCTURE.md` | JSON schema for story templates in `backend/test_data/`. |

---

## How to update this file

- **New file?** Add a row under the right section, one line of role.
- **Renamed file?** Update the path; don't leave a redirect note unless someone might still link to the old name.
- **File deleted?** Remove the row.
- **Responsibility moved?** Update both files' rows so the boundaries are clear.

A future reader should be able to read this map and `BUILD_INSTRUCTIONS.md` and know where to start, without grep.
