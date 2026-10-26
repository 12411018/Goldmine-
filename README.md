# Goldmine AI

Goldmine AI is a React chat client backed by a FastAPI service. Supabase Auth provides user sessions; the API verifies access tokens and uses Prisma Client Python to persist profiles, chats, messages, responses, and memories in PostgreSQL. Provider adapters call OpenRouter, Gemini, and Hugging Face from the backend. Provider credentials and the Supabase service-role key must remain server-side.

## Setup

Prerequisites: Python 3.11+, Node.js/npm, a PostgreSQL database (Supabase is supported), and an OpenRouter API key. The app defaults to an allowlist of explicitly free model endpoints; free-provider quotas and model availability can change.

1. Copy `.env.example` to the repository root as `.env` and fill in the values locally. Do not commit `.env`.
2. Create a Python environment and install backend dependencies:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   ```

3. Apply the SQL files in `supabase/migrations/` to the Supabase PostgreSQL project in numeric order (for example, with the Supabase CLI linked to the intended project, or through the SQL editor). Migration `008_research_upload_synthesis.sql` adds provenance fields and creates the private document bucket.
4. Generate the Python Prisma client from the repository root:

   ```powershell
   prisma generate --schema backend/prisma/schema.prisma
   ```

   `DATABASE_URL` should use the application connection endpoint; `DIRECT_URL` should use a direct PostgreSQL endpoint for schema operations. Keep both server-only.
5. Start the API from the repository root:

   ```powershell
   python run_backend.py
   ```

   The API listens on `http://localhost:8000`; health information is at `/api/health`.
6. In another terminal, start the web client:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Vite serves the app on `http://localhost:5173`. Only `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_URL` belong in browser-visible configuration. Never use a `VITE_` prefix for private credentials.

## Environment variables

| Variable | Used by | Required for |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | Backend | OpenRouter free model endpoints |
| `FREE_MODELS_ONLY` | Backend | Defaults to `true`; hides Gemini/Hugging Face and restricts Goldmine to allowlisted `:free` endpoints |
| `HF_TOKEN` | Backend | Hugging Face provider (only when free-only mode is explicitly disabled) |
| `GOOGLE_API_KEY` | Backend | Gemini provider (only when free-only mode is explicitly disabled) |
| `SYNTHESIS_MODEL_ID` | Backend, optional | Exact configured model ID used for multi-model synthesis; defaults to the highest-scoring responder |
| `SUPABASE_URL` | Backend | Auth token verification and server Supabase client |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend only | Server Supabase client; grants elevated access |
| `DATABASE_URL` | Prisma runtime | PostgreSQL application connection |
| `DIRECT_URL` | Prisma schema tooling | Direct PostgreSQL connection |
| `VITE_SUPABASE_URL` | Frontend | Supabase Auth client |
| `VITE_SUPABASE_ANON_KEY` | Frontend | Public Supabase client key (RLS still required) |
| `VITE_API_URL` | Frontend | FastAPI base URL; defaults to localhost:8000 |
| `SEARCH_API_KEY` | Backend, optional | Tavily web research when the user enables research for a message |

The backend resolves the root `.env` relative to its source file, so starting it from the repository root or `backend` uses the same configuration. Explicit process environment variables take precedence. Keep `FREE_MODELS_ONLY=true` (the default) to prevent requests from routing to Gemini or Hugging Face. Set `OPENROUTER_API_KEY` in the backend environment to enable the free model allowlist; do not put it in a `VITE_` variable. Free model endpoints can have daily limits and their providers may retain prompts, so do not submit confidential data.

## Development checks

```powershell
cd backend
python -m pytest tests
cd frontend
npm run build
npm run lint
```

Provider calls are not needed for unit tests. Do not run schema migrations against production as part of local development without confirming the target database.

## Current scope and limitations

- Single-model chat streams provider deltas. Multi-model chat collects up to three configured responses, then makes a separate synthesis call using a configured synthesis model or another available model that did not produce a candidate response. `SYNTHESIS_MODEL_ID` selects the synthesis model when it is not one of the candidate models. If no separate model is available, fewer than two models answer, or synthesis fails, the UI labels the individual-response fallback.
- Evaluation scores are heuristic signals, not a guarantee of factual correctness. Search sources are real Tavily results; the app does not independently verify each cited claim.
- Web research is opt-in per message and requires `SEARCH_API_KEY`. The key remains on the backend.
- Private document uploads support PDF, TXT, and Markdown up to 10 MB each. PDFs are limited to 120 pages; scanned PDF OCR and DOCX are not supported. Relevant text excerpts are selected for the prompt; original extracted text remains in the user-owned attachment row until removed.
- The authenticated frontend uses only the public Supabase URL and anon key. Provider and service-role credentials remain server-side.
- Free-only model mode is enabled by default and exposes only four backend allowlisted OpenRouter model IDs ending in `:free`. The OpenRouter free plan currently limits free-model requests to 50/day; endpoint availability and model IDs may change. The allowlist prevents Goldmine from silently using a paid model.
- Memory management is available from the account menu and uses the authenticated API. Context retrieval is best-effort and currently uses the server Supabase client.
