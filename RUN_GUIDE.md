# Unified Run & Operations Guide (Windows PowerShell)

This guide consolidates all steps to prepare data, run the FastAPI backend, launch the Flutter web frontend, and operate the MCP (Model Context Protocol) server that exposes backend functionality to AI assistants.

---
## 1. Environment Setup

### 1.1 Clone & Navigate
```pwsh
# Already in repo? Skip clone.
cd C:\src\automated-trader
```

### 1.2 Python Virtual Environment (Recommended)
```pwsh
py -3.11 -m venv .venv
# Activate
. .venv\Scripts\Activate.ps1
# Upgrade pip
python -m pip install --upgrade pip
```

### 1.3 Install Python Dependencies
Backend + shared scripts:
```pwsh
pip install -r backend\requirements.txt
```
MCP server (adds MCP + httpx if not already resolved):
```pwsh
pip install -r mcp_server\requirements.txt
```
(Optional) Root utilities (only if you add a combined requirements file later).

### 1.4 Flutter Dependencies
Ensure Flutter 3.x is installed and on PATH:
```pwsh
flutter --version
flutter pub get --directory frontend
```
If your Flutter version is older than project constraints, upgrade Flutter SDK.

---
## 2. Database & Data Preparation

The repository includes an `at_data.sqlite` at root. Backend defaults to `backend/../at_data.sqlite` unless overridden.

### 2.1 Inspect Existing Tables
```pwsh
python list_tables.py
```

### 2.2 (Optional) Enrichment / Maintenance Scripts (Run Order)
Run only if you need to regenerate or update data.
```pwsh
# 1. Populate instruments if missing
python populate_instruments.py

# 2. Sync/update instrument universe (e.g., S&P 500)
python sync_instruments.py

# 3. Fill unknown instrument metadata with defaults
python fill_instrument_metadata.py

# 4. External enrichment (yfinance, etc.)
python enrich_instrument_metadata.py

# 5. ETF classification
python enrich_etf_classification.py

# 6. Backfill style categories / normalize labels
python assign_styles_basic.py
```
Notes:
- Scripts are idempotent where possible; review stdout before re-running repeatedly.
- Style normalization replaced `core` with `value` in prior processing.

### 2.3 Holdings / Strategy Imports (If Needed)
```pwsh
python import_holdings.py  # Ensure holdings table is populated
```

---
## 3. Run the Backend API (FastAPI / Uvicorn)

### 3.1 Development Mode (Auto-Reload)
```pwsh
cd backend
python main.py
```
This starts on port `8000` by default.

### 3.2 Explicit Uvicorn Command
```pwsh
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.3 Environment Overrides
```pwsh
$env:DATABASE_PATH = "C:\\src\\automated-trader\\at_data.sqlite"  # Optional if relocating DB
$env:LOG_LEVEL = "INFO"
```

### 3.4 Basic Health Checks
```pwsh
curl http://localhost:8000/api/health
curl http://localhost:8000/api/holdings/summary
curl "http://localhost:8000/api/holdings/positions?limit=5"
```

---
## 4. Run the Frontend (Flutter Web)

In a new terminal (keep backend running):
```pwsh
cd frontend
flutter pub get
flutter run -d web-server --web-port 3000
```
Access UI: http://localhost:3000

Hot reload is available while terminal remains open.

---
## 5. MCP Server (Model Context Protocol)

The MCP server exposes backend endpoints as AI assistant tools over stdio.
Location: `mcp_server/server.py`

### 5.1 Environment Variables
```pwsh
$env:AT_BACKEND_BASE_URL = "http://localhost:8000/api"  # Override if backend served elsewhere
$env:AT_MCP_DEBUG = "1"                                  # Enable verbose stderr logging (optional)
$env:AT_MCP_PERMISSIVE = "1"                             # Use simplified input schemas (debug)
```
Unset permissive mode (stricter JSON Schema validation) once stable:
```pwsh
Remove-Item Env:AT_MCP_PERMISSIVE
```

### 5.2 Start MCP Server
```pwsh
python -m mcp_server.server
```
The process waits on stdio for a client (e.g., Claude Desktop, Cline, custom MCP harness).

### 5.3 Switching to Strict Schema
```pwsh
$env:AT_MCP_PERMISSIVE = "0"  # or remove variable
python -m mcp_server.server
```

### 5.4 Available Tools
| Tool | Description | Params |
|------|-------------|--------|
| echo | Debug echo | message? |
| health_check | Backend health | (none) |
| get_portfolio_summary | Portfolio overview | (none) |
| list_positions | Positions list | account?, ticker?, limit?, offset? |
| list_accounts | Account list | (none) |
| get_instruments | Instrument search | page?, size?, ticker?, sector?, instrument_type? |
| get_holding_detail | Holding detail | ticker (required) |

### 5.5 Sample JSON-RPC Exchange (Manual Testing)
If you want to manually exercise the server (advanced):
1. Start server: `python -m mcp_server.server`
2. In another terminal, you can pipe JSON lines (requires a small custom client). For quick inspection, rely on an MCP-capable client instead.

Example request objects (client side responsibility):
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "list_tools"
}
```
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "call_tool",
  "params": {"name": "echo", "arguments": {"message": "Hello"}}
}
```
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "call_tool",
  "params": {"name": "list_positions", "arguments": {"limit": 5}}
}
```

