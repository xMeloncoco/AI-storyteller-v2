# V3_SALVAGE.md — what to take from storyteller_v3 before M1

> **Read `BUILD_INSTRUCTIONS.md` first.** This is a pre-M1 cleanup list, in the same
> spirit as the old `REFACTOR_FIRST.md`: small, self-contained improvements lifted from
> the abandoned `storyteller_v3` prototype. Do these (or the subset you want) **before
> starting M1**, then delete this file.
>
> Status legend: `[ ]` not started, `[~]` in progress, `[x]` done. Tick with a dated
> one-line note and a commit hash, same as the checklist in `BUILD_INSTRUCTIONS.md`.
>
> **⚠️ `storyteller_v3` is being deleted.** Every item still pointing at a `storyteller_v3/…`
> path has had its content copied into this repo first — the not-yet-built prompt ideas
> (P-B, P-C) now live verbatim in `docs/V3_REFERENCE.md`. The old `Source:` line numbers
> below are kept only for provenance; do not expect those files to exist.

---

## 0. Context — why this list exists

`storyteller_v3` was a React/Vite + Supabase + DeepSeek prototype. Its **engine is the
wrong architecture** for our goals (it leans on one big system prompt and asks the model
to behave — the exact thing `BUILD_INSTRUCTIONS.md §0` says we are replacing). We are
**not** migrating to it. But its **presentation layer and a few prompt-assembly ideas are
genuinely cleaner than v2's**, and they are cheap to port.

**Explicitly NOT taking from v3** (do not "salvage" these):

- **v3's client-side-everything design.** The browser holding all state and calling the
  model directly. This bypasses the backend pipeline — and therefore the validator and
  witness filtering — which is the whole point of v2. The Python backend must stay the
  **only** path to generation (desktop or phone client → Python pipeline → DB + model).
- **State-as-JSON-blobs.** v3 stores world/scene state as opaque JSON and `JSON.stringify`s
  it into the prompt. Violates `P1`/`P3` (no per-character filtering at the data layer).
  Keep v2's relational schema even if the DB moves.
- **Prompt-as-enforcement.** v3's "NPCs only know what they witnessed" is a *prompt line*,
  not a code rule. That is failure mode #7. Our validator + witness columns are the fix.

> **Note on Supabase (corrected):** Supabase *itself* is fine and is a likely future
> direction — see `DIRECTION.md`. Supabase is just managed Postgres, and `P1` says
> "relational DB," not "SQLite." Swapping the SQLAlchemy `DATABASE_URL` from SQLite to
> Supabase Postgres is compatible with the whole architecture and gives a Studio table
> browser for overview. What we reject above is v3's *client-side pipeline*, not the
> database product.

Everything below is presentation or a portable idea — none of it touches the hard-state
architecture.

---

## A. Visual / frontend (this is what makes v3 "look better")

The palette is **already the same** in both apps (`#1a1a2e` / `#16213e` / `#0f3460` /
`#e0e0e0`). v3 only *looks* more polished because it is structured better. These are pure
CSS/markup changes with **zero backend impact**.

- [x] **V1 — Design tokens.** v2's `frontend/src/styles.css` hardcodes hex values
  everywhere. Lift v3's `:root` variable block (`src/index.css`) into v2 and replace the
  hardcoded hexes with `var(--…)`. This is the single highest-leverage visual change and a
  prerequisite for every other style tweak.
  - Source: `storyteller_v3/src/index.css` lines 9–28.
  - 2026-06-28: full `styles.css` rewrite onto a `:root` token block (v3 palette + pink
    accent). All class names preserved, so the vanilla-JS components are untouched.
- [x] **V2 — Message bubbles.** Adopt v3's chat bubble style: user messages right-aligned,
  narrator left-aligned, asymmetric rounded corners, `max-width: 85%`, uppercase role
  label. Much more readable than a flat transcript.
  - Source: `storyteller_v3/src/components/ChatPanel.css` lines 24–55.
  - 2026-06-28: `#chat-messages` is now a flex column; `.message.user`/`.message.narrator`
    align right/left with asymmetric corners; `.message-header` is an uppercase label.
