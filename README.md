# Millenium Radius: Marketing AI Agent Platform

Welcome to the **Millenium Radius** platform—a production-grade, web-based Marketing AI Agent system designed to automate creative asset production, copywriting, and multi-platform aspect ratio tailoring. 

Users submit campaign briefs, prompts, or product asset photos, and the system intelligently orchestrates generation, tailoring captions/tones, formatting sizes (e.g., 9:16, 16:9, 1:1) to major target social platforms, and compiling deliverables.

---

## 1. Project Capabilities & Features

* **Multimodal Chat Interaction:** Supports full iterative conversational refinement with image attachments, follow-up instructions, and context retention.
* **Intelligent Routing & Framing:** Analyzes intent using a local LLM to route tasks dynamically between text-to-image, reference-image-to-image, and brand/tone transformations (casual, professional, creative).
* **Multi-Platform Aspect Formatter:** Automatically formats final media deliverables using localized social media layout templates and platform ratios.
* **Context Window Optimization:** Operates entirely locally on a 42,000 token limit using dynamic schema lazy-loading (on-demand MCP tool loading) and strict message boundaries to prevent context bloat.
* **Shared Sandbox Environment:** Uses a unified local workspace volume for secure asset pre-flight path resolution, sandboxed file writing, and public web-serving mounts.

---

## 2. System Architecture

The platform operates on a **5-tier decoupled architecture** spanning web, intelligence, protocol, and hardware rendering layers.

```
+-------------------------------------------------------------+
|                     Layer 1: Frontend UI                    |
|                Next.js 16 + React 19 + Tailwind             |
+------------------------------+------------------------------+
                               |
                               | (HTTP Fetch / WebSockets)
                               v
+-------------------------------------------------------------+
|          LAYER 2 & 3: AI ORCHESTRATOR & WEB BACKEND         |
|                 FastAPI Server - Port 8000                  |
|                                                             |
|  +-----------------------+              Loads Directly      |
|  |     FastAPI Router    +--------------------------------+ |
|  |  (Auth, Sessions, WS) |                                | |
|  +-----------------------+                                v |
|  +--------------------------------------------------------+ |
|  |            LangChain Agent Core (The Brain)            | |
|  |   - Binds MCP Tools          - Local Qwen 3.6-35B LLM  | |
|  |   - Parses Tone & Demography - Manages Session State   | |
|  +--------------------------------------------------------+ |
+------------------------------+------------------------------+
                               |
                               | (Model Context Protocol - Port 9000)
                               v
+-------------------------------------------------------------+
|          Layer 4: Creator API (comfyui-mcp-server)          |
|    - Handles tool map generation & dynamic asset registry   |
|    - Compiles abstract JSON parameters into workflows       |
+------------------------------+------------------------------+
                               |
                               | (Local WebSockets - Port 8188)
                               v
+-------------------------------------------------------------+
|              Layer 5: ComfyUI Hardware Renderer             |
|         - Runs Ideogram 4.0 & Flux 2.1 (Dev) pipelines      |
+-------------------------------------------------------------+
```

### Communication Protocols
* **Layer 1 to Layer 2 & 3:** REST APIs (HTTP Fetch) for session control, user authentication, and system health status. Stateful WebSockets stream active chat messages and token generations.
* **Layer 2 & 3 to Layer 4:** Model Context Protocol (MCP) JSON payloads served via SSE (Server-Sent Events) or stdio transport.
* **Layer 4 to Layer 5:** Local WebSockets and REST endpoints (`/view`, `/upload`, `/prompt`) hosted by ComfyUI to control execution graph pipelines.

---

## 3. Repository Directory Structure

The workspace is organized into separate repositories interlocking via config variables and shared mounts:

```
MilleniumRadius/
├── backend/                  # FastAPI Web Backend & LangChain Agent
│   ├── app/                  # Application core modules (agent, api, database, models)
│   ├── migrations/           # Alembic database migrations
│   ├── shares/               # Public assets served static to the frontend UI
│   ├── .env.example          # Environment variables template
│   └── requirements.txt      # Backend Python dependencies
│
├── comfyui-mcp-server/       # Model Context Protocol (MCP) server
│   ├── managers/             # Workflow, Asset, Defaults, and Publish managers
│   ├── workflows/            # JSON workflows and dynamic metadata files
│   ├── tools/                # Specialized MCP tools (asset, generation, doc tools)
│   ├── server.py             # Server entry point (supports stdio & streamable-http)
│   └── requirements.txt      # MCP Server Python dependencies
│
├── front-end/                # Next.js Frontend UI Client
│   ├── src/
│   │   ├── app/              # Main app pages, styles, layout routing
│   │   └── components/       # Chat window, sidebar, input area components
│   ├── package.json          # Node package definition
│   └── tsconfig.json         # TypeScript configuration
│
└── gen-content/              # Shared Workspace Volume (Shared Sandbox)
                              # Resolves input paths, briefs, and houses ComfyUI renders
```

