#!/usr/bin/env python3
"""Test script to check if MCP imports work"""

try:
    print("Testing basic imports...")
    import asyncio
    print("OK - asyncio imported")
    
    import json
    print("OK - json imported")
    
    import os
    print("OK - os imported")
    
    import sys
    print("OK - sys imported")
    
    import httpx
    print("OK - httpx imported")
    
    print("Testing MCP imports...")
    from mcp.server import Server
    print("OK - mcp.server.Server imported")
    
    from mcp.types import InitializeResult, Implementation, Tool, CallToolResult
    print("OK - mcp.types imported")
    
    from mcp.server.stdio import stdio_server
    print("OK - mcp.server.stdio.stdio_server imported")
    
    print("All imports successful!")
    
except ImportError as e:
    print(f"ERROR - Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"ERROR - Other error: {e}")
    import traceback
    traceback.print_exc()