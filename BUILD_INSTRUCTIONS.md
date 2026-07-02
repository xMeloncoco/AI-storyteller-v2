# BUILD_INSTRUCTIONS.md — Read Me First, Every Time

> **AI assistants: READ THIS WHOLE FILE before you touch any code.**
> **Programmer is a beginner vibe coder.** Optimize for legibility, isolation, and loud logs over clever abstractions.
> When you finish a step in the checklist below, change `[ ]` to `[x]` and add a one‑line dated note under it.

---

## 0. What this project is and what it is solving

This is a local‑first interactive AI storytelling app (working name: **Dreamwalkers**). It is being built to fix the eight failure modes the user keeps hitting on character‑chat sites:

1. AI does things it shouldn't (speaks/acts for the user).
2. AI forgets or misremembers facts.
3. Characters start distinct but drift into "agree‑with‑user" mush.
4. Characters always agree / always back down.
5. Story doesn't progress; no tension; world only follows the user.
6. Physical inconsistencies ("moves closer" when they are across the room).
7. Characters remember things they were never told / never witnessed.
8. AI reads user actions or thoughts as if they were said aloud.

**The fix is architectural, not a better prompt.** The LLM is demoted from "the thing that remembers and decides" to "the thing that writes prose, given tightly controlled inputs." Everything that must be exact lives in the database. The model never has to remember; we re‑inject what it needs every turn, filtered to what the *currently‑speaking character* would actually know.

---

## 1. Hard principles — do not violate without asking

These are the rules every change must respect. If a change cannot follow them, **stop and ask the user before writing code**.

### P1. Externalize all hard state.
Positions, relationships, who‑knows‑what, inventory, emotional state, goals, time, location — **all of this lives in SQLite, not in the model's memory**. Every turn, the relevant slice is fetched fresh and injected into the prompt. The model is never expected to "remember" anything across turns.

### P2. Generation is wrapped in a check.
Every AI generation runs through a cheap validator pass. The validator asks narrow yes/no questions (did the user's character speak? did anyone do something physically impossible? did a character reference something they couldn't know?). On fail → repair or regenerate. **The validator is not optional.**

### P3. Knowledge is scoped per character.
When we assemble the prompt input for a character, we filter their in‑world context to **only what that character witnessed, was told, or could plausibly deduce**. Global memory dumps are how characters "know" things they shouldn't. Never feed a character context they wouldn't have.

### P4. Structured input, not free text.
User input is parsed into separate fields: **speech**, **action**, **thought**. Thoughts are *never* shown to NPCs. Actions are world events. Speech is what NPCs can hear. This is the single cheapest fix for "the AI treated my thought like dialogue."

### P5. The world has its own forces.
NPCs have goals that conflict with the user. A director layer can introduce complications independent of user input. The user goes along with the story; the story is not just whatever the user asks for.

### P6. Small modules, single responsibility, loud logs.
Every pipeline stage is a separate function/class. Every stage logs **its inputs, its outputs, and any decisions it made**, structured (JSON in the `details` column), with the stage name as a tag. When a bug happens, the programmer should be able to read the log and immediately see which stage misbehaved without opening the source.

### P7. No premature features, no half-finished features.
If a step in the checklist isn't done, don't reference it from other code as if it were. Don't add fallback paths "for later." Don't introduce abstractions you don't need yet. Three similar lines beats a premature framework.

### P8. Never write `try/except: pass`. Never swallow errors silently.
If something fails, log it loudly with full context (stage, inputs, exception, traceback) and surface it. A silent failure is the worst possible outcome for a beginner programmer trying to debug.

### P9. Comments explain WHY, not WHAT.
Identifiers should explain *what*. Comments only earn their keep when the *why* is non‑obvious (a hidden constraint, a workaround, a gotcha). Do not narrate the code.

### P10. Confirm before risky operations.
Schema migrations that drop or rename columns, deleting playthroughs, force‑resetting the database, anything destructive → confirm with the user first, even if it seems implied.

