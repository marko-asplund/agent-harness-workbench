# Google sign-in with Supabase

For a high-level overview covering all services, start with [service setup](setup.md).
This page provides the detailed Google and Supabase configuration steps.

The frontend and Agent Server run locally. A hosted Supabase project handles
accounts and sessions; Google authenticates users. No chat messages are stored
in Supabase by this integration. Chat state stays in Agent Server.

## 1. Create a Supabase project

1. Open [Supabase](https://supabase.com/dashboard) and create a project.
2. Copy its project URL and **publishable key** from the project's Connect/API
   settings. Older projects can use the public `anon` key in the same variables.
   Do not use a secret key or `service_role` key.
3. In **Authentication → URL Configuration**, set the Site URL to
   `http://localhost:3000` and add `http://localhost:3000/` to Redirect URLs.
4. In **Authentication → Sign In / Providers → Google**, find the Supabase
   callback URL. It normally looks like
   `https://YOUR_PROJECT.supabase.co/auth/v1/callback`. Copy the exact value
   supplied by the dashboard for the next step.

## 2. Configure Google

1. Create/select a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Open **Google Auth Platform**. Configure Branding (app name and contact
   details), Audience, and Data Access. Choose an External audience if testers
   use personal Google accounts or accounts outside your organization.
3. Use only basic identity scopes: `openid`, email, and profile. No Gmail,
   Drive, or Calendar access is required.
4. Under **Clients**, create an OAuth client of type **Web application**.
5. Set an authorized JavaScript origin of `http://localhost:3000`.
6. Set its authorized redirect URI to the exact **Supabase callback URL** from
   step 1. This is not the frontend's localhost URL.
7. Save the Google client ID and client secret in Supabase's Google provider
   settings and enable that provider. The secret does not go in this repository.

During testing, add your testers under Audience → Test users if your Google app
configuration requires it. Google documents an exception to the test-user
allowlist for apps requesting only basic identity scopes. Workspace admin
policies may still restrict organization accounts. Google test-user settings
are not an application authorization allowlist for this app.

Supabase must permit new user sign-ups for first-time testers. If Google should
be the only sign-in method, disable unused email/anonymous providers in Supabase.
The backend accepts authenticated users of the configured Supabase project.

## 3. Configure the application

Keep existing Mistral settings and add these to `backend/.env`:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

Add the same project values to `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=deep_agent
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

Remove obsolete `NEXT_PUBLIC_LOCAL_AUTH`, `NEXT_PUBLIC_AUTH_SCHEME`, and
`LOCAL_ALICE_TOKEN` / `LOCAL_BOB_TOKEN` settings if present; they are no longer
used. Environment files remain ignored by Git. No Supabase service-role key,
Google API access token, or LangSmith API key is needed to authenticate chat.

## 4. Restart and test

Stop existing servers with Ctrl+C. In two terminals:

```bash
cd backend
uv sync
uv run langgraph dev --no-browser
```

```bash
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000` and click **Sign in with Google**. Complete the
Google consent flow in the same browser that initiated sign-in (PKCE stores
its verifier there). The app returns to `/` and displays your email.

Create a chat, then sign in with a second Google account in a private window.
Verify that each account has separate history. Copying the first account's
`?threadId=...` URL into the second window must be rejected by the backend.
Sign out and back in to verify history restoration. Old local-token demo
histories are not transferred to the new Supabase user IDs.

There are two redirects to keep distinct:

| Redirect | Configure in |
| --- | --- |
| Google → `https://YOUR_PROJECT.supabase.co/auth/v1/callback` | Google OAuth client |
| Supabase → `http://localhost:3000/` | Supabase redirect allowlist |

If the frontend uses a different port, update its origin in Google and both the
Site URL and redirect allowlist in Supabase. Use `localhost` consistently rather
than mixing it with `127.0.0.1` for the frontend.

## Troubleshooting

For an existing frontend tunnel, set `NEXT_PUBLIC_API_URL` to
`https://YOUR_TUNNEL_HOST/agent-api` and `ALLOWED_DEV_ORIGINS` to
`YOUR_TUNNEL_HOST` in `frontend/.env.local`. Next.js forwards `/agent-api/*` to
`http://127.0.0.1:2024/*`, preserving the user's bearer token. The backend stays
local. Restart the frontend after changing these settings.

Add `https://YOUR_TUNNEL_HOST/` to Supabase's redirect allowlist (and use the
public origin as Site URL when sharing remotely). Add the public origin to
Google's authorized JavaScript origins. Google's redirect URI remains the
Supabase callback URL. Always initiate and complete login on the same frontend
origin so the PKCE verifier remains available.

- **`redirect_uri_mismatch` at Google:** check Google's authorized redirect URI
  against the exact Supabase callback URL.
- **Sign-in returns to the wrong site:** check Supabase URL Configuration.
- **Missing configuration screen / backend 503:** fill in the project URL and
  publishable key in both env files and restart the servers.
- **Backend 401 after Google login:** both sides must use the same Supabase
  project. Requests use the Supabase session JWT, not Google's provider token.
- **Denied access to an old chat:** chats belong to a stable Supabase user ID;
  other accounts and the old Alice/Bob tokens cannot access them.

The browser SDK manages session persistence, PKCE code exchange, and token
refresh. React receives refreshed tokens for future SDK requests. The backend
verifies each incoming bearer token with Supabase's `/auth/v1/user` endpoint;
it does not trust user IDs or email addresses sent by the browser. This adds an
auth-provider round trip to protected API requests. Missing configuration and
provider outages fail closed.

## References

- [Supabase Google sign-in](https://supabase.com/docs/guides/auth/social-sign-in/auth-google)
- [Supabase PKCE flow](https://supabase.com/docs/guides/auth/sessions/pkce-flow)
- [Google OAuth app states and testing](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview)
- [LangGraph: connect an authentication provider](https://docs.langchain.com/langsmith/add-auth-server)
