# Frontend

A customized Agent Chat UI built with Next.js and React. It provides Google
sign-in, streaming chat, and private conversation history for the backend agents.

## Prerequisites and configuration

Use Node.js matching `.nvmrc` (22) and pnpm matching `package.json` (10.5.1).
Complete the [shared service setup](../docs/setup.md) and start the
[backend](../backend/README.md).

From `frontend/`, install dependencies and create the environment file on first
setup. Preserve an existing `.env.local` rather than replacing it:

```bash
pnpm install
cp .env.example .env.local
```

Configure these public values in `.env.local`:

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Agent Server URL; locally `http://localhost:2024` |
| `NEXT_PUBLIC_ASSISTANT_ID` | Default graph ID; normally `deep_agent` |
| `NEXT_PUBLIC_SUPABASE_URL` | Same Supabase project used by the backend |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key |
| `ALLOWED_DEV_ORIGINS` | Optional comma-separated development hostnames for tunnel access |

For local-only access, set `NEXT_PUBLIC_API_URL=http://localhost:2024`.
For access through a frontend tunnel, set
`NEXT_PUBLIC_API_URL=https://YOUR_TUNNEL_HOST/agent-api` instead. The frontend
forwards `/agent-api/*` to the backend on port 2024. See the
[ngrok setup](../docs/setup.md#optional-ngrok-access).

Browser configuration uses publishable values. Mistral/LangSmith API keys stay
in the backend; the Google client secret stays in Supabase provider settings.

## Run and use

```bash
pnpm dev
```

Open `http://localhost:3000`, select **Sign in with Google**, and start a chat.
Both frontend and backend must be running. Stop the frontend with Ctrl+C and
restart after changing environment configuration.

The UI shows your email and a sign-out button. Supabase manages session refresh;
chat and history requests carry the user's bearer token. Account changes clear
mounted chat state, and the backend enforces conversation ownership.

Select a graph through the URL:

| URL parameter | Agent |
| --- | --- |
| `?assistantId=deep_agent` | Deep Agents |
| `?assistantId=agent` | LangChain |

Start a new conversation when switching agents. Reopening an existing thread
restores its history for the signed-in owner. The API destination comes from
environment configuration, not a URL parameter.

## Remote access and customization

For ngrok, use the [remote access setup](../docs/setup.md#optional-ngrok-access).
Next.js forwards `/agent-api/*` to the local backend while retaining the user's
bearer token. There is no shared-key API proxy.

For UI development examples, see [frontend customization](../docs/frontend-customization.md).
The imported version is recorded in [upstream provenance](../docs/frontend-upstream.md).

## Checks

```bash
pnpm lint
pnpm build
```
