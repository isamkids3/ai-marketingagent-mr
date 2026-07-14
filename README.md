# Millenium Radius: Marketing AI Agent Platform

Welcome to the **Millenium Radius** platform—a prototype-grade, web-based Marketing AI Agent system designed to automate creative asset production, copywriting, and multi-platform aspect ratio tailoring. 

Users submit campaign briefs, prompts, or product asset photos, and the system intelligently orchestrates generation, tailoring captions/tones, formatting sizes (e.g., 9:16, 16:9, 1:1) to major target social platforms, and compiling deliverables.

---

## 1. Project Capabilities & Features

* **Multimodal Chat Interaction:** Supports full iterative conversational refinement with image attachments, follow-up instructions, and context retention.
* **Interactive Image Masking & Local Inpainting:** Allows users to paint mask overlays directly on reference images using an interactive brush canvas modal. The backend automatically handles ComfyUI RGBA merging and alpha inversion.
* **Intelligent Routing & Framing:** Analyzes intent using a local LLM to route tasks dynamically between text-to-image, reference-image-to-image, and brand/tone transformations.
* **Text-to-Video & Video-to-Video Animation:** Exposes advanced video workflows leveraging LTX models (via ComfyUI) to generate 15-second or 30-second video clips (`text_video` and `image_text_video`) directly from text prompts or reference images.
  > [!NOTE]
  > Heavy video models like LTX-Video can take 5+ minutes to generate on GPUs. To prevent browsers (e.g., Brave, Chrome) from timing out the HTTP connection during these runs, the backend implements active SSE keep-alive ping heartbeats every 15 seconds, and the connection/execution timeouts are extended to 800 seconds.
* **Direct Downloads & Document File Cards:** Displays generated `.pdf` and `.md` files as elegant interactive Document Cards with inline **Preview** and direct **Download** actions. Generated images and videos feature seamless download overlay buttons to bypass manual path copying.
* **3-Image Reference Editing & Compositing:** Enables blending subjects, accessories, and backgrounds/environments from up to three distinct reference images into a single cohesive output visual using the `image_image_3ref` tool.
* **Virtual Sandbox Workspace Resolution:** Configures virtual `/sandbox/` path mapping to the local workspace volume, with **Session ID Auto-Stripping** to prevent double-session path nesting.
* **Dynamic S3/R2 Asset Self-Healing:** Prevents publishing errors by dynamically parsing the Cloudflare R2 bucket configuration and auto-healing token hash truncations in attachment links.
* **Multi-Platform Aspect Formatter:** Automatically formats final media deliverables using localized social media layout templates and platform ratios.
* **Context Window Optimization:** Operates locally on a 42,000 token limit using dynamic schema lazy-loading (on-demand MCP tool loading) and strict message boundaries to prevent context bloat.
* **Shared Sandbox Environment:** Uses a unified local workspace volume for secure asset pre-flight path resolution, sandboxed file writing, and public web-serving mounts.

---

## 2. Technical Stack

