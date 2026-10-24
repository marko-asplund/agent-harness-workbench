# Service setup

This guide covers the external services and configuration shared by the backend
and frontend. Component installation and startup commands live in the
[backend README](../backend/README.md) and [frontend README](../frontend/README.md).

## What is required?

| Service | Role | Needed for |
| --- | --- | --- |
| Mistral AI | Model completions | Both agents |
| Supabase Auth | Application users and sessions | Authenticated browser chat |
| Google OAuth | Sign-in identity provider | The current frontend login flow |
| LangSmith | Execution and model-call tracing | Optional observability |
| ngrok | Public HTTPS access to the local frontend | Optional remote testing |

Configure Mistral and Google/Supabase first, then run both components. Add tracing
or a public tunnel when needed. Use placeholders in committed examples; keep local
environment files out of Git.

## Mistral AI

1. Create an account and API key in the [Mistral console](https://console.mistral.ai/).
2. Set `MISTRAL_API_KEY` in `backend/.env`.
3. Set `CHAT_MODEL` to a model available to that account. The example configuration
   uses `mistral-small-latest`; both agents use this setting.

The key stays on the backend. Restart the backend after changing it or the model.
Model availability and usage limits are managed in the Mistral account.

## Supabase and Google sign-in

1. Create a [Supabase project](https://supabase.com/dashboard). Copy its project
   URL and publishable key to the backend and frontend variables below.
2. Create/select a [Google Cloud project](https://console.cloud.google.com/).
   Configure Google Auth Platform branding, an External audience for testers
   outside your organization, and basic OpenID/email/profile scopes.
3. Create a Web application OAuth client. Add the frontend origin to its
   authorized JavaScript origins. Add the exact callback URL displayed in
   Supabase's Google provider settings to Google's authorized redirect URIs.
4. Enable Google in Supabase Auth, entering that Google client's ID and secret.
5. Set Supabase's Site URL to the frontend origin and allow the frontend's return
   URL. Permit sign-up for first-time testers and configure the intended sign-in
   methods and audience.

| Value | Backend `.env` | Frontend `.env.local` |
| --- | --- | --- |
| Supabase project URL | `SUPABASE_URL` | `NEXT_PUBLIC_SUPABASE_URL` |
| Supabase publishable key | `SUPABASE_PUBLISHABLE_KEY` | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` |

Both components must use the same Supabase project. A secret/service-role key is
not needed. The Google client secret is configured in Supabase, not in these files.

There are two different redirects:

| Handoff | Example | Configured in |
| --- | --- | --- |
| Google → Supabase | `https://YOUR_PROJECT.supabase.co/auth/v1/callback` | Google OAuth client |
| Supabase → frontend | `http://localhost:3000/` | Supabase Auth redirect allowlist |

Keep the local frontend origin and return URL when adding a public testing URL.
Initiate and complete sign-in on the same frontend origin so the browser retains
the PKCE verifier. Authentication grants access to the app; backend authorization
separately limits each user to their own threads.

See [Google sign-in details](google-auth.md) for dashboard steps, callback locations,
testing-mode considerations, and troubleshooting.

## Optional ngrok access

Use this when remote testers need to reach the app running on your machine.

1. Install/sign in to [ngrok](https://ngrok.com/docs/start) and configure its
   account token following the dashboard instructions.
2. With both app components running, expose the frontend:

   ```bash
   ngrok http 3000
   ```

3. Set these frontend values using the assigned public hostname:

   ```dotenv
   NEXT_PUBLIC_API_URL=https://YOUR_TUNNEL_HOST/agent-api
   ALLOWED_DEV_ORIGINS=YOUR_TUNNEL_HOST
   ```

4. In Supabase, add `https://YOUR_TUNNEL_HOST/` to allowed redirect URLs. Use the
   public origin as Site URL when sharing the app remotely. In Google, add
   `https://YOUR_TUNNEL_HOST` to authorized JavaScript origins. Google's redirect
   URI remains the Supabase callback URL.
5. Restart the frontend, then open the public URL and sign in there. If the tunnel
   hostname changes, update these settings. Leave the tunnel running while testing.

The tunnel reaches port 3000 only. Next.js forwards `/agent-api/*` to
`http://127.0.0.1:2024/*`, including the user's bearer token and streamed responses.
Remote browsers must not use `localhost:2024` as the API URL: that would refer to
the tester's own computer. ngrok may show a one-time visit confirmation page.

## Optional LangSmith tracing

1. Create a [LangSmith account](https://smith.langchain.com), select the intended
   workspace, and create an API key in Settings.
2. Configure the backend:

   ```dotenv
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=YOUR_LANGSMITH_KEY
   LANGSMITH_PROJECT=agent-harness-workbench-dev
   ```

3. If the workspace uses a non-default region, set `LANGSMITH_ENDPOINT` to that
   region's API endpoint as described in the
   [tracing quickstart](https://docs.langchain.com/langsmith/observability-quickstart).
4. Restart the backend and send a chat message. The first trace creates the named
   tracing project if it does not exist and the API key has the required permission.
   In newer agent-based workspaces, LangSmith represents this as an agent with
   tracing environments; use the setup values shown there when selecting one.
5. Open the tracing destination in LangSmith and expand model calls to inspect
   inputs, outputs, timing, and available usage metadata.

Tracing records subsequent activity and sends recorded content to LangSmith.
It is optional, separate from chat authentication, and not the planned local
research archive. Set `LANGSMITH_TRACING=false` to disable it.
See [project selection](https://docs.langchain.com/langsmith/log-traces-to-project).

## Verify the whole setup

- Sign in and send a message. Confirm a response streams back.
- Reload or sign out and back in; confirm the same account's history is available.
- Use a second account in a private window and confirm separate histories, including
  denial when opening another user's thread URL.
- If tracing is enabled, confirm a new trace appears in the selected LangSmith
  destination.

Development history lives in Agent Server's local storage. Configure durable
production storage separately before relying on it for long-term retention.