---

## 2. How to do work in this repo (the loop)

Every change follows this loop. Do **not** skip the read and the plan.

1. **Read `BUILD_INSTRUCTIONS.md`** (this file) — the principles and the checklist.
2. **Read `FILE_MAP.md`** — figure out which files own the thing you're changing.
3. **Re‑read the touched files** before editing. Don't trust the file map alone; the code is the source of truth.
4. **State a plan in chat** (3–6 bullets max) before editing:
   - Which checklist item this maps to (or "not on the list — proposing addition").
   - Which files you intend to touch and why.
   - What new logs you will add.
   - What you will manually verify after.
5. **Make the change.** Keep edits scoped. If you discover the change is bigger than the plan, stop and update the plan.
6. **Add or update logs** for any new stage/branch. Logs are part of the deliverable, not optional.
7. **Run the app** (`./start-test.sh`) and trigger the path you changed. Watch the logs. If you can't run it, say so explicitly.
8. **Tick the checklist** item in this file with a one‑line dated note. Update `FILE_MAP.md` if file responsibilities changed.
9. **Commit** with a short message naming the checklist item (e.g. `feat(M2.3): witness-filtered per-character prompt`).

If a step in the checklist is huge, **break it into sub‑steps in this file** before starting and tick them off as you go.

---

## 3. Logging contract (so bugs are findable)

Every stage of the pipeline must log:

- **Entry**: stage name, key inputs (truncated to ~500 chars for big strings), session id.
- **Decisions**: any AI call's prompt length, model used, raw response, parsed result. If it's JSON, log the *parsed* dict, not the raw string.
- **Mutations**: any DB write — table, row id, the fields that changed, before/after for important values (trust, location, emotional_state).
- **Exit**: stage name, summary of what it produced (or "no‑op"), elapsed ms.
- **Errors**: full exception, stage name, all relevant ids, the inputs that triggered it. Use `logger.error(...)`. Never bare `except: pass`.

The `logs` table and the Tester panel are the primary debugging surface. **If a bug is hard to diagnose from the logs alone, that is a logging bug — fix the logs first.**

Categories to use (matches `Log.log_category`): `system`, `database`, `ai`, `memory`, `character`, `story`, `validation`, `director`, `spatial`, `knowledge`, `intake`.

---

## 4. Architecture (target shape)

This is what we are building toward. Items in the checklist below are the steps to get there. Don't pre‑build anything below that isn't on the list.

> **Vocabulary (R8):** "**prompt**" = what we send to the LLM (the structured `PromptBundle`, rendered for the model). "**context**" = the in‑world background of a character or scene — their situation, what they know, where they are, what they're feeling. Each in‑world context (character sheet, spatial state, director pressure, knowledge) gets assembled *into* the prompt, but isn't itself called "the prompt."

```
INTAKE → PARSE → TRIGGER → STATE_APPLY → DIRECTOR → PROMPT_BUILD(per‑character, witness‑filtered)
       → SCENE_SIMULATION (per NPC) → GENERATION → VALIDATION (regex + AI critic, repair loop)
       → PRESENTATION → STATE_UPDATE (mutations + memory writes, witness‑tagged)
```

Two stores:
- **SQLite (SQLAlchemy)** — hard facts: characters, positions, relationships, knowledge, goals, beliefs, flags, scene state. **Every fact has witnesses.**
- **ChromaDB (vector)** — soft recall: episodic memory texture, atmospheric callbacks. **Vector results are filtered by witness tags before being shown to a character.**

Two model tiers:
- **Small** (local Ollama 3B, or `*-3b-instruct:free`) — parsing, triggers, decisions, critic checks. Cheap, fast, narrow questions.
- **Large** (local Ollama 8B+, or `*-8b-instruct:free`, or paid DeepSeek for quality runs) — generation only.

---

## 5. THE CHECKLIST — what to build, in this order