| Layer / Component | Technology | Description / Usage |
| :--- | :--- | :--- |
| **Frontend UI** | Next.js 16 + React 19 + Tailwind CSS v4 | Interactive UI client, styled with Tailwind CSS, featuring HTML5 Canvas for the image masking tools. |
| **Web Backend** | Python + FastAPI + Uvicorn | Session control, authentication, SSE streams, static asset delivery, and Pillow (PIL) for image/mask merging. |
| **Datastore** | PostgreSQL 16 (Dockerized) | Persistent storage for users, chat histories, session logs, and assets. |
| **AI Agent Framework** | LangChain | Core orchestrator for routing, message memory management, and MCP tool bindings. |
| **AI Agent Search Engine** | Tavily | Dynamic web-search integration for live market research and context enrichment. |
| **Inference LLM** | Qwen 3.6 - 35B | Locally hosted large language model running inside a vLLM container for fast local orchestration. |
| **Creator MCP API** | Python (Model Context Protocol) | Custom server based on [comfyui-mcp-server](https://github.com/joenorton/comfyui-mcp-server) exposing dynamic generation and registry tools. |
| **Image & Video Generation** | ComfyUI + Ideogram 4.0 + Flux 2.1 (Dev) + LTX-Video 0.9 | Locally hosted hardware-accelerated diffusion/transformer pipeline for high-fidelity asset rendering and 15s/30s cinematic animations. |
| **Social Media Publisher** | Postiz (Next.js/NestJS) + Cloudflare R2 | Self-hosted social media scheduler and publisher integrated via S3-compatible cloud bucket storage. |

---

## 3. System Architecture

The platform operates on a **5-tier decoupled architecture** spanning web, intelligence, protocol, and hardware rendering layers.

```
+-------------------------------------------------------------+
|                     Layer 1: Frontend UI                    |
|             Next.js 16 + React 19 + Tailwind v4             |
+------------------------------+------------------------------+
                               |
                               | (HTTP Fetch / WebSockets / SSE)
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
* **Layer 1 to Layer 2 & 3:** REST APIs (HTTP Fetch) for session control, user authentication, and system health status. Server-Sent Events (SSE) stream active chat messages and token generations.
* **Layer 2 & 3 to Layer 4:** Model Context Protocol (MCP) JSON payloads served via stdio or SSE transport.
* **Layer 4 to Layer 5:** Local WebSockets and REST endpoints (`/view`, `/upload`, `/prompt`) hosted by ComfyUI to control execution graph pipelines.

---

## 4. Repository Directory Structure

The workspace is organized into separate directories interlocking via config variables and shared mounts:

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

## 5. Core Operational Flow

1. **Ingestion:** The user submits a prompt, product image, brief, or mask paint payload to the **Layer 1 UI**.
2. **Intent Parsing:** **Layer 2 & 3** receives the payload. The LangChain orchestrator prompts the **Qwen LLM** to extract target tones, demography data, and decide if image generation, reference img2img, or local mask-inpainting (`mask_image_image`) is required.
3. **Pillow Mask Merging (Inpainting only):** If a mask is provided, the backend merges the original image and mask into a single RGBA PNG. Grayscale mask values are mathematically inverted to match ComfyUI alpha conventions (`alpha = 255 - mask_pixel`).
4. **MCP Tool Dispatch:** The LLM requests tool execution. The agent triggers MCP client tools (`text_image`, `image_image`, `mask_image_image`) registered dynamically from the **Layer 4 MCP Server**.
5. **Pre-flight & Workspace Mapping:** The backend translates virtual document paths into local absolute paths within `gen-content/` and forwards the structured parameters to **Layer 4**.
6. **Graph Unrolling & Compiling:** The **Layer 4 MCP Server** compiles parameters directly into a ComfyUI execution graph. For inpainting, it prioritizes `SaveImage` node outputs to return the final stitched rendering instead of intermediate cropped previews.
7. **Hardware Render:** The local **ComfyUI engine (Layer 5)** processes the workflows using Ideogram 4.0/Flux and outputs files to `gen-content/`.
8. **Deliverable Adaptation:** The backend processes generated assets, copies them to the public `/shares` path, applies platform formatting/aspect ratio modifications, and streams the finished assets to the UI.

---

## 6. Startup & Deployment Guide

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

## 7. Verification and Diagnostics

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

* **Execute full Text-to-Video pipeline (LTX Model):**
```bash
python3 test_workflow_execution.py --workflow text-video --prompt "A fluffy cat dancing under colorful disco lights, 15 seconds"
```

* **Execute full Image-to-Video animation pipeline (LTX Model):**
```bash
python3 test_workflow_execution.py --workflow image_text-video --prompt "Animate this cat dancing" --image /path/to/local/source.png
```

---

## 8. Postiz Social Media Integration & Troubleshooting

The platform integrates directly with **Postiz** using the Model Context Protocol (MCP) to schedule, draft, and publish generated campaign assets across 28+ channels (X/Twitter, LinkedIn, Instagram, Threads, Discord, etc.).

### Architecture & Connection
* **Multi-Session Client Connection**: The FastAPI backend orchestrator (`app/agent/orchestrator.py`) concurrently connects to the ComfyUI MCP server (stdio) and the Postiz MCP server (streamable HTTP SSE transport).
* **Environment Variables**: Managed via `/postiz-docker-compose/.env`.
* **Agent Integration**: The agent dynamically parses the available social posting tools (e.g. `integrationList`, `schedulePostTool`, `generateImageTool`) and uses native system prompts to coordinate scheduling.
### Key Hurdles & Solutions

#### Instagram / Meta "Media Fetch Failed" & Storage Resolution
* **The Hurdle**: Meta's Graph APIs publish images by sending a request to "pull" the image file from a public URL. Since Postiz runs locally on a private network (`http://localhost:4007`), Meta's servers cannot reach it, causing a `Media fetch failed` error.
* **R2 Host Constraints**: Postiz's R2 storage client hardcodes the S3 endpoint to Cloudflare R2's domain (`<id>.r2.cloudflarestorage.com`). This makes it impossible to use non-Cloudflare S3 providers (like Backblaze B2) without triggering SSL handshake errors.
* **The Solution (Cloudflare R2 Configuration)**:
  1. Enable Cloudflare R2 on your account (requires a valid card/Apple Pay on file, but stays free under 10 GB/month).
  2. Update your `docker-compose.yaml` file to map `STORAGE_PROVIDER="cloudflare"` and the associated `CLOUDFLARE_` environment variables.
  3. In your Cloudflare bucket settings, **enable the public r2.dev subdomain** (or connect a custom domain) to get a public `https` URL.
  4. In your `.env` file, set `CLOUDFLARE_BUCKET_URL="https://pub-xxxxxx.r2.dev"` (your public R2 subdomain) and set `CLOUDFLARE_REGION="auto"`.
  5. **Auto-Delete Spending Protection**: Under your Cloudflare bucket settings -> **Object Lifecycle Rules**, add a rule to automatically delete objects after **7 days**. This keeps your storage usage near 0 MB, guaranteeing you never exceed the 10 GB free tier.

