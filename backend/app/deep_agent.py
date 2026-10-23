"""Deep Agents comparison: run with `uv run python -m app.deep_agent`."""

import os

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain.agents.middleware import TodoListMiddleware
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

model = init_chat_model(
    os.getenv("CHAT_MODEL", "mistral-large-latest"),
    model_provider="mistralai",
    temperature=0,
)


def build_agent(*, checkpointer=None):
    """Let Agent Server manage persistence; standalone callers can supply it."""
    # Deep Agents supplies summarization and context offloading automatically.
    # Its default virtual filesystem stores working files in thread state.
    # Planning is opt-in; no custom tools, skills, or subagents are configured.
    return create_deep_agent(
        model=model,
        system_prompt="You are a helpful assistant.",
        checkpointer=checkpointer,
        middleware=[TodoListMiddleware()],
    )


agent = build_agent()


def main() -> None:
    """Run the same conversation-memory demo as app.agent."""
    agent = build_agent(checkpointer=InMemorySaver())
    # Reuse a thread ID to continue a conversation. Memory is lost on restart.
    config = {"configurable": {"thread_id": "conversation-1"}}

    agent.invoke(
        {"messages": [{"role": "user", "content": "My name is Marko."}]},
        config=config,
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's my name?"}]},
        config=config,
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
