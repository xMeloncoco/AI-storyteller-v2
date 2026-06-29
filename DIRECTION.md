# DIRECTION.md — longer-term product direction (tentative)

> Forward-looking notes that don't belong in the `BUILD_INSTRUCTIONS.md` checklist yet.
> These are **leanings**, not committed milestones. Read alongside `BUILD_INSTRUCTIONS.md`.

## Supabase + cross-device + phone access

**The want:** a good at-a-glance overview of all state, and eventually the ability to use
the app across devices — including from a phone.

**Why it's compatible with v2:** v2's architecture is database-agnostic. `P1` requires a
*relational* DB, not SQLite specifically. Supabase is managed Postgres, so the schema
(including witness columns) ports directly via the SQLAlchemy `DATABASE_URL`.

**The load-bearing constraint:** the Python backend pipeline stays the **only** path to
generation. Every turn must pass through the validator + witness filtering. A client
(desktop or phone) is always a thin client:

```
thin client (desktop / phone browser) → Python backend (pipeline + validator) → Supabase Postgres + model APIs
```

Never let a client call the model or the raw DB directly — that's the v3 mistake.

**This decomposes into 3 independent decisions** (do not need to happen together):

1. **DB swap — SQLite → Supabase Postgres.** Low cost (connstring + driver + port
   migrations). Buys the Studio table-browser *overview* immediately, even if everything
   else stays local. Can be done any time after the schema stabilizes.
2. **Web frontend — Electron desktop → web app.** Medium cost. Needed for phone access.
   This is the "reuse v3's React components" migration from `V3_SALVAGE.md §A`, now with a
   real justification.
3. **Backend hosting.** Where the Python pipeline runs.
   - *Cheap & private:* keep it on the PC, expose over Tailscale / a tunnel. Phone works
     when the PC is on; API keys never leave the machine.
   - *Full cloud:* host on Railway / Render / Fly.io. Always-on, but costs money and runs
     model usage in the cloud.

**Explicitly rejected:** rewriting the pipeline into Supabase Edge Functions
(TypeScript/Deno). That discards v2's Python backend — its core value — and repeats v3.

**Suggested sequencing:** finish M1–M3 of the engine on SQLite first (DB choice doesn't
affect that work) → do the DB swap whenever the Studio overview is wanted → web frontend
when phone access is wanted → pick hosting last (start with Tailscale).
