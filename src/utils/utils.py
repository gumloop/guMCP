from typing import Any, TypedDict


class ToolResponse(TypedDict):
    success: bool
    data: Any
    error: Any
