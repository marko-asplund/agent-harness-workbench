from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

_ = load_dotenv()

model = init_chat_model(
    "mistral-large-latest",
    model_provider="mistralai",
    temperature=0,
)

agent = create_agent(
    model=model,
    tools=[],
    system_prompt="You are a helpful assistant.",
    checkpointer=InMemorySaver(),
    middleware=[
        SummarizationMiddleware(
            model=model,
            trigger=("tokens", 8000),
            keep=("messages", 10),
        ),
    ],
)

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
