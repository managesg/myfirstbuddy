# MyFirstBuddy

A child's first AI companion, designed by the child, built to send them back outside.

**Prototype built in one sitting for a hackathon. SAMPLE DATA ONLY** (child "Mia, age 7", companion "Pip the purple dragon"). No real child data, no accounts. It is not a certified or "safe for kids" product and must not be used with real children without proper review.

## What it does
- The child describes a companion ("a purple dragon who loves math") and gets a character card.
- Learning in tiny steps: replies of at most 40 words, one idea, a question back.
- Offline mission every 3rd turn (draw it, ask a grown-up, go outside).
- Session timer; at zero the buddy says a short goodbye with one mission, input locks, and the screen says "Time to play offline, Mia!" (no continue button).
- Parent area (locked behind a 4-digit PIN, sample PIN `2468`, stored as salted sha256): settings (child, age band, minutes, topics, goal), session summaries, safety flags.
- Keyword safety pre-check (`address|phone|where do you live|password|kill|gun|sex|secret|hurt`) runs before any model call: canned redirect, parent flag, no model call.
- Model: Muse Ember (`meta/muse-ember`) via OpenRouter. Proof tab shows generation ids, tokens, cost, cache hits.
- Cache: every model response is stored in `cache/` keyed by sha256 of the messages, so replays cost $0.

## Run
```
set OPENROUTER_API_KEY=...        # only needed for uncached prompts
python server.py                  # http://127.0.0.1:8765  (env PORT, HOST)
python server.py --selftest
python record.py video            # needs playwright + chrome; replays cached turns
```
Python stdlib only. The key is read server-side from the environment (or Windows user env) and is never sent to the browser or committed.

## API
`GET /api/settings` (no PIN fields) | `POST /api/unlock {pin}` -> `{token}` (send as `X-Parent-Token`) | `POST /api/settings`, `POST /api/companion {name,persona,emoji,color}`, `GET /api/summaries` (token required) | `POST /api/chat {text,wind_down}` -> `{reply,mission,topic,safety_flag,learning_note,turn}` | `POST /api/end {minutes}` -> summary JSON | `POST /api/reset` | `GET /api/proof`.

## Safety and privacy principles (COPPA-style, not a compliance claim)
No personal information collected or requested (prompt forbids names, addresses, schools, phones, photos); parent controls time, topics and goal; no dark patterns (no streaks, no "keep chatting", the session ends itself); flags are shown to the parent; sample data only; nothing leaves the machine except the prompts sent to OpenRouter. Known limits: the keyword filter is a floor, not a guarantee; the PIN has no attempt rate-limit; the model can still err.

## Proof (real measured numbers, `proof/`)
| Item | Value |
|---|---|
| Model | meta/muse-ember via OpenRouter |
| Live model calls logged | 9 (3 early calls hit the 300-token cap because the model spends tokens on reasoning, content was empty; fixed with max_tokens 1200 and low reasoning effort) |
| Cost of those calls (from `usage.cost`) | $0.002576 total; about $0.0003 per turn |
| Cache hits (replays, $0) | 11 at time of writing, see `proof/openrouter_log.jsonl` |
| Avg live latency | 2.2 s |
| `/api/v1/key` usage before / after | 0.105585 / 0.118671 (delta $0.0131; larger than the log because the same key was also used by other hackathon work during the window) |
| Budget guard | server refuses live calls once logged spend reaches $0.40 |
| Estimate | one 2-minute session of about 6 calls is about $0.002, so a month of daily sessions is about $0.06 (under $1) |

Demo video: `demo/myfirstbuddy_demo.webm` (cached replay, sample data).
