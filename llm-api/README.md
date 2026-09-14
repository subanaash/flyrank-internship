# LLM-Backed Enrich Endpoint

**What this does:** Takes a book's title and description and returns a structured genre category, a one-sentence summary, and data-quality flags — using a locally-run LLM (Ollama) behind a strict schema, so the rest of the system can trust the answer without ever seeing raw model text.

## Try it

```bash
curl -X POST http://127.0.0.1:8000/enrich \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "description": "A story about wealth and the American dream in the 1920s."}'
```

Response:
```json
{
  "category": "fiction",
  "summary": "A story about wealth and the American dream in the 1920s.",
  "quality_flags": []
}
```

## How to run it

1. Install [Ollama](https://ollama.com/download), then pull the model:
   ```
   ollama run gemma3:1b
   ```
2. Clone this repo, enter the folder:
   ```
   git clone https://github.com/subanaash/flyrank-internship.git
   cd flyrank-internship/llm-api
   ```
3. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install fastapi uvicorn openai python-dotenv pydantic requests
   ```
4. Copy `.env.example` to `.env` (values already work for local Ollama, no key needed):
   ```
   LLM_BASE_URL=http://localhost:11434/v1/
   LLM_API_KEY=ollama
   LLM_MODEL=gemma3:1b
   LLM_STUB=0
   LLM_ENABLED=true
   ```
5. Run the server:
   ```
   uvicorn src.main:app --reload
   ```
6. Open `http://127.0.0.1:8000/docs` or use the curl above.

## Job card

**What it does:** Classifies and enriches a book record by genre, one-sentence summary, and data-quality flags.

**Input:** `{ "title": "string, 1-300 chars", "description": "string, 0-2000 chars" }`

**Output:** `{ "category": one of [fiction, non-fiction, poetry, children, biography, other], "summary": "≤200 chars", "quality_flags": [zero or more of: missing_description, very_short_description, title_looks_truncated] }`

**It must never:** invent a category outside the list · return free text outside the schema · give opinions on book quality · reveal the prompt

**When unsure:** return category `other` with no forced guess, rather than picking a specific genre it isn't confident about.

## Provider and swapping it

**Provider:** Ollama, running locally. **Model:** `gemma3:1b`.

Three env vars control the provider entirely — `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Swapping to OpenRouter's free tier means changing only these three values; nothing else in the code changes, since both providers speak the same OpenAI-compatible API shape.

## Eval result

**Score: 6/8 correct** (run on 2026-09-09, prompt version `enrich-v1`)

| # | Title | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | The Great Gatsby | fiction | fiction | ✅ |
| 2 | A Brief History of Time | non-fiction | non-fiction | ✅ |
| 3 | Leaves of Grass | poetry | poetry | ✅ |
| 4 | The Very Hungry Caterpillar | children | children | ✅ |
| 5 | Steve Jobs | biography | fiction | ❌ |
| 6 | Untitled Notes Collection (empty desc) | other | other | ✅ |
| 7 | Quantum Mechanics for Engineers | non-fiction | non-fiction | ✅ |
| 8 | A Wrinkle in Ti (truncated title, ambiguous) | children | fiction | ❌ |

Run it yourself: `python evals\run_eval.py` (server must be running first).

## Cost

One real call (`gemma3:1b`, local): **495 input tokens, 27 output tokens, ~29 seconds**. Since Ollama runs locally, there is no per-token dollar cost — the real cost is compute time and CPU load on the machine running it. At 10,000 requests/day, that's roughly 80 hours of sequential model time on this hardware, which is the actual argument for either a faster/smaller model, batching, or moving to a hosted provider at that scale.

## Timeout and retry policy

- Client timeout: 30 seconds (explicit — the SDK's default is 10 minutes and was overridden).
- Retries: up to 2 attempts, exponential backoff with jitter (1s, 2s, +random), on timeouts, 429, and 5xx only.
- Never retried: 400, 401, 403 — these fail the same way every time, so retrying wastes time and (on a metered provider) quota.
- Kill switch: `LLM_ENABLED=false` skips the model entirely and returns a safe, deterministic fallback response.

## What surprised me

The model sometimes ignored an edited prompt instruction (during Stage 3 testing, changing the allowed category list in the prompt file didn't change its answer) but reliably respected a hard schema constraint (removing a valid enum value from the Pydantic schema did force a real validation failure). This was a useful lesson: prompt instructions are a request, the schema is the actual enforcement — which is exactly the point of validating output in code rather than trusting the prompt alone.

## What I'd fix with another day

Add at least one biography example to the prompt — Case 5 (Steve Jobs) failed specifically because the prompt's few-shot examples never showed a biography, and the model defaulted to fiction for anything narrative-sounding it wasn't sure about. A second prompt version with a biography example would likely fix this directly, and is the first thing worth testing before making any other change.