### 5.6 Debug Tips
- If you see `Unknown tool`, call `list_tools` first to confirm registration.
- Use permissive mode (`AT_MCP_PERMISSIVE=1`) if client rejects schemas with `-32602 Invalid params`.
- Integer parameters accept numeric strings; server normalizes them.
- Enable `$env:AT_MCP_DEBUG = "1"` to surface stderr trace messages.

---
## 6. Common Workflows

### 6.1 Full Clean Start (Fresh Shell)
```pwsh
cd C:\src\automated-trader
. .venv\Scripts\Activate.ps1
$env:AT_BACKEND_BASE_URL = "http://localhost:8000/api"
python backend\main.py  # Terminal 1
```
New terminal:
```pwsh
cd C:\src\automated-trader\frontend
flutter run -d web-server --web-port 3000  # Terminal 2
```
Optional third terminal (MCP):
```pwsh
cd C:\src\automated-trader
$env:AT_MCP_DEBUG = "1"
python -m mcp_server.server  # Terminal 3
```

### 6.2 Data Refresh Cycle
```pwsh
python sync_instruments.py
python enrich_instrument_metadata.py
python enrich_etf_classification.py
python assign_styles_basic.py
```

### 6.3 Quick MCP Tool Smoke Test
Within your MCP client (conceptual commands):
- list tools
- call tool: echo {"message": "ping"}
- call tool: health_check {}
- call tool: list_accounts {}
- call tool: list_positions {"limit": 3}

---
## 7. Testing & Validation

### 7.1 Backend Tests
```pwsh
cd backend
pytest -q
```

### 7.2 Targeted Endpoint Checks
```pwsh
curl http://localhost:8000/api/holdings/accounts
curl "http://localhost:8000/api/instruments?ticker=MSFT"
```

### 7.3 MCP Behavior
If a tool fails:
- Confirm backend endpoint directly via curl.
- Re-run MCP with debug: `$env:AT_MCP_DEBUG = "1"`.
- Try permissive schema flag if param validation triggers.

---
## 8. Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Backend 404 | Wrong base URL | Ensure `AT_BACKEND_BASE_URL` ends with `/api` |
| MCP silent | Client not attached | Use an MCP-capable client; stdio sits idle |
| Invalid params (-32602) | Schema mismatch | Enable permissive mode |
| HTTP error 422 | Missing required param | Add required field (`ticker`) |
| Flutter hot reload slow | Dev build constraints | Consider `--web-renderer canvaskit` |
| SQLite lock | Concurrent writes | Avoid running multiple enrichment scripts simultaneously |

---
## 9. Extending the System

### 9.1 Adding a New Backend Endpoint
1. Create route in `backend/api/`.
2. Add logic in corresponding `services/` module.
3. Update `models/schemas.py` if new models needed.
4. Add test in `backend/tests/`.

### 9.2 Exposing Endpoint via MCP Tool
1. Edit `mcp_server/server.py` `TOOLS` dict; add entry:
```python
"new_tool": {
  "description": "Describe it",
  "params": {"foo": {"type": "string", "required": False}},
  "path": "/api/path"  # Omit /api because base maps to /api already? (Note: base URL already ends with /api)
}
```
2. Restart MCP server.
3. Call `list_tools` to verify.

### 9.3 Frontend Consumption
Add method in `frontend/lib/services/api_service.dart`, create provider, integrate into UI widget/state.

---
## 10. Reference Paths
- Backend root: `backend/`
- Frontend root: `frontend/`
- MCP server: `mcp_server/server.py`
- Database file: `at_data.sqlite`

---
## 11. Quick Command Cheat Sheet
```pwsh
# Activate env
. .venv\Scripts\Activate.ps1

# Backend
python backend\main.py

# Frontend
cd frontend; flutter run -d web-server --web-port 3000

# MCP (debug + permissive)
$env:AT_MCP_DEBUG = "1"; $env:AT_MCP_PERMISSIVE = "1"; python -m mcp_server.server

# Test endpoints
curl http://localhost:8000/api/holdings/summary

# Quick positions via MCP (conceptual client command)
call_tool name=list_positions arguments={"limit":5}
```

---
## 12. Notes
- Keep `AT_MCP_PERMISSIVE` disabled in stable environments to surface contract issues early.
- The MCP server currently supports only GET passthroughs; extend `BackendClient` for POST/PUT as needed.
- Cost basis semantics: `cost_basis` = total cost, not per-share.

---
**Last Updated:** $(Get-Date -Format 'yyyy-MM-dd')
