# REFACTOR_FIRST.md — Cleanup the current code needs before new features

> **AI assistants: this file is temporary. It exists to bring the current codebase up to the shape `BUILD_INSTRUCTIONS.md` assumes. Do these first, then start the M1+ checklist.**
> **Delete this file once every box below is ticked AND the matching M0 boxes in `BUILD_INSTRUCTIONS.md` are ticked.**
>
> Programmer is a beginner. Each refactor below is intentionally small and isolated. Do not bundle them.

---

## Why this exists

I reviewed the current codebase and it's structurally healthy for a v1 (good models, sensible router split, real logging table, demo mode, three working test stories). But four things will hurt every later step if we don't fix them now:

1. **`chat.py:send_message` is ~250 lines and does ten jobs.** Any change to one stage risks breaking the others. The beginner programmer can't isolate bugs to a stage.
2. **`ContextBuilder.build_full_context()` returns one giant string.** Every character sees the same context. We literally cannot filter by witness until this is split. (This is the root cause of failure modes #2, #3, #7.)
3. **`ContentValidator` only logs.** The `chat.py` comment even says *"we don't want to block the story"*. That means right now the validator is decoration. Every M3 step assumes it can repair.
4. **Magic numbers are scattered** (`min_importance=7`, `limit=10`, etc.). Tuning is guesswork because the values aren't in one place.

None of these are big rewrites. They're surgical. Each one unlocks a section of `BUILD_INSTRUCTIONS.md`.

---

## Working agreement for these refactors

- **One refactor per commit.** Each box below is its own PR/commit.
- **Behavior must not change** while doing M0 refactors. Run the app before and after each one — same input should yield same output. If output changes, you broke something; revert and try again.
- **Logs may get richer**, but every old log call must still produce a comparable entry (so the Tester panel doesn't suddenly go dark).
- **No new dependencies** during the refactor pass.

---

## R1 — Extract a `Pipeline` class (unblocks M0.1)

**Goal:** `routers/chat.py:send_message` becomes a thin HTTP handler that calls `pipeline.run(...)`. The pipeline lives in its own module so each stage is a method we can edit in isolation.

- [ ] Create `backend/app/pipeline/__init__.py` and `backend/app/pipeline/chat_pipeline.py`.
- [ ] Define `ChatPipeline(db, session_id)` with one method per stage matching `PIPELINE_STAGES.md`:
  - `intake(user_message) -> IntakeResult`
  - `trigger_detection(intake) -> TriggerResult`
  - `context_gather() -> ContextBundle`
  - `scene_simulation(context) -> List[CharacterDecision]`
  - `generate(context, decisions) -> str`
  - `validate(text, decisions) -> ValidationResult`
  - `present(text) -> Conversation` (writes the narrator row)
  - `state_update(text, decisions, validation) -> StateUpdateSummary`
- [ ] Move the current logic out of `send_message` into the matching methods. **Do not change behavior.**
- [ ] `send_message` becomes: parse `ChatRequest`, instantiate `ChatPipeline`, `await pipeline.run(message)`, shape `ChatResponse`. Should be < 40 lines.
- [ ] Same for `generate_more` — give it its own pipeline method or its own thin class.

**How to verify:** load a story, run a turn before and after. Output text should be similar (allow LLM variance). Logs should still appear per stage.

---

## R2 — Type the context bundle (unblocks M0.2 and M2.x)

**Goal:** stop passing a single giant string into prompts. The pipeline carries a structured `ContextBundle` and the prompt templates compose it on demand.

- [ ] Add `backend/app/pipeline/context_bundle.py` with a `ContextBundle` dataclass (or Pydantic model): `story`, `scene`, `characters_present: List[CharacterView]`, `history: List[Conversation]`, `relationships: List[RelationshipView]`, `active_arcs`, `memory_flags`.
- [ ] `CharacterView` includes the character sheet block separately from current state and goals — these will be re-injected fresh each turn (P2.4 / M2.4).
- [ ] Refactor `ContextBuilder` so its public surface is:
  - `build_bundle() -> ContextBundle` (replaces the old `build_full_context`).
  - `build_for_character(character_id) -> ContextBundle` (returns now, no filtering yet — M2.3 will add filtering).
- [ ] `PromptTemplates.story_generation_prompt` accepts a `ContextBundle`, not a pre-baked string. It does the assembly. (This is the single place where "what the model sees" is decided.)
- [ ] Keep `build_full_context` as a deprecated alias that calls `build_bundle().to_string()` so nothing breaks in one go. Remove it once M2.3 lands.

**How to verify:** the assembled prompt sent to the LLM should be byte-for-byte (or near) what it was before. Log it before and after and diff.

---

## R3 — Stage-tagged logging (unblocks M0.3)

**Goal:** every log line knows which stage it came from, without the caller having to remember.

- [ ] In `utils/logger.py`, add a `pipeline_stage(stage_name)` context manager. Inside it, all `AppLogger` calls auto-tag `details["stage"] = stage_name` and prefix the printed line with `[STAGE:NAME]`.
- [ ] Each method in `ChatPipeline` wraps its body in `with pipeline_stage("INTAKE"):` (etc).
- [ ] Existing `logger.notification/ai_decision/context/error` calls stay; the wrapper just enriches them.
- [ ] Tester panel log viewer: add a stage filter dropdown (read the `stage` field from `details`).

**How to verify:** run a turn, open the log viewer, confirm every entry has a stage tag and the dropdown filters correctly.

---

## R4 — Make the validator actually do something (unblocks M0.4 and M3.x)

**Goal:** the validator can fail a turn. Right now it doesn't. Even before we add the AI critic, the regex checks for *"AI controlling the user character"* should already cause a regeneration — that's the #1 user complaint and we already detect it.

- [ ] Add `VALIDATION_MODE` to `config.py` with values `warn` (default, current behavior), `block` (return an error to the user — for tests), `repair` (regenerate up to N times).
- [ ] In `ChatPipeline.validate(...)`:
  - `warn` → log issues, return text unchanged.
  - `block` → raise a 422 with the issues listed.
  - `repair` → if `controls_user` issue is present, regenerate **once** with an addendum prompt: *"You previously wrote `<span>`. Do not write or imply what `<user_name>` says, thinks, or does. Rewrite without that."* Re-validate. If still bad, log `validation.unrepairable` and return the original.
- [ ] Default stays `warn` so behavior doesn't change yet. The plumbing is what M3 needs.
- [ ] Add a clear log entry on each path (`validation.passed`, `validation.warned`, `validation.repaired`, `validation.unrepairable`).

**How to verify:** flip `VALIDATION_MODE=repair`, force a bad output (e.g., temporarily relax the system prompt), confirm regeneration happens and is logged.

---

## R5 — Constants into `config.py` (unblocks M0.5)

**Goal:** every tuning knob in one file.

- [ ] Grep for hardcoded numbers in `context_builder.py`, `validator.py`, `routers/chat.py`, `relationships/updater.py`, `story/progression.py`. Common offenders: `[:10]`, `min_importance=7`, `> 50` (dialogue length), `limit=settings.max_context_messages`, retry counts.
- [ ] Add named constants in `config.py` (e.g. `MEMORY_FLAG_TOP_N = 10`, `MEMORY_FLAG_MIN_IMPORTANCE = 7`, `MAX_DIALOGUE_WORDS = 50`).
- [ ] Replace the literals with the named settings.
- [ ] Document each in a comment in `config.py` — when would you change it, what does raising/lowering it do?

**How to verify:** behavior identical; greppable by name; comment explains the trade-off.

---

## R6 — Witness columns on memory tables (unblocks M2.x and M9.x)

**Goal:** the schema is ready for per-character knowledge filtering before we wire the filtering logic.

- [ ] Add `witnesses` (JSON list of character ids) and `told_to` (JSON list of character ids) columns to `MemoryFlag`, `CharacterMemory`, and `CharacterKnowledge` (if not already there).
- [ ] Write a tiny migration: for existing rows, default `witnesses` to all characters present in the same `session_id` (best effort), or empty list. Log a `database.backfill` notice per row touched.
- [ ] **Do not** change retrieval yet. CRUD reads stay the same. We're staging the columns so M2.3 can flip them on.

**How to verify:** new rows include witnesses (you'll need to wire writes in the next step), schema migration runs cleanly on a fresh DB and an existing DB.

---

## R7 — Sanity sweep

Once R1–R6 are done:

- [ ] Run `start-test.sh`. Load the Starling Contract story. Run 5 turns. Confirm everything still works.
- [ ] Open the Tester panel. Confirm logs are stage-tagged, all stages appear, no `pass`/swallowed exceptions.
- [ ] Check `FILE_MAP.md` is updated for the new `pipeline/` directory and the moved logic.
- [ ] In `BUILD_INSTRUCTIONS.md`, tick M0.1–M0.5 (they map 1:1 to R1–R5; R6/R7 are pre-work for M2 and a sanity gate respectively — note that in the box's dated comment).
- [ ] Delete this file. Commit the deletion with `chore: refactor pre-work complete, removing REFACTOR_FIRST`.

---

## What NOT to do during the refactor pass

- Don't add new features. Tempting changes — better prompts, new tables, ChromaDB wiring — all wait. The refactor's value comes from being a *behavior-preserving* cleanup.
- Don't rename existing model fields. The DB has live test data. Renames trigger migrations and break the test JSONs.
- Don't reformat unrelated files. Every diff in this pass should be tied to a specific R-item above. Mass formatting hides the actual changes from review.
- Don't skip the verification step on each R-item. The whole point is to land cleanups without regressions.
