# V3_REFERENCE.md — preserved artifacts from storyteller_v3

> **Why this file exists:** `storyteller_v3` is being deleted. A few of its pieces are
> worth keeping as references for *later* milestones, but they are fiddly to reconstruct
> from memory, so they are copied here **verbatim**. This is documentation, not active
> code — nothing here is wired in. Do not build from it ahead of the milestone it maps to
> (`BUILD_INSTRUCTIONS.md` P7).
>
> What was already taken (not preserved here, it's live):
> - Visual style → `frontend/src/styles.css` (V3_SALVAGE §A).
> - Prompt rules (identity / narration / user-character say-do-think / world-NPC) →
>   `backend/app/ai/prompts.py::story_generation_prompt` (V3_SALVAGE P-A).

---

## 1. Structured side-channel output + parser  → maps to M5 (director) / M8 (NPC intent)

v3 had the model emit per-NPC intentions and off-screen world events as pseudo-function
calls *alongside* the narrative, then parsed them out. **We deliberately did NOT adopt
this** (v2 computes NPC decisions in a separate call — see `DIRECTION.md`). Keep it only
as a reference for when M5/M8 want a structured side-channel, and for the robust
brace-counting parser (handles braces/parens inside string values, with a salvage path).

### 1a. The output convention (from v3 systemPrompt.js `buildOutputInstructions`)

```
You must always output the following function calls before writing any narrative:
1. background_context({ character, intention, will_act, mood }) — one call per NPC in the scene
2. world_background({ events }) — one call describing anything happening in the world
   outside the immediate scene that may be relevant (weather changing, distant sounds,
   off-screen events). Omit if nothing is happening outside the scene.
3. narrative({ text }) — the actual story response

Do not write any narrative text outside the narrative() function call.
```

Note the `will_act` field — this is the "does this NPC even respond this turn?" signal
(lets you skip silent NPCs). In v2 that decision lives in the separate decision call
(`prompts.py::character_decision_prompt`), not in the generation output.

### 1b. The parser (v3 `src/utils/parseNarratorResponse.js`, verbatim)

```javascript
/**
 * Parses DeepSeek's raw response text into structured parts.
 * background_context({...}) / world_background({...}) / narrative({...})
 */

function extractFunctionCall(text, funcName) {
  const results = []
  const pattern = new RegExp(funcName + '\\s*\\(\\s*\\{', 'g')
  let match

  while ((match = pattern.exec(text)) !== null) {
    const braceStart = text.indexOf('{', match.index + funcName.length)
    if (braceStart === -1) continue

    let depth = 0
    let end = -1
    for (let i = braceStart; i < text.length; i++) {
      if (text[i] === '{') depth++
      else if (text[i] === '}') {
        depth--
        if (depth === 0) { end = i; break }
      }
    }
    if (end === -1) continue

    const jsonStr = text.slice(braceStart, end + 1)
    try {
      results.push(JSON.parse(jsonStr))
    } catch {
      // Salvage — sometimes the JSON has unescaped quotes in values
      results.push({ raw: jsonStr, parseError: true })
    }
  }
  return results
}

function removeAllFunctionCalls(text, funcName) {
  const pattern = new RegExp(funcName + '\\s*\\(\\s*\\{', 'g')
  let match
  const ranges = []

  while ((match = pattern.exec(text)) !== null) {
    const braceStart = text.indexOf('{', match.index + funcName.length)
    if (braceStart === -1) continue

    let depth = 0
    let end = -1
    for (let i = braceStart; i < text.length; i++) {
      if (text[i] === '{') depth++
      else if (text[i] === '}') {
        depth--
        if (depth === 0) { end = i; break }
      }
    }
    if (end === -1) continue

    let closeParenIdx = end + 1
    while (closeParenIdx < text.length && text[closeParenIdx] !== ')') {
      if (text[closeParenIdx].trim()) break
      closeParenIdx++
    }
    if (closeParenIdx < text.length && text[closeParenIdx] === ')') end = closeParenIdx

    ranges.push([match.index, end + 1])
  }

  let result = text
  for (let i = ranges.length - 1; i >= 0; i--) {
    result = result.slice(0, ranges[i][0]) + result.slice(ranges[i][1])
  }
  return result
}

function extractNarrativeText(rawText) {
  const narrativeCalls = extractFunctionCall(rawText, 'narrative')
  if (narrativeCalls.length > 0 && narrativeCalls[0].text) return narrativeCalls[0].text

  let cleaned = rawText
  cleaned = removeAllFunctionCalls(cleaned, 'background_context')
  cleaned = removeAllFunctionCalls(cleaned, 'world_background')
  cleaned = removeAllFunctionCalls(cleaned, 'narrative')
  cleaned = cleaned.trim()
  if (cleaned.length > 0) return cleaned
  return rawText
}

export function parseNarratorResponse(rawText) {
  const backgroundContext = extractFunctionCall(rawText, 'background_context')
  const worldBackgroundArr = extractFunctionCall(rawText, 'world_background')
  const worldBackground = worldBackgroundArr.length > 0 ? worldBackgroundArr[0] : null
  const narrativeText = extractNarrativeText(rawText)
  return { narrativeText, backgroundContext, worldBackground, raw: rawText }
}
```

When v2 reaches M8, the Python equivalent is a brace-counting scan over the model output;
porting the algorithm above is faster than rediscovering the edge cases.

---

## 2. Character typing (full vs compact blocks)  → maps to M2.4 (character-sheet injection)

v3 tagged each character `user` / `main` / `side` and rendered **main** NPCs with a full
sheet (incl. correct/incorrect example lines) and **side** NPCs with a compact block — a
cheap token budget. v2 already stores `character_type`; M2.4 should branch the per-character
prompt block on it the same way. Reference rendering (v3 `systemPrompt.js`, trimmed):

```javascript
// Main characters — full detail (sheet + hard rules + example lines + state)
function buildFullCharacterBlock(name, char, userName) {
  const sheet = char.sheet || {}
  const lines = [`**${name}** (${sheet.name || name})`]
  if (sheet.role) lines.push(`Role: ${sheet.role}`)
  if (sheet.personality) lines.push(`Personality: ${sheet.personality}`)
  if (sheet.hard_rules?.length) { lines.push('Hard rules:'); sheet.hard_rules.forEach(r => lines.push(`  - ${r}`)) }
  if (sheet.speech_style) lines.push(`Speech style: ${sheet.speech_style}`)

  // "Example correct" vs "Example WRONG (drift — never do this)" lines, collected from
  // any fields prefixed example_correct* / example_incorrect*. These anchor voice and
  // make drift (failure mode #3) concrete for the model.
  const correct = collectPrefixedFields(sheet, 'example_correct')
  const wrong = collectPrefixedFields(sheet, 'example_incorrect')
  if (correct.length) { lines.push(`Example correct ${name} response:`); correct.forEach(e => lines.push(`  "${e}"`)) }
  if (wrong.length) { lines.push(`Example WRONG ${name} response (drift — never do this):`); wrong.forEach(e => lines.push(`  "${e}"`)) }

  const state = char.state || {}
  lines.push(`Current mood: ${state.current_mood || 'unknown'}`)
  lines.push(`Current goal: ${state.current_goal || 'none'}`)
  if (state.knowledge?.length) { lines.push('Knows:'); state.knowledge.forEach(k => lines.push(`  - ${k}`)) }
  return lines.join('\n')
}

// Side characters — compact (role/personality + rules + one example + one-line state)
function buildCompactCharacterBlock(name, char) { /* same fields, fewer of them */ }

function collectPrefixedFields(obj, prefix) {
  return Object.entries(obj)
    .filter(([k]) => k.startsWith(prefix))
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, v]) => v)
}
```

The genuinely portable ideas: (1) **full vs compact by character type** to save tokens on
side characters; (2) **`example_correct` / `example_incorrect` voice anchors** baked into
the sheet — v2's character model has `would_never_do`/`would_always_do` but no example
lines; consider adding example fields when M2.4 lands.

---

## 3. Everything else from v3

Deliberately NOT carried over (see `V3_SALVAGE.md §0` for the reasoning): Supabase
*client-side* design, state-as-JSON-blobs, and prompt-as-enforcement. The database product
(Supabase Postgres) is still a live future option — see `DIRECTION.md`.
