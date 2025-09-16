import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

import httpx
from mcp.server import Server
from mcp.types import (
    InitializeResult,
    Implementation,
    Tool,
    CallToolResult,
)

# Configuration (simplified: no auth token or custom timeout)
DEFAULT_BASE_URL = "http://localhost:8000/api"
BASE_URL = os.environ.get("AT_BACKEND_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

# Simple HTTP client wrapper
class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        # Use default httpx timeout settings
        self._client = httpx.AsyncClient()

    async def close(self):
        await self._client.aclose()

    def _headers(self) -> Dict[str, str]:
        return {"Accept": "application/json"}

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        resp = await self._client.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        if resp.text.strip():
            return resp.json()
        return None

backend = BackendClient(BASE_URL)
server = Server("automated-trader-mcp")

# Capture MCP library version (if available) for debug
try:  # pragma: no cover
    import importlib.metadata
    MCP_VERSION = importlib.metadata.version('mcp')
except Exception:  # pragma: no cover
    try:
        import mcp  # type: ignore
        MCP_VERSION = getattr(mcp, "__version__", "unknown")
    except Exception:  # pragma: no cover
        MCP_VERSION = "unknown"

def _log(msg: str):  # stderr only to avoid protocol stdout noise
    if os.getenv("AT_MCP_DEBUG"):
        print(f"[MCP-SERVER] {msg}", file=sys.stderr)

# Tool definitions metadata
TOOLS: Dict[str, Dict[str, Any]] = {
    "echo": {
        "description": "Echo back provided arguments for debugging.",
        "params": {
            "message": {"type": "string", "required": False},
        },
        "path": None,  # special handling
    },
    "health_check": {
        "description": "Check backend health status.",
        "params": {},
        "path": "/health",
    },
    "get_portfolio_summary": {
        "description": "Retrieve overall portfolio summary including allocations and top holdings.",
        "params": {},
        "path": "/holdings/summary",
    },
    "list_positions": {
        "description": "List positions with optional filters (account, ticker, limit, offset).",
        "params": {
            "account": {"type": "string", "required": False},
            "ticker": {"type": "string", "required": False},
            "limit": {"type": "integer", "required": False},
            "offset": {"type": "integer", "required": False},
        },
        "path": "/holdings/positions",
    },
    "list_accounts": {
        "description": "List accounts with position counts.",
        "params": {},
        "path": "/holdings/accounts",
    },
    "get_instruments": {
        "description": "List instruments with optional filters (page, size, ticker, sector, instrument_type).",
        "params": {
            "page": {"type": "integer", "required": False},
            "size": {"type": "integer", "required": False},
            "ticker": {"type": "string", "required": False},
            "sector": {"type": "string", "required": False},
            "instrument_type": {"type": "string", "required": False},
        },
        "path": "/instruments",
    },
    "get_holding_detail": {
        "description": "Get detailed holding info across accounts for a ticker.",
        "params": {"ticker": {"type": "string", "required": True}},
        "path": "/holdings/{ticker}",
    },
}

@server.list_tools()
async def list_tools() -> list[Tool]:
    tool_list: list[Tool] = []
    for name, meta in TOOLS.items():
        # Build schema; allow permissive mode to debug client issues
        permissive = os.getenv("AT_MCP_PERMISSIVE") == "1"
        if permissive:
            schema = {"type": "object"}
        else:
            schema = {
                "type": "object",
                "properties": {k: {"type": v["type"]} for k, v in meta.get("params", {}).items()},
                "required": [k for k, v in meta.get("params", {}).items() if v.get("required")],
                "additionalProperties": False,
            }
        tool_list.append(
            Tool(
                name=name,
                description=meta["description"],
                inputSchema=schema,
            )
        )
    return tool_list

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any] | None) -> CallToolResult:
    arguments = arguments or {}
    if name not in TOOLS:
        return CallToolResult(content=[{"type": "text", "text": f"Unknown tool: {name}"}])

    meta = TOOLS[name]
    path_template = meta["path"]

    # Echo tool (debug only)
    if name == "echo":
        pretty = json.dumps({"received": arguments}, indent=2, sort_keys=True)
        return CallToolResult(content=[{"type": "text", "text": pretty}])

    # Path substitution for ticker detail
    if path_template and "{ticker}" in path_template:
        ticker = arguments.get("ticker")
        if not ticker:
            return CallToolResult(content=[{"type": "text", "text": "Missing required parameter: ticker"}])
        path = path_template.replace("{ticker}", str(ticker).upper())
    elif path_template:
        path = path_template
    else:
        path = None  # Should not happen except for echo

    # Build query params excluding unknown keys
    raw_params = {k: v for k, v in arguments.items() if k in meta.get("params", {}) and v is not None}
    # Normalize numeric strings to integers where schema expects integer
    norm_params: Dict[str, Any] = {}
    for k, v in raw_params.items():
        spec = meta.get("params", {}).get(k)
        if spec and spec.get("type") == "integer" and isinstance(v, str) and v.isdigit():
            try:
                norm_params[k] = int(v)
                continue
            except Exception:  # pragma: no cover
                pass
        norm_params[k] = v

    params = norm_params

    try:
        data = await backend.get(path, params=params if path and params else None) if path else {}
        pretty = json.dumps({
            "tool": name,
            "path": path,
            "params": params,
            "data": data,
        }, indent=2, sort_keys=True)
        return CallToolResult(content=[{"type": "text", "text": pretty}])
    except httpx.HTTPStatusError as e:
        return CallToolResult(content=[{"type": "text", "text": f"HTTP error {e.response.status_code}: {e.response.text}"}])
    except Exception as e:  # pylint: disable=broad-except
        return CallToolResult(content=[{"type": "text", "text": f"Error calling tool {name}: {e}"}])

# Some versions of the MCP Python library may not expose an 'initialize' decorator.
# Guard this so the server still runs instead of raising AttributeError.
if hasattr(server, "initialize"):
    @server.initialize()
    async def initialize() -> InitializeResult:  # type: ignore
        return InitializeResult(
            protocolVersion="2024-11-05",
            serverInfo=Implementation(name="automated-trader-mcp", version="0.1.0"),
            capabilities={},
        )

async def main():
    _log(f"Starting automated-trader MCP (mcp lib version: {MCP_VERSION})")
    try:
        # Use the stdio_server function from mcp.server.stdio
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=None  # Try None instead of empty dict
            )
    finally:
        await backend.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback
        print(f"Error running server: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
