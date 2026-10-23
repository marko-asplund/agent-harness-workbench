"""Verify Supabase access tokens and keep each user's conversations private."""

import os

import httpx
from langgraph_sdk import Auth

auth = Auth()


@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    """Use Supabase's user endpoint to validate, never merely decode, the JWT."""
    authorization = headers.get(b"authorization", b"").decode("latin-1")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise Auth.exceptions.HTTPException(status_code=401, detail="Sign in required")

    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not key:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="Supabase authentication is not configured"
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{url}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": key},
            )
    except httpx.RequestError as exc:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="Authentication provider is unavailable"
        ) from exc

    if response.status_code in {401, 403}:
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Invalid or expired session"
        )
    if response.status_code != 200:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="Authentication provider is unavailable"
        )
    try:
        user = response.json()
    except ValueError as exc:
        raise Auth.exceptions.HTTPException(
            status_code=503, detail="Invalid authentication provider response"
        ) from exc
    if (
        not isinstance(user, dict)
        or not isinstance(user.get("id"), str)
        or not user["id"]
    ):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid session")
    return {
        "identity": user["id"],
        "display_name": user.get("email") or user["id"],
    }


@auth.on
async def deny_other_resources(ctx: Auth.types.AuthContext, value: dict):
    """No shared stores, crons, or other mutable resources are exposed."""
    return False


@auth.on.threads
async def private_threads(ctx: Auth.types.AuthContext, value: dict):
    """Enforce ownership on history, state, mutations, and runs as well as lists."""
    # Override client-supplied ownership, including on updates and create_run.
    value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return {"owner": ctx.user.identity}


@auth.on.assistants
async def shared_graphs(ctx: Auth.types.AuthContext, value: dict):
    """Both users can discover/use the installed graphs, but cannot change them."""
    return ctx.action in {"read", "search"}
