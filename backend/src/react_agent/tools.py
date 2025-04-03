import asyncio
import json
import logging
import os
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from arcadepy import Arcade
from arcadepy._exceptions import APIError, AuthenticationError, PermissionDeniedError
from arcadepy.types import ToolDefinition
from arcadepy.types.execute_tool_response import Output
from langchain_core.tools import StructuredTool
from langgraph.config import get_config
from langgraph.types import interrupt

from react_agent.defaults import get_tools
from react_agent.tool_utils import tool_definition_to_pydantic_model

# Set up logging
logger = logging.getLogger(__name__)

# Import the service methods from defaults


def get_arcade_client() -> Arcade:
    """Get an initialized Arcade client instance.

    Returns:
        An initialized Arcade client

    Raises:
        Exception: If required credentials are missing
    """
    try:
        # Note: The Arcade client looks for authentication credentials
        api_key = os.environ.get("ARCADE_API_KEY") or os.environ.get(
            "ARCADE_BEARER_TOKEN"
        )
        base_url = os.environ.get("ARCADE_BASE_URL", "https://api.arcade.dev")

        client = Arcade(
            api_key=api_key,
            base_url=base_url,
        )

        # Perform a health check to verify connectivity
        client.health.check()
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Arcade client: {str(e)}")
        raise


def _get_available_tools() -> Tuple[List[str], Dict[str, ToolDefinition]]:
    """Get available tools from the Arcade client with caching.

    Returns:
        A tuple of (tool_ids, available_tools_by_name)
    """
    client = get_arcade_client()
    try:
        response = client.tools.list(limit=1000)
        available_tools = response.items
        tool_definitions = {tool.name: tool for tool in available_tools}
        tool_names = get_tools()
        final_tools = []
        for t, definition in tool_definitions.items():
            if t in tool_names:
                final_tools.append(definition)
        return final_tools
    except Exception as e:
        logger.error(f"Failed to get available tools: {str(e)}")
        raise


def _handle_authorization_error(output: Output, user_id: str) -> None:
    """Handle authorization-related errors.

    Args:
        output: The output from the API response
        user_id: The ID of the user making the request
    """
    if output.authorization is None:
        logger.error(f"No authorization found in output: {output}")
        raise ValueError("No authorization found in output")

    auth = output.authorization
    logger.info(f"Authorization required for user {user_id}, initiating auth flow")
    return interrupt(
        [
            {
                "action_request": {
                    "action": "Auth",
                    "args": {"url": auth.url},
                },
                "config": {
                    "allow_ignore": False,
                    "allow_respond": False,
                    "allow_edit": False,
                    "allow_accept": True,
                },
                "description": None,
            }
        ]
    )


def _handle_auth_exception(exception: Exception, user_id: str, tool_name: str) -> None:
    """Handle authentication-related exceptions.

    Args:
        exception: The exception that was raised
        user_id: The ID of the user making the request
    """
    logger.info(f"Authentication error for user {user_id}, initiating auth flow")
    # Extract URL from exception if available or use a default auth URL
    auth_url = getattr(exception, "url", None)
    if not auth_url:
        client = get_arcade_client()
        auth_response = client.tools.authorize(tool_name=tool_name, user_id=user_id)
        logger.info(f"Authorization response: {auth_response}")
        if auth_response.url:
            auth_url = auth_response.url
        else:
            raise ValueError("No authorization URL found in response")

    return interrupt(
        [
            {
                "action_request": {
                    "action": "Auth",
                    "args": {"url": auth_url},
                },
                "config": {
                    "allow_ignore": False,
                    "allow_respond": False,
                    "allow_edit": False,
                    "allow_accept": True,
                },
                "description": None,
            }
        ]
    )


def create_tool_caller(tool_id: str) -> Callable[..., Any]:
    """Create a tool caller for the specified tool.

    Args:
        tool_id: The ID of the tool to call

    Returns:
        A callable function that will execute the tool with the given parameters
    """
    # We don't create a client here to avoid creating multiple clients
    # The client will be obtained when the tool is called

    def call_tool(**kwargs: Any) -> Any:
        """Call a tool with the given parameters."""
        client = get_arcade_client()
        config = get_config()
        user_id = config["configurable"].get("langgraph_auth_user_id")

        if not user_id:
            logger.error("Missing langgraph_auth_user_id in configuration")
            raise ValueError("Missing langgraph_auth_user_id in configuration")

        logger.debug(f"Calling tool {tool_id} for user {user_id} with args: {kwargs}")

        try:
            # Call the tool using the client's built-in method
            response = client.tools.execute(
                tool_name=tool_id, input=kwargs, user_id=user_id
            )

            # Check for successful response
            if not response.success:
                error_msg = response.output.error or "Unknown error occurred"
                logger.error(f"Tool call failed: {error_msg}")
                raise ValueError(f"Tool call to {tool_id} failed: {error_msg}")

            return response.output.value

        except (PermissionDeniedError, AuthenticationError) as e:
            # Handle auth errors without depending on response variable
            return _handle_auth_exception(e, user_id, tool_id)
        except Exception as e:
            # Handle unexpected errors
            logger.exception(f"Unexpected error calling tool {tool_id}: {str(e)}")
            raise

    return call_tool


def convert_output_to_json(output: Any) -> str:
    """Convert output to JSON string."""
    if isinstance(output, dict) or isinstance(output, list):
        return json.dumps(output)
    else:
        return str(output)


def get_langchain_tools(tool_types: Optional[List[str]] = None) -> List[StructuredTool]:
    """Get structured tools, optionally filtered by tool type.

    Args:
        tool_types: List of tool types to include (e.g., "x", "github")

    Returns:
        List of structured tools
    """
    tools = _get_available_tools()
    langchain_tools = []
    for tool in tools:
        try:
            langchain_tools.append(
                StructuredTool(
                    name=tool.name,
                    description=tool.description,
                    args_schema=tool_definition_to_pydantic_model(tool),
                    func=create_tool_caller("_".join((tool.toolkit.name, tool.name))),
                )
            )
        except Exception as e:
            logger.error(f"Failed to create tool for {tool.name}: {str(e)}")

    return langchain_tools

