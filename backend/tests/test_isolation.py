"""Integration checks: ISOLATION_API_URL=http://localhost:2024 uv run pytest -q."""

import os
from uuid import uuid4

import httpx
import pytest

API_URL = os.getenv("ISOLATION_API_URL")
TOKEN_A = os.getenv("ISOLATION_TOKEN_A")
TOKEN_B = os.getenv("ISOLATION_TOKEN_B")
pytestmark = pytest.mark.skipif(
    not (API_URL and TOKEN_A and TOKEN_B),
    reason="Set ISOLATION_API_URL and two Supabase access tokens: ISOLATION_TOKEN_A/B",
)


@pytest.fixture
def clients():
    with (
        httpx.Client(
            base_url=API_URL,
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        ) as alice,
        httpx.Client(
            base_url=API_URL,
            headers={"Authorization": f"Bearer {TOKEN_B}"},
        ) as bob,
    ):
        yield alice, bob


def test_invalid_tokens():
    for headers in (
        {},
        {"Authorization": "Bearer invalid"},
        {"X-Api-Key": "alice-local-token"},
    ):
        response = httpx.post(f"{API_URL}/threads/search", headers=headers, json={})
        assert response.status_code == 401


def test_thread_isolation(clients):
    alice, bob = clients
    batch = str(uuid4())
    threads = []
    try:
        owners = []
        for client in (alice, bob):
            response = client.post(
                "/threads", json={"metadata": {"owner": "forged", "test": batch}}
            )
            assert response.status_code == 200, response.text
            thread = response.json()
            threads.append((client, thread["thread_id"]))
            assert thread["metadata"]["owner"] != "forged"
            owners.append(thread["metadata"]["owner"])

        assert owners[0] != owners[1]

        for (owner, thread_id), other in zip(threads, (bob, alice), strict=True):
            assert owner.get(f"/threads/{thread_id}").status_code == 200
            for method, path, body in (
                ("GET", "", None),
                ("GET", "/state", None),
                ("POST", "/history", {}),
                ("GET", "/runs", None),
                ("PATCH", "", {"metadata": {"owner": "bob"}}),
                ("POST", "/state", {"values": {"messages": []}}),
                (
                    "POST",
                    "/runs",
                    {"assistant_id": "deep_agent", "input": {"messages": []}},
                ),
                (
                    "POST",
                    "/runs/stream",
                    {"assistant_id": "deep_agent", "input": {"messages": []}},
                ),
                ("DELETE", "", None),
            ):
                response = other.request(
                    method, f"/threads/{thread_id}{path}", json=body
                )
                assert response.status_code in {403, 404}, (
                    method,
                    path,
                    response.status_code,
                    response.text,
                )
            # Denied writes/deletes must not have changed ownership.
            assert owner.get(f"/threads/{thread_id}").status_code == 200

            response = owner.post("/threads/search", json={"metadata": {"test": batch}})
            assert response.status_code == 200
            assert [t["thread_id"] for t in response.json()] == [thread_id]
    finally:
        for client, thread_id in threads:
            client.delete(f"/threads/{thread_id}")


def test_shared_graphs_are_read_only(clients):
    for client in clients:
        response = client.post("/assistants/search", json={})
        assert response.status_code == 200
        assert {a["graph_id"] for a in response.json()} >= {"agent", "deep_agent"}
        assert (
            client.post("/assistants", json={"graph_id": "deep_agent"}).status_code
            == 403
        )


def test_bearer_token():
    response = httpx.post(
        f"{API_URL}/threads/search",
        headers={"Authorization": f"Bearer {TOKEN_A}"},
        json={},
    )
    assert response.status_code == 200