> **Tick the box when done. Add a one‑line dated note under each ticked item with the commit hash or PR.**
> If you reorder items, write a note explaining why in the section header.
>
> Status legend: `[ ]` = not started, `[~]` = in progress, `[x]` = done.
> **Before starting M0**, also read `REFACTOR_FIRST.md` — it covers cleanup the current codebase needs before new features go on top.

---

### M0 — Refactor foundation (do this BEFORE new features)

See `REFACTOR_FIRST.md` for the full reasoning. These exist to make every later step possible without breaking the whole.

- [x] **M0.1** Extract a `Pipeline` class with one method per stage. `chat.py:send_message` should be ~30 lines that just orchestrates `pipeline.run(user_message)`.
  - 2026-06-28: `refactor(R1): extract ChatPipeline class` — `app.pipeline.ChatPipeline` owns every stage; `routers/chat.py` is now a thin shell.
- [x] **M0.2** Split `ContextBuilder.build_full_context()` into named getters that return *typed dicts*, not concatenated strings. Add a `build_for_character(character_id)` entry point that the per‑character path will use later.
  - 2026-06-28: `refactor(R2): typed ContextBundle with byte-for-byte legacy renderer` — typed `ContextBundle` in `pipeline/context_bundle.py`; `ContextBuilder.build_bundle()` and `build_for_character()` added; `build_full_context()` is now a deprecated alias.
- [x] **M0.3** Add a `pipeline_stage` log helper that auto‑tags every log inside a `with stage("CONTEXT"):` block. Update existing log sites to use it.
  - 2026-06-28: `refactor(R3): stage-tagged logging via pipeline_stage context manager` — contextvar-backed `pipeline_stage()` / `@pipeline_stage_method()` decorates every ChatPipeline method; `AppLogger` auto-injects `details["stage"]`; tester logs panel filters on it.
- [x] **M0.4** Confirm the validator is wired and *actually blocks* (current code logs and continues). Add a config flag `VALIDATION_MODE=warn|block|repair` defaulting to `warn`, so future steps can flip it.
  - 2026-06-28: `refactor(R4): wire VALIDATION_MODE so the validator can actually block/repair` — `settings.validation_mode` (warn|block|repair, default warn). `repair` regenerates once with an addendum on `controls_user`, re-validates, falls back to original on `validation.unrepairable`. M3 expands repair strategies.
- [x] **M0.5** Move all magic numbers (token limits, context message counts, importance thresholds) into `config.py` with named constants. No more `[:10]` and `min_importance=7` scattered in code.
  - 2026-06-28: `refactor(R5): lift tuning literals into config.py with trade-off comments` — seven new settings (`memory_flag_min_importance`, `memory_flag_top_n`, `max_dialogue_words`, `relationship_update_temperature`, `relationship_min_change`, `story_flag_analysis_temperature`, `generate_more_max_tokens`), each with a trade-off comment.

> **Pre-work also done (no matching M0 box):**
> - 2026-06-28: `refactor(R6): add witness/told_to columns and idempotent backfill migration` — stages the schema for M2.x per-character knowledge filtering. CRUD reads still ignore the columns; M2.3 will turn on filtering.
> - 2026-06-28: R7 sanity sweep — `FILE_MAP.md` updated for `pipeline/` and `migrations.py`; static check confirmed no `except: pass`. `start-test.sh` runtime verification is the last gate before deleting `REFACTOR_FIRST.md`.
> - 2026-06-28: `refactor(R8): vocabulary cleanup (context → prompt)` — `ContextBundle` → `PromptBundle`, `ContextBuilder` → `PromptBuilder`, pipeline stage `CONTEXT` → `PROMPT_BUILD`, `context_gather()` → `build_prompt()`, `build_full_context` → `build_prompt_string`, `AppLogger.prompt()` added (with `.context()` kept as deprecated alias for one commit), tester tab "AI Context" → "Prompt", `/admin/tester/context/` → `/admin/tester/prompt/`. After R8: "prompt" / "bundle" = LLM input; "context" = in-world background.