- [x] **V3 — Typing indicator.** The three-dot bouncing "narrator is writing" animation
  while a turn is generating. Small, but makes the app feel alive during the (slow) local
  model calls.
  - Source: `storyteller_v3/src/components/ChatPanel.css` lines 113–139.
  - 2026-06-28: `.chat-typing` CSS + `ChatComponent.showTypingIndicator()` /
    `removeTypingIndicator()`; shown on `setLoading(true)`, replaced when the real message
    arrives. Renders as a `.message.narrator` bubble so it matches the new chat style.
- [ ] **V4 — Floating overlay panels + debug dropdown.** v3 puts Log / World State /
  System Prompt behind a single "Debug" dropdown that opens centered floating overlay
  panels (with an error-count badge), instead of v2's always-present tester chrome. Cleaner
  default view; debug surface is one click away. Maps onto v2's existing Tester/Logs panels
  — keep the same data, restyle the container.
  - Source: `storyteller_v3/src/App.css` lines 53–168, `App.jsx` lines 165–230.
- [x] **V5 — Custom scrollbars.** Thin themed `::-webkit-scrollbar` styling. Trivial,
  cohesive.
  - Source: `storyteller_v3/src/index.css` lines 43–55.
  - 2026-06-28: scrollbars down to 6px on themed tokens.

> **V4 (overlay panels + debug dropdown) is intentionally left for a follow-up** — it's a
> UX restructure of the working Tester/Logs screens (JS + markup), not pure visual, so it
> carries more risk than reward right now. Revisit alongside the React-frontend decision
> below. V3 (typing indicator) is done.

> **Bigger decision (not a checklist item — decide separately):** whether to replace v2's
> vanilla-JS Electron renderer with a **React frontend** that reuses v3's components,
> pointed at v2's REST API. This gets the v3 look "for free" and is more legible than one
> large `renderer.js`, but it's a real frontend rewrite. Recommendation: do **V1–V5** first
> (cheap, immediate ~80% of the v3 feel), then evaluate the React migration as its own
> project once M1–M3 of the engine are in. Do **not** start the rewrite as part of this
> list.

---

## B. Prompt-assembly ideas worth borrowing

These inform v2's `backend/app/ai/prompt_builder.py` and the roadmap. Treat as references,
not drop-ins — port them in the spirit of the principle they map to, and don't pre-build
ahead of the relevant milestone (`P7`).

- [x] **P-A — Section-builder pattern + prompt rules.** v3's `systemPrompt.js` composes the
  prompt from small labeled `[SECTION]` blocks. Its actual *rules* (narrator identity,
  narration, the user-character say/do/think convention, world/NPC knowledge + physical
  consistency) were cleaner and more complete than v2's old ALL-CAPS rules wall.
  - 2026-06-28: ported those rules into `backend/app/ai/prompts.py::story_generation_prompt`
    as labeled sections, keeping v2's injection points (context bundle, character decisions,
    user action) and **plain-narrative output**. This is also the prompt-side down-payment
    on **M1** (the matching backend parse of speech/action/thought is M1.3+). The broader
    `prompt_builder.py` section refactor remains optional, not done.
- [ ] **P-B — Character typing (`user` / `main` / `side`).** v3 tags each character so
  main NPCs get a **full** sheet block and side NPCs get a **compact** one — a simple,
  effective token budget. Fold this into **M2.4** (character-sheet re-injection) rather
  than doing it now; note it here so it isn't forgotten.
  - Reference (v3 deleted): rendering snippet preserved in `docs/V3_REFERENCE.md §2`.
- [ ] **P-C — Structured side-channel output + robust parser.** v3 has the model emit
  `background_context({character, intention, will_act, mood})` per NPC and
  `world_background({events})` alongside the `narrative({text})`, then parses them with a
  brace-counting parser that has a salvage fallback for malformed JSON. The **idea** maps
  onto **M8** (NPC intent) and **M5** (director pressure). Do not build ahead of M5/M8 —
  and recall we chose v2's *separate decision call* over this merged-output style
  (`DIRECTION.md`), so this is a reference, not a plan.
  - Reference (v3 deleted): output convention + full parser preserved verbatim in
    `docs/V3_REFERENCE.md §1`.

---

## C. When you're done

- [ ] Each box ticked has a dated note + commit hash.
- [ ] `FILE_MAP.md` updated if any frontend file gained/lost responsibility.
- [ ] Visual changes verified by running the app (`start-test.bat` / `./start-test.sh`).
- [ ] Delete this file once A is done and B items are either done or folded into the
      `BUILD_INSTRUCTIONS.md` checklist notes for M2/M5/M8.
