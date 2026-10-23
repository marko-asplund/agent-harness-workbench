"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { Button } from "@/components/ui/button";
import { getSupabase } from "@/lib/supabase";
import { AuthContext } from "@/lib/auth-context";

function clearSelectedThread() {
  const url = new URL(window.location.href);
  url.searchParams.delete("threadId");
  window.history.replaceState(null, "", url);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const previousUser = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    try {
      const supabase = getSupabase();
      // Capture OAuth errors before the SDK cleans the callback URL.
      const params = new URLSearchParams(window.location.search);
      const oauthError = params.get("error_description") || params.get("error");
      const updateSession = (next: Session | null) => {
        if (!active) return;
        const userId = next?.user.id ?? null;
        if (previousUser.current && previousUser.current !== userId) {
          clearSelectedThread();
        }
        previousUser.current = userId;
        setSession(next);
        setLoading(false);
      };
      const { data } = supabase.auth.onAuthStateChange((_event, next) => {
        updateSession(next);
      });
      // getSession also completes the PKCE callback and refreshes expired sessions.
      void supabase.auth
        .getSession()
        .then(({ data, error }) => {
          if (!active) return;
          updateSession(data.session);
          if (error || oauthError) setError(error?.message || oauthError || "");
        })
        .catch(() => {
          if (!active) return;
          updateSession(null);
          setError("Could not restore your session. Please sign in again.");
        });
      return () => {
        active = false;
        data.subscription.unsubscribe();
      };
    } catch (cause) {
      // Configuration errors are shown instead of mounting an anonymous chat.
      queueMicrotask(() => {
        if (!active) return;
        setError(
          cause instanceof Error ? cause.message : "Authentication failed.",
        );
        setLoading(false);
      });
      return () => {
        active = false;
      };
    }
  }, []);

  if (loading) return <main className="p-6">Loading sign-in…</main>;

  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="flex w-full max-w-sm flex-col gap-4 rounded-lg border p-6">
          <h1 className="text-xl font-semibold">Agent Chat</h1>
          <p>Sign in to access your conversations.</p>
          {error && <p role="alert">{error}</p>}
          <Button
            disabled={pending}
            onClick={async () => {
              setPending(true);
              setError("");
              try {
                clearSelectedThread();
                const { error } = await getSupabase().auth.signInWithOAuth({
                  provider: "google",
                  options: {
                    redirectTo: `${window.location.origin}/`,
                    queryParams: { prompt: "select_account" },
                  },
                });
                if (error) setError(error.message);
              } catch (cause) {
                setError(
                  cause instanceof Error ? cause.message : "Sign-in failed.",
                );
              } finally {
                setPending(false);
              }
            }}
          >
            {pending ? "Redirecting…" : "Sign in with Google"}
          </Button>
        </div>
      </main>
    );
  }

  return (
    <AuthContext.Provider value={{ accessToken: session.access_token }}>
      <div className="bg-background fixed top-3 right-4 z-50 flex items-center gap-2 rounded-md border p-2">
        <span className="max-w-48 truncate text-sm">{session.user.email}</span>
        <Button
          variant="outline"
          disabled={pending}
          onClick={async () => {
            setPending(true);
            try {
              const { error } = await getSupabase().auth.signOut({
                scope: "local",
              });
              if (error) {
                setError(error.message);
                return;
              }
              // Also reset URL-driven state and all mounted provider caches.
              window.location.replace("/");
            } catch {
              setError("Sign-out failed. Please try again.");
            } finally {
              setPending(false);
            }
          }}
        >
          Sign out
        </Button>
        {error && (
          <p
            role="alert"
            className="text-sm"
          >
            {error}
          </p>
        )}
      </div>
      <div key={session.user.id}>{children}</div>
    </AuthContext.Provider>
  );
}