---

### M1 — Structured input parsing (kills problem #1 and #8)

> **Prompt-side down-payment done early (2026-06-28):** `story_generation_prompt` now
> instructs the model on the speech/action/thought convention (quotes = spoken; outside
> quotes = action or thought; ambiguous → treat as thought), ported from storyteller_v3's
> prompt before it was deleted (see `V3_SALVAGE.md` P-A, `docs/V3_REFERENCE.md`). This is
> only the *prompt* half — M1.1–M1.6 below are the *backend* half that actually parses and
> persists those fields and enforces them in code. The prompt asking nicely is not the fix;
> these boxes are.

- [ ] **M1.1** Define an `IntakeMessage` schema: `{speech: str|None, action: str|None, thought: str|None, raw: str}`. Treat `thought` as private — never surfaced to NPCs.
- [ ] **M1.2** Frontend: chat input has three optional modes. Default is `speech`. Users can prefix `*action*`, `(thought)`, or use a mode toggle. Document the syntax in‑app.
- [ ] **M1.3** Backend INTAKE stage parses raw input into `IntakeMessage`. Small‑model fallback parser for ambiguous input.
- [ ] **M1.4** Persist the parsed fields on `Conversation` rows (add columns `speech`, `action`, `thought`). Backfill existing rows with `speech = message`.
- [ ] **M1.5** Validator rule: if generated text contains the user character's name as a speaker (`Name:`, `Name said`), **regenerate**, do not just warn.
  - 2026-06-30: detection down-payment — widened `validator._check_user_character_control` to also catch present-tense and comma'd dialogue attribution and a broader speech-verb set (`say/says/whisper/mutter/reply/answer/tell/…`), and `re.escape`'d the user name (was a latent crash on names with regex metachars). Still **quote-anchored** on purpose: arbitrary action-control (`you leave the room`) can't be told apart from valid 2nd-person narration (`you watch him leave`) by regex — that's M3.2's critic. The **regenerate** half of this box only fires under `VALIDATION_MODE=repair` today; wiring it to always-regenerate (independent of mode) is the rest of M1.5. Verified with 10 unit cases (3 newly-caught, 4 false-positive guards). Box left open.
- [ ] **M1.6** When assembling the prompt input for an NPC, **exclude all user `thought` content**. Add a log line showing what was excluded.

---

### M2 — Per‑character, witness‑filtered prompt input (kills problems #2, #3, #7)

- [ ] **M2.1** Implement a `WitnessTag` model (or reuse `CharacterKnowledge` + `MemoryFlag`) so every fact records `who_witnessed` (list of character ids) and `who_was_told` (list of character ids).
- [ ] **M2.2** STATE_UPDATE: when storing a new memory/flag, **always** compute and store witnesses from the current `scene_characters` list. Never write a fact without witnesses.
- [ ] **M2.3** PROMPT_BUILD: replace the single `build_prompt_string()` with `build_prompt_bundle_for_character(char_id)` that filters `CharacterMemory`, `CharacterKnowledge`, `MemoryFlag` and (later) ChromaDB results to those where the character is a witness or was told. Remove the deprecated `build_prompt_string` once this lands.
- [ ] **M2.4** Re‑inject the **character sheet** (values, fears, would_never_do, would_always_do, decision_style, verbal_patterns, current_emotional_state, top 3 goals, internal_contradiction) at the top of every prompt that involves that character. Drift starts when these dilute.
  - **Reference:** `docs/V3_REFERENCE.md §2` (salvaged from v3) — render **main** characters with a full sheet and **side** characters with a compact block (token budget), and consider adding `example_correct`/`example_incorrect` voice-anchor fields to the character model to make drift concrete for the model.
- [ ] **M2.5** Add a logger line per character per turn: `"Character X sees N memories, M knowledge items, K flags"` — so it's obvious from logs when retrieval is empty.

