from typing import Annotated, Any, Callable, Union

from arcadepy import NOT_GIVEN, Arcade, AsyncArcade
from arcadepy.types import ExecuteToolResponse, ToolDefinition
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from pydantic import BaseModel, Field, create_model

# Check if LangGraph is enabled
LANGGRAPH_ENABLED = True
try:
    from langgraph.errors import NodeInterrupt
except ImportError:
    LANGGRAPH_ENABLED = False

# Mapping of Arcade value types to Python types
TYPE_MAPPING = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "json": dict,
}


def get_python_type(val_type: str) -> Any:
    """Map Arcade value types to Python types.

    Args:
        val_type: The value type as a string.

    Returns:
        Corresponding Python type.
    """
    _type = TYPE_MAPPING.get(val_type)
    if _type is None:
        raise ValueError(f"Invalid value type: {val_type}")
    return _type


def tool_definition_to_pydantic_model(tool_def: ToolDefinition) -> type[BaseModel]:
    """Convert a ToolDefinition's inputs into a Pydantic BaseModel.

    Args:
        tool_def: The ToolDefinition object to convert.

    Returns:
        A Pydantic BaseModel class representing the tool's input schema.
    """
    try:
        fields: dict[str, Any] = {}
        for param in tool_def.input.parameters or []:
            # check if the paramter has the Inferrable annotation set to False
            if param.inferrable is False:
                print(f"Parameter {param.name} has Inferrable set to False")
            else:
                param_type = get_python_type(param.value_schema.val_type)
                if param_type == list and param.value_schema.inner_val_type:  # noqa: E721
                    inner_type: type[Any] = get_python_type(
                        param.value_schema.inner_val_type
                    )
                    param_type = list[inner_type]  # type: ignore[valid-type]
                param_description = param.description or "No description provided."
                default = ... if param.required else None
                fields[param.name] = (
                    param_type,
                    Field(default=default, description=param_description),
                )
        return create_model(f"{tool_def.name}Args", **fields)
    except ValueError as e:
        raise ValueError(
            f"Error converting {tool_def.name} parameters into pydantic model for langchain: {e}"
        )


def process_tool_execution_response(
    execute_response: ExecuteToolResponse, tool_name: str, langgraph: bool
) -> Any:
    """Process the response from tool execution and handle errors appropriately.

    Args:
        execute_response: The response from tool execution
        tool_name: The name of the tool that was executed
        langgraph: Whether LangGraph-specific behavior is enabled

    Returns:
        The output value on success, or error details on failure
    """
    if execute_response.success and execute_response.output is not None:
        return execute_response.output.value

    # Extract detailed error information
    error_details = {
        "error": "Unknown error occurred",
        "tool": tool_name,
    }

    if (
        execute_response.output is not None
        and execute_response.output.error is not None
    ):
        error = execute_response.output.error
        error_message = (
            str(error.message) if hasattr(error, "message") else "Unknown error"
        )
        error_details["error"] = error_message

        # Add all non-None optional error fields to the details
        if (
            hasattr(error, "additional_prompt_content")
            and error.additional_prompt_content is not None
        ):
            error_details["additional_prompt_content"] = error.additional_prompt_content
        if hasattr(error, "can_retry") and error.can_retry is not None:
            error_details["can_retry"] = str(error.can_retry)
        if hasattr(error, "developer_message") and error.developer_message is not None:
            error_details["developer_message"] = str(error.developer_message)
        if hasattr(error, "retry_after_ms") and error.retry_after_ms is not None:
            error_details["retry_after_ms"] = str(error.retry_after_ms)

    if langgraph:
        raise NodeInterrupt(error_details)
    return error_details


