"""LangChain comparison agent, served as graph ID `agent`."""

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

_ = load_dotenv()

model = init_chat_model(
    os.getenv("CHAT_MODEL", "mistral-large-latest"),
    model_provider="mistralai",
    temperature=0,
)


def build_agent(*, checkpointer=None):
    """Let Agent Server manage persistence; standalone callers can supply it."""
    return create_agent(
        model=model,
        tools=[],
        system_prompt="You are a helpful assistant.",
        checkpointer=checkpointer,
        middleware=[
            SummarizationMiddleware(
                model=model,
                trigger=("tokens", 8000),
                keep=("messages", 10),
            ),
        ],
    )


agent = build_agent()


def main() -> None:
    agent = build_agent(checkpointer=InMemorySaver())
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