---

### M3 — Validator with teeth (problems #1, #3, #4, #6, #7)

- [ ] **M3.1** Promote validator from "log issues" to "regenerate or repair." Wire `VALIDATION_MODE=repair` and test it.
- [ ] **M3.2** Add a small‑model **critic pass** with a narrow checklist prompt: `{controls_user, impossible_movement, out_of_character_compliance, mind_reading, knew_unknowable_fact}` → JSON yes/no per item, with one‑line evidence.
- [ ] **M3.3** Repair strategy: on `controls_user` or `mind_reading` → regenerate with the offending span quoted as "do not do this." On `impossible_movement` → ask the model to rewrite that paragraph only, given the spatial state.
- [ ] **M3.4** Cap regeneration retries (e.g. 2). On 3rd fail, fall back to the last partial response and log a `validation.unrepairable` error. Never loop forever.
- [ ] **M3.5** Validator logs **must** show: which checks ran, which failed, the offending span, the repair prompt sent, the new output.

---

### M4 — Spatial state (problem #6)

- [ ] **M4.1** Define a lightweight position model: per character in scene, store `position` (free text like "by the window") and `holding` (free text). Extend `SceneCharacter` if it fits, else add a sibling table.
- [ ] **M4.2** STATE_APPLY: when the user `action` implies movement ("I walk to the bar"), update the user character's position before generation.
- [ ] **M4.3** STATE_UPDATE: after generation, extract NPC position/holding changes from the narrative with a small‑model parser, write them back.
- [ ] **M4.4** Validator check `impossible_movement`: given current positions, did the new text claim someone "moved closer" / "took the cup" / "left the room" without a setup? Repair if so.

---

### M5 — Director layer (problem #5)

- [ ] **M5.1** Add a `StoryDirector` module. On each turn, it sees: open arcs, unresolved conflicts, time since last tension beat, NPC goals.
- [ ] **M5.2** Director emits a `directorial_pressure` object: `{escalate: bool, who_acts: char_id|null, what_pressure: text, why: text}`. This is *injected into the generation prompt*, not the validator.
  - **Reference:** `docs/V3_REFERENCE.md §1` (salvaged from v3) — if this pressure object ever comes back *from the model* as structured output, the brace-counting parser there handles braces/quotes inside values with a salvage fallback. (We chose to compute pressure in code, not parse it out — so this is a fallback reference only.)
- [ ] **M5.3** NPC agendas: each NPC's top active goal is **pushed forward at least slightly** each turn unless blocked. Log when an NPC takes a goal step.
- [ ] **M5.4** Tension meter: a single 0–1 float per playthrough, updated by STATE_UPDATE. Director uses it to decide whether to inject a complication.

---

### M6 — Vector memory (ChromaDB) — atmosphere, not facts

- [ ] **M6.1** Stand up ChromaDB (already in `requirements.txt`). One collection per playthrough.
- [ ] **M6.2** On STATE_UPDATE, embed and store *episodic* memory entries (the prose of what happened), tagged with `playthrough_id`, `witnesses`, `timestamp`.
- [ ] **M6.3** Retrieval: semantic search filtered by `witnesses contains current_character_id`. Top‑k results join with the structured `CharacterMemory` rows; do not duplicate.
- [ ] **M6.4** Hard rule: **canonical facts never come from the vector store.** If the model needs to know X's trust level, that comes from SQLite. Vector store is texture and callback only.

---

### M7 — Emotional state + time skips

- [ ] **M7.1** Implement decay on `CharacterState.current_emotional_state` toward `baseline_emotional_state` over in‑story time. Acute emotions decay fast, grief/love slow.
- [ ] **M7.2** On time‑skip narrative events, run the decay once before generating.
- [ ] **M7.3** Inject current state into character context (already partly done) — add `emotion_started_at` so the model knows how fresh the emotion is.

---

### M8 — Goal‑driven NPC simulation

