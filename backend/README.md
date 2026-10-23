# Agent backend

From `backend/`, install dependencies and configure Mistral:

```bash
uv sync
cp .env.example .env
```

Set `MISTRAL_API_KEY` in `.env`. `CHAT_MODEL` selects the Mistral model for
both agents (defaults to `mistral-large-latest` if unset).

Start Agent Server:

```bash
uv run langgraph dev --no-browser
```

The API runs at `http://localhost:2024`. `langgraph.json` registers two graphs:

- `deep_agent`: Deep Agents with built-in context compression and opt-in planning.
- `agent`: LangChain with explicit summarization middleware.

Both exported graphs use server-managed conversation persistence. Neither runs
the demo on import. The development server stores local state in the ignored
`.langgraph_api/` directory; this is not a production database.

## Agent Chat UI

In `frontend/`, copy `.env.example` to `.env.local` if you have not already
configured the UI. Set:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=deep_agent
```

Then run `pnpm install` and `pnpm dev` from `frontend/`, and open
`http://localhost:3000`. No LangSmith API key is needed for local chat.
The Mistral key stays in the backend. Both servers must be running.

To compare approaches, open `http://localhost:3000/?assistantId=agent` for
LangChain or `http://localhost:3000/?assistantId=deep_agent` for Deep Agents.
Start a new conversation when switching agents. The UI manages thread IDs;
continuing an existing thread restores its conversation state.

Deep Agents retains its default virtual filesystem and built-in tools; no host
filesystem, shell backend, custom skills, or cross-thread memory store is configured.

## Standalone demos

```bash
uv run python -m app.agent
uv run python -m app.deep_agent
```

These run a two-turn memory example using a process-local `InMemorySaver`.
Standalone memory is separate from the server's chat threads and is lost on exit.
