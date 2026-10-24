# Backend

Python agents served through LangGraph Agent Server. The backend runs model
calls, maintains conversation state, and enforces per-user thread access.

## Prerequisites and configuration

Use Python 3.12 and uv. Complete the required Mistral, Supabase, and Google
configuration in the [shared setup guide](../docs/setup.md).

From `backend/`, install dependencies and create the environment file on first
setup. Preserve an existing `.env` rather than replacing it:

```bash
uv sync
cp .env.example .env
```

Configure these values in `.env`:

| Variable | Purpose |
| --- | --- |
| `MISTRAL_API_KEY` | Backend credential for model requests |
| `CHAT_MODEL` | Mistral model for both agents; the example uses `mistral-small-latest` |
| `SUPABASE_URL` | Project URL, matching the frontend's Supabase project |
| `SUPABASE_PUBLISHABLE_KEY` | Project publishable key used when validating user sessions |
| `LANGSMITH_TRACING` | Optional tracing; disabled in the example |

Optional LangSmith keys, project selection, and endpoints are covered in the
[tracing setup](../docs/setup.md#optional-langsmith-tracing).

## Run

```bash
uv run langgraph dev --no-browser
```

The API runs at `http://localhost:2024`. Stop it with Ctrl+C. Restart after
changing environment or server configuration.

`langgraph.json` exposes two graph IDs:

| Graph ID | Implementation |
| --- | --- |
| `deep_agent` | Deep Agents with built-in context compression and opt-in planning |
| `agent` | LangChain with explicit summarization middleware |

Both exported agents use server-managed checkpointing. The development server
stores state in the ignored `.langgraph_api/` directory. This is development
storage, not a production database or the planned research archive.

## Authentication and isolation

`app/auth.py` validates Supabase bearer tokens and uses the verified user ID to
enforce thread ownership. Users can access only their own conversations, state,
and runs. Graph definitions are shared and read-only; store access and other
resource types are denied. Studio's alternative authentication path is disabled.

Google is the frontend's sign-in provider; the backend validates Supabase
sessions independently of the identity provider. See the
[Google/Supabase guide](../docs/google-auth.md) for details.

Deep Agents uses a thread-scoped virtual filesystem and its built-in tools.
No host filesystem, shell backend, custom skills, or cross-thread memory store
is configured.

## Checks

```bash
uv run ruff check
uv run pytest -q
```

Unit tests run without external services. Live isolation tests require a running
server and fresh Supabase access tokens for two different users, provided through
`ISOLATION_TOKEN_A` and `ISOLATION_TOKEN_B`:

```bash
ISOLATION_API_URL=http://localhost:2024 uv run pytest -q tests/test_isolation.py
```

Without these variables the integration tests skip. They create and delete test
threads without making model calls.

## Standalone demos

```bash
uv run python -m app.agent
uv run python -m app.deep_agent
```

These run a two-turn memory example with process-local checkpointing, separate
from the server's threads. Standalone memory is lost when the process exits.

For browser chat and graph selection, see the [frontend README](../frontend/README.md).