---

## 4. Core Operational Flow

1. **Ingestion:** The user submits a prompt, product image, or PDF campaign brief to the **Layer 1 UI**.
2. **Intent Parsing:** **Layer 2 & 3** receives the payload. The LangChain orchestrator prompts the **Qwen LLM** to extract target tones, demography data, and decide if image generation or editing is required.
3. **MCP Tool Dispatch:** The LLM requests tool execution. The agent triggers MCP client tools (`text_image`, `image_image`, etc.) registered dynamically from the **Layer 4 MCP Server**.
4. **Pre-flight & Workspace Mapping:** The backend translates virtual document paths into local absolute paths within `gen-content/` and forwards the structured parameters to **Layer 4**.
5. **Graph Unrolling & Compiling:** The **Layer 4 MCP Server** compiles parameters directly into a ComfyUI execution graph.
6. **Hardware Render:** The local **ComfyUI engine (Layer 5)** processes the workflows using Ideogram 4.0/Flux and outputs files to `gen-content/`.
7. **Deliverable Adaptation:** The backend processes generated assets, copies them to the public `/shares` path, applies platform formatting/aspect ratio modifications, and streams the finished assets to the UI.

---

## 5. Startup & Deployment Guide

Follow these sequential steps to boot the entire local stack.

### Step 1: Core Datastore Setup (PostgreSQL)

Spin up an isolated PostgreSQL database to store user authentication keys, conversational threads, and history.

* **Create and run the database container:**
```bash
docker run --name millenium-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=my_secure_dev_password \
  -e POSTGRES_DB=millenium_radius \
  -p 5432:5432 \
  -v backend_postgres_data:/var/lib/postgresql/data \
  -d postgres:16-alpine
```

* **Control container lifecycle:**
```bash
# Start the database container
docker start millenium-postgres

# Stop the database container
docker stop millenium-postgres
```

---

### Step 2: ComfyUI Hardware Renderer Environment

Initialize a virtual environment for the rendering engine and fetch the target weights.

```bash
# 1. Environment initialization & Core framework setup
python3 -m venv comfyui-ideogram-env
source comfyui-ideogram-env/bin/activate

pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu130

git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI/
pip install -r requirements.txt
pip install huggingface_hub[cli]

# 2. Fetch the Qwen3-VL Vision/Text Encoder
mkdir -p models/text_encoders/
huggingface-cli download Comfy-Org/Qwen3-VL qwen3vl_8b_fp8_scaled.safetensors --local-dir models/text_encoders/

# 3. Fetch the Core Base Weights (Scaled and Unconditional models)
mkdir -p models/diffusion_models/
huggingface-cli download Comfy-Org/Ideogram-4 diffusion_models/ideogram4_fp8_scaled.safetensors --local-dir models/
huggingface-cli download Comfy-Org/Ideogram-4 diffusion_models/ideogram4_unconditional_fp8_scaled.safetensors --local-dir models/

# 4. Fetch the Compatible VAE & clean up file path layout
mkdir -p models/vae/
huggingface-cli download Comfy-Org/flux2-dev split_files/vae/flux2-vae.safetensors --local-dir models/vae/ --local-dir-use-symlinks False

mv models/vae/split_files/vae/flux2-vae.safetensors models/vae/
rm -rf models/vae/split_files/

# 5. Launch the ComfyUI Hardware Render Server
python main.py --listen 0.0.0.0 --port 8188 --enable-manager
```

#### ComfyUI Models Directory Layout

Ensure your ComfyUI models folder matches the directory structure below:

```
models/
├── diffusion_models
│   ├── flux2_dev_fp8mixed.safetensors
│   ├── ideogram4_fp8_scaled.safetensors
│   └── ideogram4_unconditional_fp8_scaled.safetensors
├── loras
│   ├── Flux2TurboComfyv2.safetensors
│   └── Flux_2-Turbo-LoRA_comfyui.safetensors
├── text_encoders
│   ├── mistral_3_small_flux2_bf16.safetensors
│   ├── mistral_3_small_flux2_fp8.safetensors
│   └── qwen3vl_8b_fp8_scaled.safetensors
└── vae
    ├── flux2-vae.safetensors
    └── full_encoder_small_decoder.safetensors
```

---

### Step 3: LLM Inference Container Controls (Qwen Agent Backend)

Manage host VRAM allocations by spinning the containerized local Qwen model backend up or down.

* **Free VRAM completely (Stop and spin down):**
```bash
sudo docker stop qwen-agent-backend
```

* **Instantly resume inference container:**
```bash
sudo docker start qwen-agent-backend
```

* **Monitor streaming generation logs:**
```bash
sudo docker logs -f qwen-agent-backend
```

* **Verify container execution states:**
```bash
sudo docker ps
# View all containers (including stopped instances):
sudo docker ps -a
```

* **Permanently wipe container configuration (to adjust mappings/VRAM limits):**
```bash
sudo docker stop qwen-agent-backend
sudo docker rm qwen-agent-backend
```

---

### Step 4: Model Context Protocol (MCP) Server Setup

Prepare the Creator API to bridge the backend and ComfyUI.

1. Navigate to the MCP server directory and configure python requirements:
   ```bash
   cd comfyui-mcp-server
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Launch the MCP server as a standalone HTTP service (defaulting to Port 9000):
   ```bash
   python server.py
   ```
   *(Note: Add `--stdio` if connecting directly to LLM environments utilizing stdio pipelines rather than SSE)*.

---

### Step 5: Web Backend Setup

Configure connection endpoints and seed database tables.

1. Navigate to the backend directory and set up dependencies:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Create your `.env` configuration file:
   ```bash
   cp .env.example .env
   ```
   Configure key variables inside `.env`:
   ```env
   PROJECT_NAME="Millenium Radius API"
   API_V1_STR="/api/v1"
   
   # PostgreSQL Connection
   DATABASE_URL=postgresql+asyncpg://postgres:my_secure_dev_password@localhost:5432/millenium_radius
   
   # Local Qwen Backend Configuration
   OPENAI_API_KEY=adam-dali-test-qwen-key
   OPENAI_MODEL=Qwen/Qwen3.6-35B-A3B-FP8
   OPENAI_API_BASE=http://localhost:8000/v1
   
   # Sandbox and ComfyUI Paths
   SHARED_WORKSPACE_ROOT="/Users/adamdali/Documents/MilleniumRadius/gen-content"
   COMFYUI_URL="http://localhost:8188"
   MCP_SERVER_URL="http://127.0.0.1:9000/mcp"
   MCP_SERVER_SCRIPT="/Users/adamdali/Documents/MilleniumRadius/comfyui-mcp-server/server.py"
   ```
3. Initialize tables and database structures:
   ```bash
   python db_init.py
   ```
4. Launch the FastAPI backend:
   ```bash
   fastapi dev main.py --port 8000
   ```

---

### Step 6: Frontend Client Setup

Boot the client user interface.

1. Navigate to the frontend directory:
   ```bash
   cd front-end
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the Next.js development client (serves on Port 3000):
   ```bash
   npm run dev
   ```
4. Access the UI dashboard by visiting [http://localhost:3000](http://localhost:3000) and register/login with a local email address to begin prompting campaigns.

---

## 6. Verification and Diagnostics

Ensure layers are properly routing communications using these check commands.

### Test MCP connection workflows
Run the local workflow execution test script inside the `comfyui-mcp-server` environment:

* **Dry-Run Workflow Generation (Prints compiled JSON configuration map without submitting it to ComfyUI):**
```bash
python3 test_workflow_execution.py --workflow text-image --prompt "A futuristic cityscape" --print-only
```

* **Execute full Text-to-Image pipeline:**
```bash
python3 test_workflow_execution.py --workflow text-image --prompt "A beautiful digital art of a celestial phoenix rising from ashes, fantasy illustration"
```

* **Execute full Image-to-Image pipeline:**
```bash
python3 test_workflow_execution.py --workflow image-image --prompt "Make the image look like an oil painting" --image /path/to/local/source.png
```
