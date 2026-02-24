"""
Tool Registry System - Extensible tool management for the agent orchestrator.

This module provides a decorator-based tool registration system that allows
easy addition of new tools without modifying core orchestration logic.

Usage:
    @register_tool(
        name="my_tool",
        description="Description for LLM",
        parameters={"param1": "string", "param2": "integer"}
    )
    async def my_tool(param1: str, param2: int, user_id: str = None):
        # Implementation
        return ToolResult(data=result, summary="Brief summary")
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from app.core.logging_config import get_logger
import inspect

logger = get_logger("tools")

# Global tool registry
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


@dataclass
class ToolResult:
    """Standardized result from tool execution."""
    data: Any
    summary: str
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "summary": self.summary,
            "success": self.success,
            "error": self.error
        }


@dataclass
class ToolDefinition:
    """Definition of a registered tool."""
    name: str
    description: str
    parameters: Dict[str, str]
    handler: Callable
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, str]
):
    """
    Decorator to register a tool in the global registry.
    
    Args:
        name: Unique tool name
        description: Description for LLM to understand when to use this tool
        parameters: Dict mapping parameter names to their types
    
    Example:
        @register_tool(
            name="search_documents",
            description="Search uploaded documents using semantic similarity",
            parameters={"query": "string", "limit": "integer"}
        )
        async def search_documents(query: str, limit: int = 5, user_id: str = None):
            ...
    """
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": func,
            "is_async": inspect.iscoroutinefunction(func)
        }
        logger.info(f"Registered tool: {name}")
        return func
    return decorator


def get_tool(name: str) -> Optional[ToolDefinition]:
    """Get a tool definition by name."""
    tool_data = TOOL_REGISTRY.get(name)
    if tool_data:
        return ToolDefinition(
            name=tool_data["name"],
            description=tool_data["description"],
            parameters=tool_data["parameters"],
            handler=tool_data["handler"]
        )
    return None


def list_tools() -> List[Dict[str, Any]]:
    """List all registered tools with their descriptions."""
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"]
        }
        for tool in TOOL_REGISTRY.values()
    ]


def get_tools_for_llm() -> str:
    """
    Get a formatted string of available tools for LLM context.
    This helps the intent detector understand what tools are available.
    """
    tools_desc = []
    for tool in TOOL_REGISTRY.values():
        params_str = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
        tools_desc.append(f"- {tool['name']}({params_str}): {tool['description']}")
    return "\n".join(tools_desc)


async def execute_tool(
    name: str,
    params: Dict[str, Any],
    user_id: str
) -> ToolResult:
    """
    Execute a registered tool by name.
    
    Args:
        name: Tool name to execute
        params: Parameters to pass to the tool
        user_id: Current user ID for data isolation
    
    Returns:
        ToolResult with data and summary
    """
    tool_data = TOOL_REGISTRY.get(name)
    
    if not tool_data:
        logger.error(f"Tool not found: {name}")
        return ToolResult(
            data=None,
            summary=f"Tool '{name}' not found",
            success=False,
            error=f"Unknown tool: {name}"
        )
    
    try:
        handler = tool_data["handler"]
        # Always inject user_id
        params["user_id"] = user_id
        
        logger.info(f"Executing tool: {name} with params: {list(params.keys())}")
        
        if tool_data["is_async"]:
            result = await handler(**params)
        else:
            result = handler(**params)
        
        # If handler returns ToolResult, use it directly
        if isinstance(result, ToolResult):
            return result
        
        # Otherwise wrap in ToolResult
        return ToolResult(
            data=result,
            summary=f"Tool '{name}' executed successfully"
        )
        
    except Exception as e:
        logger.error(f"Tool execution error ({name}): {e}")
        return ToolResult(
            data=None,
            summary=f"Error executing '{name}': {str(e)}",
            success=False,
            error=str(e)
        )


# Import tool modules to register them
# These imports trigger the @register_tool decorators
def load_tools():
    """Load all tool modules to register them."""
    from app.services.tools import document_tools
    from app.services.tools import memory_tools
    logger.info(f"Loaded {len(TOOL_REGISTRY)} tools")
