from typing import Optional, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, create_react_agent

from react_agent.prompts import SYSTEM_PROMPT
from react_agent.tools import get_langchain_tools
from react_agent.utils import get_formatted_times, load_chat_model


class HumanInterruptConfig(TypedDict):
    """Settings for the human interrupt."""

    allow_ignore: bool
    allow_respond: bool
    allow_edit: bool
    allow_accept: bool


class ActionRequest(TypedDict):
    """Action request from the agent."""

    action: str
    args: dict


class HumanInterrupt(TypedDict):
    """Interrupt the agent with a human action request."""

    action_request: ActionRequest
    config: HumanInterruptConfig
    description: Optional[str]


async def make_graph(config: RunnableConfig) -> CompiledStateGraph:
    """Create a custom state graph for the Reasoning and Action agent."""
    # Initialize the model with tool binding. Change the model or add more tools here.
    model = load_chat_model("openai/o3-mini")

    # Format the system prompt. Customize this to change the agent's behavior.
    prompt = SYSTEM_PROMPT.format(current_times=get_formatted_times())

    # Get allowed tool types from config
    tool_types = config.get("configurable", {}).get("tools", [])

    # Get the tools filtered by allowed types
    allowed_tools = get_langchain_tools(tool_types)

    graph = create_react_agent(model, tools=allowed_tools, prompt=prompt, version="v2")
    graph.name = "ReAct Agent"  # This customizes the name in LangSmith
    return graph