> **Reference:** `docs/V3_REFERENCE.md §1` (salvaged from v3) holds v3's per-NPC
> `background_context({character, intention, will_act, mood})` convention and its output
> parser. v3 merged intent into the generation output; v2 keeps the **separate decision
> call** (see `DIRECTION.md` for why). Use the reference for the *intent fields* (esp.
> `will_act` → skip silent NPCs) and the parser, not for the merged-output approach.

- [ ] **M8.1** SCENE_SIMULATION (per NPC, parallelizable): use `character_goals` + current state + relationships to decide an *intent* this turn. Store on `SceneCharacter`.
- [ ] **M8.2** Generation prompt receives each NPC's intent (terse, 1 line). NPCs act on intents; they don't all need to speak.
- [ ] **M8.3** Validator check `out_of_character_compliance`: did the NPC suddenly agree to something their goal contradicts? Repair.

---

### M9 — Knowledge tracking, end‑to‑end

- [ ] **M9.1** STATE_UPDATE extracts new "facts learned" per character (small‑model call) and writes to `CharacterKnowledge` with `source`, `certainty`, witnesses.
- [ ] **M9.2** Context for character X must include their `CharacterKnowledge`, ranked by `importance × recency × access_count`.
- [ ] **M9.3** Validator check `knew_unknowable_fact`: did the NPC reference something they have no `CharacterKnowledge` row for and weren't a witness to? Repair.

---

### M10 — Authoring & playthrough UX

- [ ] **M10.1** Story authoring: an "Edit Story" panel that lets the user create/edit characters, locations, relationships, opening scene from the UI — not just JSON.
- [ ] **M10.2** Playthrough viewer: surface positions, knowledge, goals, beliefs per character so the user can sanity‑check the world model.
- [ ] **M10.3** Manual override: user can edit any character/scene field mid‑playthrough (and the change is logged as `manual_override`).
- [ ] **M10.4** Save/load / export playthrough as a single file.

---

### M11 — Quality of life & polish

- [ ] **M11.1** Streaming responses from the LLM so the UI shows tokens as they arrive.
- [ ] **M11.2** Rate‑limit / cost tracking per provider, visible in Settings.
- [ ] **M11.3** Prompt library viewer in the Tester panel — see every prompt that was sent, copy/edit/replay.
- [ ] **M11.4** Replay mode: re‑run a turn with a modified prompt or modified state, see how the output changes. Critical for iterating on prompts.

---

### M12 — Stretch / later

- [ ] **M12.1** Multi‑user playthroughs.
- [ ] **M12.2** Mixed model strategy: local small for parsing/critic, paid model (DeepSeek, etc.) for generation, configurable per stage.
- [ ] **M12.3** Auto‑summarization of old conversation chunks to free context room.
- [ ] **M12.4** Branching / save points within a playthrough.

---

## 6. When you're done

After finishing any checklist item:

- [ ] Box ticked with a dated note (date in `YYYY‑MM‑DD`, one line of what shipped).
- [ ] `FILE_MAP.md` updated if any file gained/lost responsibility.
- [ ] New logs verified by running the app and watching the Tester panel.
- [ ] A commit message that names the checklist item: `feat(M3.2): small-model critic pass`.

If you finished something **not** on the list, stop and add it to the list first (with rationale), then tick it.

---

## 7. Things to NEVER do (lessons from JanitorAI failure modes baked in)

- Never let generation see the user's `thought` field.
- Never let generation produce dialogue or actions for the user character. Validate and regenerate.
- Never load all memories globally; always filter by witnesses.
- Never silently change a character's `would_never_do` to make a scene work. The whole point is that the character resists.
- Never store a "fact" without witnesses. If you can't say who knows it, you can't safely retrieve it.
- Never trust an LLM JSON response without parsing it defensively. Always log the raw response *and* the parsed dict.
- Never put a value the model has to "remember" only in the prompt. It goes in SQLite first, gets re‑injected fresh each turn.
