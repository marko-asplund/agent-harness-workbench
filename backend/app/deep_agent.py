"""Deep Agents comparison: run with `uv run python -m app.deep_agent`."""

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain.agents.middleware import TodoListMiddleware
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

model = init_chat_model(
    "mistral-large-latest",
    model_provider="mistralai",
    temperature=0,
)

# Deep Agents supplies summarization and context offloading automatically.
# Its default virtual filesystem stores working files in thread state.
# Planning is opt-in; no custom tools, skills, or subagents are configured.
agent = create_deep_agent(
    model=model,
    system_prompt="You are a helpful assistant.",
    checkpointer=InMemorySaver(),
    middleware=[TodoListMiddleware()],
)


def main() -> None:
    """Run the same conversation-memory demo as app.agent."""
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