def create_tool_function(
    client: Arcade,
    tool_name: str,
    tool_def: ToolDefinition,
    args_schema: type[BaseModel],
    langgraph: bool = False,
    next_step: str = None,
) -> Callable:
    """Create a callable function to execute an Arcade tool.

    Args:
        client: The Arcade client instance.
        tool_name: The name of the tool to wrap.
        tool_def: The ToolDefinition of the tool to wrap.
        args_schema: The Pydantic model representing the tool's arguments.
        langgraph: Whether to enable LangGraph-specific behavior.
        next_step: The next step to transition to after this tool completes.

    Returns:
        A callable function that executes the tool.
    """
    if langgraph and not LANGGRAPH_ENABLED:
        raise ImportError(
            "LangGraph is not installed. Please install it to use this feature."
        )

    requires_authorization = (
        tool_def.requirements is not None
        and tool_def.requirements.authorization is not None
    )
    non_inferrable_params = [
        param for param in tool_def.input.parameters if param.inferrable is False
    ]

    def tool_function(config: RunnableConfig, **kwargs: Any) -> Any:
        """Execute the Arcade tool with the given parameters.

        Args:
            config: RunnableConfig containing execution context.
            **kwargs: Tool input arguments.

        Returns:
            The output from the tool execution or a Command object with state updates.
        """
        # Extract tool_call_id directly from kwargs
        tool_call_id = kwargs.pop("tool_call_id", None)

        user_id = config.get("configurable", {}).get("user_id") if config else None

        # check for non-infferable params in config
        non_infer_params = {}
        for param in non_inferrable_params:
            non_infer_params[param.name] = kwargs.get(param.name)
            if non_infer_params[param.name] is None:
                raise ValueError(f"Missing required parameter: {param.name}")

        if requires_authorization:
            if user_id is None:
                error_message = f"user_id is required to run {tool_name}"
                if langgraph:
                    raise NodeInterrupt(error_message)
                return {"error": error_message}

            # Authorize the user for the tool
            auth_response = client.tools.authorize(tool_name=tool_name, user_id=user_id)
            if auth_response.status != "completed":
                auth_message = (
                    f"Please use the following link to authorize: {auth_response.url}"
                )
                if langgraph:
                    raise NodeInterrupt(auth_message)
                return {"error": auth_message}

        # Execute the tool with provided inputs
        print(f"Executing tool with inputs: {kwargs}, {non_infer_params}")
        execute_response = client.tools.execute(
            tool_name=tool_name,
            input={**kwargs, **non_infer_params},
            user_id=user_id if user_id is not None else NOT_GIVEN,
        )

        result = process_tool_execution_response(execute_response, tool_name, langgraph)

        # If we're in LangGraph mode, return a Command object that updates the state
        if langgraph:
            # Extract rm_loan_id if available in the result
            rm_loan_id = None
            if isinstance(result, dict) and "rmLoanId" in result:
                rm_loan_id = result["rmLoanId"]

            # Return a Command with the state updates and the original result
            update = {
                "dialog_state": "mortgage_assistant",
                "current_step": next_step,
            }

            if rm_loan_id:
                update["current_rm_loan_id"] = rm_loan_id

            return Command(
                update=update,
                tool_call_id=tool_call_id,
            )

        return result

    return tool_function


def wrap_arcade_tool(
    client: Union[Arcade, AsyncArcade],
    tool_name: str,
    tool_def: ToolDefinition,
) -> StructuredTool:
    """Wrap an Arcade `ToolDefinition` as a LangChain `StructuredTool`.

    Args:
        client: The Arcade client instance.
        tool_name: The name of the tool to wrap.
        tool_def: The ToolDefinition object to wrap.
        langgraph: Whether to enable LangGraph-specific behavior.

    Returns:
        A StructuredTool instance representing the Arcade tool.
    """
    description = tool_def.description or "No description provided."

    # Create a Pydantic model for the tool's input arguments
    args_schema = tool_definition_to_pydantic_model(tool_def)

    action_func = create_tool_function(
        client=client,
        tool_name=tool_name,
        tool_def=tool_def,
        args_schema=args_schema,
    )

    return StructuredTool.from_function(
        func=action_func,
        name=tool_name,
        description=description,
        args_schema=args_schema,
        inject_kwargs={"user_id"},
    )
