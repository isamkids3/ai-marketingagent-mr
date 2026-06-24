# MilleniumRadius Backend Server

This repository contains the backend service and agent orchestrator for the **MilleniumRadius** platform. It exposes REST API endpoints via FastAPI and compiles a dynamic marketing agent built on the `deepagents` framework and LangChain.

The backend acts as an **MCP Client**, connecting to the `comfyui-mcp-server` to dynamically discover and invoke image-generation workflows.

---

## Architecture Overview

```mermaid
graph TD
    Client[Web UI / REST Client] -->|POST /api/v1/agent/campaign| API[FastAPI Server]
    API -->|Triggers Background Task| Orchestrator[Agent Orchestrator]
    Orchestrator -->|Establishes Client Session| MCP_Client[MCP Client Bridge]
    MCP_Client -->|JSON-RPC via SSE / stdio| MCP_Server[ComfyUI MCP Server]
    MCP_Server -->|Submits Workflows| ComfyUI[ComfyUI Instance]
    ComfyUI -->|Saves Output| Shared_WS[SHARED_WORKSPACE_ROOT]
```

### Key Features
1. **Dynamic Tool Discovery**: Instead of hardcoding ComfyUI workflows, the agent dynamically fetches and registers tools directly from the MCP server at boot.
2. **Pre-Flight Path Resolution**: Automatically translates virtual paths (like `/workspace/brief.pdf`) into absolute local paths within the shared workspace directory before sending them to the MCP server.
3. **Response Adapter**: Intercepts dense ComfyUI payloads, downloads the output images, saves them under the local static mount (`/shares`), and returns the relative URL string (`/shares/outputs/...`) directly to the agent's memory.
4. **Sandbox & Share Mounts**:
   - `/sandbox` points to `SHARED_WORKSPACE_ROOT` (holds briefs, reference images, and sandboxed outputs).
   - `/shares` holds public assets served static to the frontend.

---

## Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
Set up a virtual environment and install the required libraries:
```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
.venv/bin/pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

Configure the following variables in `.env`:
```env
# Server Configs
PROJECT_NAME="MilleniumRadius"
SECRET_KEY="your-super-secret-jwt-signing-key"

# Database Connection (e.g. PostgreSQL or SQLite)
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/milleniumradius"

# LLM & External API Keys
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4o"
TAVILY_API_KEY="tvly-..."

# Shared Workspace Settings
SHARED_WORKSPACE_ROOT="/Users/adamdali/Documents/MilleniumRadius/gen-content"

# ComfyUI and MCP Server Settings
COMFYUI_URL="http://localhost:8188"
MCP_SERVER_URL="http://127.0.0.1:9000/sse"
MCP_SERVER_SCRIPT="/Users/adamdali/Documents/MilleniumRadius/comfyui-mcp-server/server.py"
```

---

## Running the Server

### 1. Initialize the Database
Ensure your database is running, then run migrations or initialize the tables:
```bash
python db_init.py
```

### 2. Start the FastAPI App
Run the server in development mode:
```bash
.venv/bin/fastapi dev main.py --port 8000
```
The documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Using the Agent

You can trigger the marketing agent by making a POST request to `/api/v1/agent/campaign`. 

### Request Payload:
```json
{
  "prompt": "Create a social media banner for a sportswear brand featuring soccer shoes, referencing /workspace/layout_guideline.png",
  "thread_id": "campaign_june_2026"
}
```

### Execution Flow:
1. The endpoint starts a background task running the agent.
2. The agent connects to the `comfyui-mcp-server`.
3. The prompt is analyzed, the reference layout path is resolved to `SHARED_WORKSPACE_ROOT/layout_guideline.png`, and the dynamic `image_reference_and_text_to_image` MCP tool is called.
4. The generated image is saved, downloaded, and a relative URL is returned.
