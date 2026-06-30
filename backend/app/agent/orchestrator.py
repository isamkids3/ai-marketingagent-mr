import os
import tempfile
import json
import logging
from typing import Optional, List, Dict, Any, Literal
from dotenv import load_dotenv
load_dotenv()
# pyrefly: ignore [missing-import]
from deepagents import create_deep_agent
# pyrefly: ignore [missing-import]
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
from app.agent.tools import (
    internet_search,
    write_file_to_sandbox,
    read_user_document_tool,
    generate_pdf_in_sandbox,
    BASE_WORKSPACE
)
from app.agent.comfy_router import WorkspaceManager

# MCP-related imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
# pyrefly: ignore [missing-import]
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model, Field, model_validator
import httpx


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


class CompositionElement(BaseModel):
    type: Literal["obj", "text"] = Field(
        ...,
        description="Type of element: 'obj' for physical objects, characters, buildings, etc. 'text' for typography, labels, signs."
    )
    bbox: Optional[List[int]] = Field(
        None,
        description="Bounding box [y1, x1, y2, x2] normalized to a 0-1000 scale. Top-left origin. MANDATORY: Specify on a 0-1000 scale. WARNING: DO NOT use 0-100 percentages (e.g. write 100 to 900, NOT 10 to 90). WARNING: You MUST use the Y-first format [y1, x1, y2, x2]. DO NOT swap X and Y (e.g. do NOT write [x1, y1, x2, y2], which turns horizontal layouts into vertical pillars)."
    )
    desc: str = Field(
        ...,
        description=(
            "30-60 words description. For 'obj': physical details (MANDATORY: NEVER name specific clothing "
            "garments like swimsuit, bikini, or underwear; instead describe the environment and situational "
            "context, e.g. 'enjoying a sunny resort pool area'). For 'text': font style, size, color, placement description."
        )
    )
    text: Optional[str] = Field(
        None,
        description="Verbatim characters to render. REQUIRED ONLY for 'text' type elements. Use \\n for line breaks. You MUST provide the literal text string here if type is 'text'."
    )

    @model_validator(mode="after")
    def validate_text_for_typography(self) -> 'CompositionElement':
        if self.type == "text":
            if not self.text:
                raise ValueError(
                    "The 'text' field is mandatory and must not be empty or null when element 'type' is 'text'."
                )
            if self.bbox:
                y1, x1, y2, x2 = self.bbox
                height = y2 - y1
                width = x2 - x1
                # Check for vertical pillar trap (likely X/Y swapped coordinates)
                if height > 2.0 * width and len(self.text) > 12 and self.text.count('\n') < 2:
                    raise ValueError(
                        f"The text bounding box {self.bbox} is extremely tall and narrow (height={height}, width={width}), "
                        f"but the text '{self.text}' is a long horizontal string ({len(self.text)} chars) with fewer than 2 line breaks. "
                        "This will squeeze the text into a vertical pillar and cause layout/spelling glitches. "
                        "Please check if you swapped X and Y coordinates (you MUST use [y1, x1, y2, x2] order), "
                        "or widen the box and add manual '\\n' line breaks."
                    )
                # Check for excessive height relative to line count (causes text duplication/stretching)
                num_lines = self.text.count('\n') + 1
                max_allowed_height = num_lines * 100
                if height > max_allowed_height:
                    raise ValueError(
                        f"The text bounding box {self.bbox} has a height of {height} for {num_lines} line(s) of text. "
                        f"This is too tall (max height allowed for {num_lines} line(s) is {max_allowed_height}). "
                        "Excessive vertical space forces the generator to duplicate lines or stretch text. "
                        "Please decrease the bounding box height (y2 - y1) to fit the text tightly (recommend 70-80 per line, e.g. height 210-240 for 3 lines)."
                    )
            # Check for spelling typos against user prompt words
            user_words = active_user_words.get()
            if user_words:
                import re
                agent_words = re.findall(r'\b[a-zA-Z]{4,}\b', self.text.lower())
                for w_agent in agent_words:
                    if w_agent not in user_words:
                        for w_user in user_words:
                            if len(w_user) >= 5 and levenshtein_distance(w_agent, w_user) == 1:
                                # Skip valid pluralizations / simple suffixes
                                if w_agent.startswith(w_user) and w_agent[-1] == 's':
                                    continue
                                if w_user.endswith('e') and w_agent == w_user[:-1] + 'ed':
                                    continue
                                if w_agent == w_user + 'ed':
                                    continue
                                if w_agent == w_user + 's':
                                    continue
                                raise ValueError(
                                    f"Spelling anomaly detected: The word '{w_agent}' in layout text is extremely close to the user's word '{w_user}' from chat history, "
                                    f"but is not equal. Please check for spelling typos in the text element (e.g., 'gocery' instead of 'grocery', or 'cofee' instead of 'coffee')."
                                )
        return self


class CompositionalDeconstruction(BaseModel):
    background: str = Field(
        ...,
        description="Description of the scene shell (walls, floor, sky, weather, ambient lighting). NEVER include elements listed in the elements array. For transparent canvas, MUST be exactly 'transparent background'."
    )
    elements: List[CompositionElement] = Field(
        ...,
        description="List of all individually placeable objects, characters, visual graphic elements, and typography text blocks."
    )

    @model_validator(mode="after")
    def validate_coordinate_scale(self) -> 'CompositionalDeconstruction':
        all_coords = []
        for el in self.elements:
            if el.bbox:
                all_coords.extend(el.bbox)
        if all_coords and max(all_coords) <= 100:
            raise ValueError(
                "All bounding box coordinates are <= 100. It appears you used a 0-100 percentage scale. "
                "You MUST use a 0-1000 pixel-based scale (e.g. scale up by multiplying by 10, like [100, 200, 900, 800])."
            )
        return self

    @model_validator(mode="after")
    def validate_no_text_obj_overlap(self) -> 'CompositionalDeconstruction':
        texts = [el for el in self.elements if el.type == "text" and el.bbox]
        objs = [el for el in self.elements if el.type == "obj" and el.bbox]
        for t in texts:
            y1_t, x1_t, y2_t, x2_t = t.bbox
            for o in objs:
                y1_o, x1_o, y2_o, x2_o = o.bbox
                # Check if bounding boxes intersect
                if not (x2_t <= x1_o or x1_t >= x2_o or y2_t <= y1_o or y1_t >= y2_o):
                    raise ValueError(
                        f"Overlap/Intersection detected: The text overlay element '{t.text}' with bbox {t.bbox} "
                        f"overlaps with the foreground object element '{o.desc[:40]}...' with bbox {o.bbox}. "
                        "To prevent rendering corruption and pixel-fighting, you MUST keep text and foreground objects physically separate. "
                        "Please shift or segment their bounding boxes so they do not intersect."
                    )
        return self


class IdeogramPrompt(BaseModel):
    aspect_ratio: str = Field(
        ...,
        description="Target W:H ratio (e.g., '16:9', '9:16', '1:1', '4:5', '3:2'). MUST NOT be 'auto'."
    )
    high_level_description: str = Field(
        ...,
        description="1-2 sentences summary of the overall scene (max 50 words). For transparent background, include the literal phrase 'on a transparent background'."
    )
    compositional_deconstruction: CompositionalDeconstruction = Field(
        ...,
        description="Structured deconstruction of the background and all visual elements."
    )


# Create local temp directory for visual briefs and generated assets
workspace_dir = tempfile.mkdtemp(prefix="marketing_workspace_")
WorkspaceManager.set_workspace_dir(workspace_dir)

# Route "/workspace/" virtual paths to actual local disk storage
backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/workspace/": FilesystemBackend(root_dir=workspace_dir, virtual_mode=True),
    }
)


# Instantiate model dynamically from environment (supports official OpenAI models and local servers)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key or openai_api_key == "your-actual-openai-api-key-here":
    openai_api_key = "mock-key-for-local-use"

openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
openai_api_base = os.getenv("OPENAI_API_BASE")  # Will default to official OpenAI API if None

class TokenLimitingChatOpenAI(ChatOpenAI):
    """
    A ChatOpenAI wrapper that counts prompt tokens and applies early stopping
    by stripping tools when approaching the model's context window.
    """
    def _estimate_tokens(self, messages: List[Any], tools: Optional[List[Any]] = None) -> int:
        try:
            # pyrefly: ignore [missing-import]
            import tiktoken
            # Try to get encoding for the model; fall back to cl100k_base
            try:
                encoding = tiktoken.encoding_for_model(self.model_name)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start><role><im_sep>
                content = getattr(message, "content", "")
                if isinstance(content, str):
                    num_tokens += len(encoding.encode(content))
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                num_tokens += len(encoding.encode(part.get("text", "")))
                        elif isinstance(part, str):
                            num_tokens += len(encoding.encode(part))
                elif isinstance(content, dict):
                    num_tokens += len(encoding.encode(json.dumps(content)))
                
                # Count tool calls if present
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        num_tokens += len(encoding.encode(json.dumps(tc)))
            
            if tools:
                for t in tools:
                    # Safely serialize tool to avoid TypeError on LangChain Tool objects
                    if hasattr(t, "dict"):
                        t_val = t.dict()
                    elif hasattr(t, "args_schema") and t.args_schema:
                        t_val = {"name": t.name, "description": t.description, "parameters": t.args_schema.schema()}
                    else:
                        t_val = t
                    try:
                        num_tokens += len(encoding.encode(json.dumps(t_val)))
                    except Exception:
                        num_tokens += len(encoding.encode(str(t_val)))
            
            num_tokens += 2  # every reply is primed with <im_start>assistant
            
            # Apply conservative safety factors & flat formatting margins
            if tools:
                num_tokens = int(num_tokens * 1.08) + 1500
            else:
                num_tokens = int(num_tokens * 1.03) + 500
                
            return num_tokens
        except Exception as e:
            logger.warning(f"Error estimating tokens: {e}")
            # Crude fallback if tiktoken fails
            total_chars = 0
            for m in messages:
                content = getattr(m, "content", "")
                total_chars += len(str(content))
            if tools:
                for t in tools:
                    total_chars += len(str(t))
            estimated = total_chars // 4
            if tools:
                estimated = int(estimated * 1.08) + 1500
            else:
                estimated = int(estimated * 1.03) + 500
            return estimated

    def _prune_messages(self, messages: List[Any], tools: Optional[List[Any]] = None) -> List[Any]:
        """
        Prunes the message history sent to the LLM by:
        1. Truncating old and large tool outputs (ToolMessage) regardless of content type.
        2. Simplifying historical AIMessage tool calls to strip verbose schema params.
        3. Enforcing a sliding token window (history eviction) preserving system message,
           the last user query, and recent dialogue turns.
        """
        import copy
        
        pruned_messages = []
        for i, msg in enumerate(messages):
            is_system = msg.__class__.__name__ == "SystemMessage"
            is_last_human = (i == len(messages) - 1) and msg.__class__.__name__ == "HumanMessage"
            
            if is_system or is_last_human:
                pruned_messages.append(msg)
                continue
            
            # 1. Truncate ToolMessage outputs of any type
            if msg.__class__.__name__ == "ToolMessage":
                content_str = ""
                if isinstance(msg.content, str):
                    content_str = msg.content
                elif isinstance(msg.content, (list, dict)):
                    content_str = json.dumps(msg.content)
                else:
                    content_str = str(msg.content)

                # Preserve short messages and any message containing a sandbox path
                has_sandbox_path = "/sandbox/" in content_str
                if not has_sandbox_path and len(content_str) > 2000:
                    msg_copy = copy.deepcopy(msg)
                    msg_copy.content = f"[Tool Output Truncated ({len(content_str)} chars) - Snippet: {content_str[:500]}...]"
                    pruned_messages.append(msg_copy)
                    continue
            
            # 2. Simplify historical AIMessage tool call parameters
            is_assistant = msg.__class__.__name__ == "AIMessage"
            if is_assistant:
                # Eagerly strip huge file content parameter from write_file_to_sandbox tool calls in ALL assistant messages
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    has_write_sandbox = any(
                        isinstance(tc, dict) and tc.get("name") == "write_file_to_sandbox"
                        for tc in msg.tool_calls
                    )
                    if has_write_sandbox:
                        msg = copy.deepcopy(msg)
                        for tc in msg.tool_calls:
                            if isinstance(tc, dict) and tc.get("name") == "write_file_to_sandbox":
                                if "args" in tc and isinstance(tc["args"], dict) and "content" in tc["args"]:
                                    orig_content = tc["args"]["content"]
                                    if isinstance(orig_content, str):
                                        tc["args"]["content"] = f"[Omitted file content ({len(orig_content)} chars)]"

                # Keep recent assistant message intact if it's near the end (last 2 indices)
                is_recent_assistant = (i >= len(messages) - 2)
                if not is_recent_assistant and hasattr(msg, "tool_calls") and msg.tool_calls:
                    msg_copy = copy.deepcopy(msg)
                    new_tool_calls = []
                    for tc in msg_copy.tool_calls:
                        tc_copy = copy.deepcopy(tc)
                        if "args" in tc_copy and isinstance(tc_copy["args"], dict):
                            args = tc_copy["args"]
                            # Simplify 'prompt' if it's a nested dict
                            if "prompt" in args and isinstance(args["prompt"], dict):
                                prompt_dict = args["prompt"]
                                simplified_prompt = {}
                                if "high_level_description" in prompt_dict:
                                    simplified_prompt["high_level_description"] = prompt_dict["high_level_description"]
                                if "aspect_ratio" in prompt_dict:
                                    simplified_prompt["aspect_ratio"] = prompt_dict["aspect_ratio"]
                                tc_copy["args"]["prompt"] = simplified_prompt
                            
                            # Truncate other arguments if they are huge
                            for k, v in list(tc_copy["args"].items()):
                                if k != "prompt":
                                    v_str = str(v)
                                    if len(v_str) > 300:
                                        tc_copy["args"][k] = f"{v_str[:200]}... [Truncated]"
                        new_tool_calls.append(tc_copy)
                    msg_copy.tool_calls = new_tool_calls
                    pruned_messages.append(msg_copy)
                    continue
                
            pruned_messages.append(msg)
            
        # 3. Sliding Window Truncation (Token-Based History Eviction)
        current_tokens = self._estimate_tokens(pruned_messages, tools)
        target_limit = 32000
        
        system_msgs = [m for m in pruned_messages if m.__class__.__name__ == "SystemMessage"]
        other_msgs = [m for m in pruned_messages if m.__class__.__name__ != "SystemMessage"]
        
        # Evict from the beginning of other_msgs, keeping at least 4 messages (2 turns)
        while len(other_msgs) > 4 and current_tokens > target_limit:
            removed_msg = other_msgs.pop(0)
            logger.info(f"[Token Limiter] Evicted older message from history to fit context window: {removed_msg.__class__.__name__}")
            temp_messages = system_msgs + other_msgs
            current_tokens = self._estimate_tokens(temp_messages, tools)
            
        return system_msgs + other_msgs

    def _apply_token_limit_logic(self, messages: List[Any], kwargs: Dict[str, Any]) -> None:
        tools = kwargs.get("tools")
        input_tokens = self._estimate_tokens(messages, tools)
        logger.info(f"[Token Limiter] Estimated input tokens (pruned): {input_tokens}")
        
        # Max context limit config
        max_context = 128000
        if "qwen" in self.model_name.lower() or os.getenv("OPENAI_API_BASE"):
            max_context = 42000
            
        # Strip tools if context gets too high to force the agent to stop looping and summarize
        if input_tokens >= 35000:
            logger.warning(f"[Token Limiter] Input tokens ({input_tokens}) >= 35000. Stripping tools to force final response.")
            kwargs.pop("tools", None)
            kwargs.pop("tool_choice", None)
            # Re-estimate without tools
            input_tokens = self._estimate_tokens(messages, None)
            
        # Dynamically adjust max_tokens (output tokens) to avoid BadRequestError (400)
        requested_max = self.max_tokens or 4096
        remaining_window = max_context - input_tokens - 500 # 200 token safety margin
        if remaining_window <= 0:
            remaining_window = 100 # absolute minimum to try to get something
            
        if requested_max > remaining_window:
            logger.warning(f"[Token Limiter] Adjusting max_tokens from {requested_max} to {remaining_window} to fit context window.")
            kwargs["max_tokens"] = remaining_window

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = kwargs.get("tools")
        pruned = self._prune_messages(messages, tools)
        self._apply_token_limit_logic(pruned, kwargs)
        temp = active_temperature.get()
        if temp is not None:
            kwargs["temperature"] = temp
        return super()._generate(pruned, stop, run_manager, **kwargs)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = kwargs.get("tools")
        pruned = self._prune_messages(messages, tools)
        self._apply_token_limit_logic(pruned, kwargs)
        temp = active_temperature.get()
        if temp is not None:
            kwargs["temperature"] = temp
        return await super()._agenerate(pruned, stop, run_manager, **kwargs)

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        tools = kwargs.get("tools")
        pruned = self._prune_messages(messages, tools)
        self._apply_token_limit_logic(pruned, kwargs)
        temp = active_temperature.get()
        if temp is not None:
            kwargs["temperature"] = temp
        return super()._stream(pruned, stop, run_manager, **kwargs)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        tools = kwargs.get("tools")
        pruned = self._prune_messages(messages, tools)
        self._apply_token_limit_logic(pruned, kwargs)
        temp = active_temperature.get()
        if temp is not None:
            kwargs["temperature"] = temp
        async for chunk in super()._astream(pruned, stop, run_manager, **kwargs):
            yield chunk

agent_llm = TokenLimitingChatOpenAI(
    model=openai_model,
    openai_api_key=openai_api_key,
    openai_api_base=openai_api_base,
    temperature=0.3,
    max_tokens=4096
)

SYSTEM_PROMPT = """<identity_and_marketing_goal>
You are an elite, real-time Marketing and Brand Strategy Agent. Your goal is to coordinate multi-step creative generation pipelines, ingest user documents, align brand messaging with live cultural events, and trigger visual workflows.

</identity_and_marketing_goal>

<strategic_operational_rules>
1. Task Planning: For tasks requiring MORE than 3 tool calls, use the built-in `write_todos` tool to generate a sequential checklist. Skip this step for simple or single-step tasks.
   - Step 1: Browse trend/competitor context (via `internet_search`) or ingest briefs/scripts (via `read_user_document_tool`).
   - Step 2: Draft brand-aligned copy & visual briefs (saved directly to files using `write_file_to_sandbox`).
   - Step 3: Trigger ComfyUI workflow (`text_image`, `image_reference_and_text_to_image`, or `image_image`).
   Mark tasks as 'in_progress' and 'completed' as you progress.

2. Ephemeral Filesystem: You have access to a secure sandbox directory. To avoid token bloat, NEVER return raw visual briefs, competitor reports, or multi-platform caption drafts directly in the chat.
   - **For Markdown/Text**: Write them to disk using `write_file_to_sandbox` (e.g., `write_file_to_sandbox(filename="brief.md", content="...")`). Keep sandbox file contents concise and under 2000 words.
   - **For PDF Generation**: If the user requests a PDF, a formatted proposal, a professional campaign brief, copy sheet, or invoice, use the `generate_pdf_in_sandbox` tool. Specify the output filename (must end in `.pdf`) and the content in Markdown format.
   - **Embedding Images in PDFs**: You can and should embed generated images inside the PDF document. To do this, **you must generate the images first** (using `text_image` or other ComfyUI tools), retrieve the returned `/sandbox/...` image path, and then include it in the `content` of `generate_pdf_in_sandbox` using Markdown image syntax: `![Alt Text](/sandbox/...)`.
   - Suppress Preambles: To prevent output token limits from truncating your file writes, do NOT output any long preambles, thought paragraphs, or narration before calling file-saving tools. Immediately call the tool.
   - Chunked/Append Writing: If you need to write a large file (e.g. detailed campaign copy or documents over 1000 words / ~60 lines), you MUST write it sequentially in chunks. Call `write_file_to_sandbox` with `append=False` (default) for the first chunk, and then call it with `append=True` in subsequent steps for the remaining chunks.

3. Image Generation Tool Selection Criteria:
   Choose the appropriate generation tool based on the user's explicit intent:
   - **Absolute Reference Constraint**: If NO reference image is uploaded or available in the session history, you MUST ALWAYS use the `text_image` tool. Do NOT attempt to call `image_image` or `image_reference_and_text_to_image` without a valid reference or initial image.
   - Use `text_image` when generating an original image from scratch solely from a text description.
   - **Images containing written text**: When generating an image that requires specific written words, typography, signs, logos, or labels within the visual itself, try to use the `text_image` generator tool (as it uses the Ideogram model, which is optimized for readable text rendering).
   - Use `image_reference_and_text_to_image` when the user wants to generate a brand new image using a reference image as a guide for layout, composition, character pose, or style transfer (ControlNet/IP-Adapter style).
   - Use `image_image` when performing Image-to-Image (Img2Img) refinement (e.g. adding elements, changing background, or altering style/details of an existing generated image while keeping its overall content). Set `init_image` to the previously generated image's `/sandbox/...` path from history.
   - Use `mask_image_image` when the user has uploaded a masked image (which contains both the image and a transparency mask, indicated by `[Uploaded Masked Image: /sandbox/...]`) and wants to perform targeted inpainting/editing on the masked area. Set `image` to the masked image's `/sandbox/...` path.

4. Image Path Reporting — CRITICAL RULE: Every image generation tool (`text_image`, `image_reference_and_text_to_image`, `image_image`, `mask_image_image`) returns a tool observation that begins with `/sandbox/...`. This is the ONLY path you must report to the user. NEVER report the `asset_url`, `image_url`, or any URL from within the JSON body of the tool result — those are internal ComfyUI server URLs (e.g. `http://localhost:8188/view?filename=...` or `/output/...`) that the user cannot access. The tool observation starting with `/sandbox/` is the correct, user-accessible path. Always quote it verbatim.

5. Single-Shot & Sequential Generation:
   - When generating an image, you MUST define all requested visual elements (including typography, primary subjects, secondary details, and layout composition) in a single JSON prompt and trigger the generation workflow tool once. Do NOT call the generation or regeneration tools multiple times to build up the image iteratively one element at a time. Try your best to generate the image with ONE tool call only.
   - **Generate Images One by One**: If a task requires generating multiple distinct images, do NOT call the image generation tools in parallel or make multiple generation tool calls in a single turn. You must trigger each generation sequentially, waiting for the first image generation to complete and return its path before starting the next image generation.

6. Progress Updates: Before the FIRST tool call only, output a single brief sentence explaining your plan. Do not narrate every subsequent tool call — let the results speak for themselves.

7. Iterative Refinement Workflow: When the user asks for edits, adjustments, style modifications, or corrections to a previously generated image:
   - Locate the previously generated image's path (`/sandbox/...`) and its `[Asset ID: <id>]` in the conversation history.
   - Choose the best refinement workflow based on the request:
     a) **Adding elements, modifying details, or changing style of the existing image**: Call the `image_image` tool. Pass the previous image path as `init_image` and describe the additions/modifications in the `prompt`.
     b) **Generating a completely new image but using the previous layout/composition as a style guide**: Call the `image_reference_and_text_to_image` tool. Pass the previous image path as `reference_image` and describe the new prompt.
     c) **Deterministic settings tweak (re-running the exact same workflow with specific seed or parameter overrides)**: Call the `regenerate` tool. Pass the `asset_id` and specify the modifications in `param_overrides` (e.g. `param_overrides={"prompt": "updated text"}`).
     d) **Generating a completely different visual from scratch (ignoring the previous image's layout/content)**: Call the `text_image` tool with the new prompt.
     e) **Inpainting / Localized editing of a specific masked region**: Call the `mask_image_image` tool. Pass the masked image path (which has the transparency mask embedded in its alpha channel, indicated by `[Uploaded Masked Image: /sandbox/...]`) as `image` and describe the inpainting/editing instructions in the `prompt`.


8. Ideogram Safety Protocols (Safety Filter Avoidance):
   - Strict Noun Replacement: To prevent the "Image blocked by safety filter" error, NEVER use explicit clothing terms (e.g. "swimsuit", "underwear", "bikini") or sensitive physical descriptors in visual prompts. Instead, describe the situational environment and persona context (e.g., "enjoying a hot summer day at a luxury resort pool area", "athletic training in a modern fitness center") and let the model naturally infer context-appropriate attire.
   - Mandatory Bounding Boxes (Layout Anchoring): Every visual element, object, or text overlay in the compositional deconstruction MUST have explicit, non-overlapping `bbox` coordinates defined to anchor the layout and prevent visual overlaps that trigger safety filters. Crucially, coordinates MUST be specified on a 0-1000 scale (e.g., [100, 200, 900, 800]), NOT as 0-100 percentages (e.g., [10, 20, 90, 80]). WARNING: You MUST use the Y-first format [y1, x1, y2, x2]. DO NOT swap X and Y (e.g., do not write [x1, y1, x2, y2], which squishes horizontal layouts into vertical pillars and causes spelling glitches).
   - Isolate Text Coordinates: Bounding boxes for text overlays (`type: "text"`) must be strictly separated from backdrop/container objects (`type: "obj"`, such as buttons, badges, banners, or boxes) so they do not overlap. If text is meant to be placed 'on' or 'inside' a shape, do NOT overlap their bounding boxes; instead, allocate a separate, smaller bounding box for the text that sits entirely inside the container box with clean margins. They must not compete or fight for the same pixels, which causes visual artifacts and spelling corruption.

9. Ideogram Infographic & Layout Discipline: If generating an infographic, flowchart, or multi-item list/comparison (e.g., "benefits with icons and labels"), you MUST explicitly define **every single item, icon/graphic, shape, and text label** in the JSON `elements` list with its own individual bounding box. If the user request is high-level, you must still expand it into a detailed, fully deconstructed layout. You are strictly forbidden from writing a high-level description for a multi-item infographic but only defining a single element in the JSON, as this forces the renderer to hallucinate the remaining elements, resulting in gibberish text and graphics.
   - **Token-Budget Optimization (BBox & Element Limits)**: To prevent JSON truncation and LLM output token limit errors, you MUST:
     - **Limit Elements Count**: Limit the visual layout to a maximum of 6 elements per image (especially for infographics or split-screens).
     - **Concise Descriptions**: Keep each element's description concise and strictly under 40 words. Do not use overly descriptive micro-prose. This forces compact JSON output and avoids truncation failures.
</strategic_operational_rules>

<loop_prevention>
1. Tool Call Preference: Prefer fewer tool calls. Do not make tool calls unless they are strictly necessary to complete the task.
2. No Duplicate Searches: Never call `internet_search` with the same or semantically similar query more than once. If the first search did not return useful results, synthesize from what you have and move on.
3. No Verification Loops: After a tool completes successfully, do NOT call another tool to confirm or validate its result. Trust the output and proceed.
4. Fail Fast on Errors: If the same tool fails twice in a row, stop retrying. Report the failure to the user and ask for guidance.
5. No Idle Writes: Do not write intermediate thoughts, plans, or summaries to sandbox files unless they are a direct deliverable. Only write files that the user explicitly needs.
6. Scope Discipline: Only do what the user asked. Do not expand the task scope by researching adjacent topics, generating unrequested variations, or adding unsolicited deliverables.
7. No Visual Feedback Loops: You CANNOT see the generated images (you only receive a file path). Do NOT generate or regenerate images repeatedly in a loop to try to visually verify, tweak, or adjust the layout. Plan your coordinates mathematically, run the generation tool once, immediately return the best image path to the user, and wait for their feedback.
</loop_prevention>

<realtime_data_ingestion_guards>
1. Search-First Verification Mandate: Marketing strategies require flawless situational awareness. If a user asks about live public events, real-time sports updates, current trends, competitor status, or dates, your internal pre-training knowledge is insufficient. You are explicitly forbidden from guessing or stating an event has not occurred based on your data cutoff. You MUST invoke the `internet_search` tool first to ground your strategy in verified reality.
2. Objective Query Formulation: Formulate objective, highly precise search queries (e.g., 'Canada vs Qatar World Cup 2026 score') rather than passing open-ended creative concepts or conversational filler into the search pipeline.
3. Linear Tool-Chaining Workflow:
   - Step A: Parse the incoming user campaign or query for dynamic variables (e.g., current events, modern brands).
   - Step B: Execute a web search immediately to fetch the latest real-world payload.
   - Step C: Synthesize the freshly retrieved search facts.
   - Step D: Generate a marketing recommendation, ad copy, or data brief grounded strictly in that real-time data.
</realtime_data_ingestion_guards>

<hallucination_prevention>
Few-Shot Anchors:
- USER QUERY: "Draft a high-impact social media ad copy for Nike tying into the recent Canada vs Qatar match in the 2026 World Cup."
- INCORRECT MODE (HALLUCINATION & CUTOFF BIAS):
  "The World Cup 2026 has not happened yet because my pre-training data cutoff is earlier. However, if it were to happen, Nike could use generic messaging..." (Fails strategic grounding).
- CORRECT MODE (SEARCH-FIRST GROUNDING):
  1. Parse query: Dynamic 2026 sports event campaign hook.
  2. Call tool: `internet_search(query="Canada vs Qatar World Cup 2026 match result score")`
  3. Receive output: "Canada won a historic 6-0 victory over Qatar on June 18, 2026."
  4. Synthesize facts and output brand-grounded copy:
     "With Canada's historic 6-0 sweep over Qatar in the 2026 World Cup groups, the energy is unmatched. Ground your campaign in this momentum: [Drafting copy highlighting the 6-0 victory]..."

Error Handling:
- If a document file path is missing or unreadable, report the error state directly and guide the user on the correct workspace file path structure.
- If the search tool fails, explicitly report that real-time data retrieval failed. Do NOT fall back to training data. Instead, ask the user to clarify or retry.
- If write_file_to_sandbox returns an error, report the failure with the exact error message and do not assume the file was saved.
- JSON Truncation & Parsing Errors: If a JSON prompt fails to parse or throws a validation error during image generation tools execution, this is due to exceeding LLM output token limits (max_tokens). It is NOT a "path length limit" or "JSON length limit". You must immediately resolve it by simplifying the prompt, reducing the number of visual elements, and making descriptions more concise.
- Sandbox File Truncation: If your sandbox file writing is truncated, it is because you have hit the output token limit. If you need the full content of a large file to be written, immediately write the file in sequential chunks using `write_file_to_sandbox` with `append=True` for subsequent parts.
</hallucination_prevention>"""

logger = logging.getLogger("orchestrator")
logger.setLevel(logging.INFO)

from contextvars import ContextVar

# ContextVar to hold the active MCP session during agent run
active_mcp_session: ContextVar[Optional[ClientSession]] = ContextVar("active_mcp_session", default=None)

# ContextVar to hold the current session/thread_id for file organization
active_session_id: ContextVar[str] = ContextVar("active_session_id", default="default")

# ContextVar to hold the current agent temperature override
active_temperature: ContextVar[Optional[float]] = ContextVar("active_temperature", default=None)

# ContextVar to hold the unique words from user messages in the chat history
active_user_words: ContextVar[set] = ContextVar("active_user_words", default=set())

class AgentSessionProxy:
    """
    A proxy wrapper for the compiled agent that intercepts ainvoke, invoke,
    and astream_events calls to set the context-local MCP session and session_id.
    """
    def __init__(self, agent):
        self.agent = agent
        self.session = None
        self._session_id: str = "default"
        self.tone: Optional[str] = None

    def _extract_user_words(self, inputs) -> set:
        words = set()
        if inputs and "messages" in inputs and inputs["messages"]:
            for msg in inputs["messages"]:
                role = getattr(msg, "type", "")
                if not role:
                    role = msg.get("role", "") if isinstance(msg, dict) else ""
                if role in ("user", "human"):
                    content = getattr(msg, "content", "")
                    if not content and isinstance(msg, dict):
                        content = msg.get("content", "")
                    if isinstance(content, str):
                        import re
                        for w in re.findall(r'\b[a-zA-Z]{3,}\b', content.lower()):
                            words.add(w)
        return words

    def _inject_date_context(self, inputs):
        if not inputs or "messages" not in inputs or not inputs["messages"]:
            return inputs
            
        from datetime import datetime
        date_prefix = f"[System context: Today is {datetime.now().strftime('%B %d, %Y')}]\n\n"
        
        inputs_copy = dict(inputs)
        messages_copy = list(inputs_copy["messages"])
        first_msg = messages_copy[0]
        
        if hasattr(first_msg, "content"):
            if isinstance(first_msg.content, str):
                try:
                    # Create a new message copy to avoid modifying the in-memory object in place
                    messages_copy[0] = first_msg.__class__(
                        content=date_prefix + first_msg.content,
                        **{k: v for k, v in first_msg.__dict__.items() if k not in ("content", "type")}
                    )
                except Exception:
                    # Secondary fallback if dict attributes unpacking fails
                    messages_copy[0] = first_msg.__class__(
                        content=date_prefix + first_msg.content
                    )
        elif isinstance(first_msg, dict) and "content" in first_msg:
            if isinstance(first_msg["content"], str):
                messages_copy[0] = {
                    **first_msg,
                    "content": date_prefix + first_msg["content"]
                }
        elif isinstance(first_msg, str):
            messages_copy[0] = date_prefix + first_msg
            
        inputs_copy["messages"] = messages_copy
        return inputs_copy

    async def ainvoke(self, inputs, config=None, **kwargs):
        inputs = self._inject_date_context(inputs)
        token_mcp = active_mcp_session.set(self.session)
        token_sid = active_session_id.set(self._session_id or "default")
        token_words = active_user_words.set(self._extract_user_words(inputs))
        tone_map = {
            "Strict Coder": 0.3,
            "Professional": 0.6,
            "Creative": 0.9
        }
        temp = tone_map.get(getattr(self, "tone", "Creative") or "Creative", 0.9)
        token_temp = active_temperature.set(temp)
        try:
            return await self.agent.ainvoke(inputs, config, **kwargs)
        finally:
            active_mcp_session.reset(token_mcp)
            active_session_id.reset(token_sid)
            active_user_words.reset(token_words)
            active_temperature.reset(token_temp)

    async def invoke(self, inputs, config=None, **kwargs):
        inputs = self._inject_date_context(inputs)
        token_mcp = active_mcp_session.set(self.session)
        token_sid = active_session_id.set(self._session_id or "default")
        token_words = active_user_words.set(self._extract_user_words(inputs))
        tone_map = {
            "Strict Coder": 0.3,
            "Professional": 0.6,
            "Creative": 0.9
        }
        temp = tone_map.get(getattr(self, "tone", "Creative") or "Creative", 0.9)
        token_temp = active_temperature.set(temp)
        try:
            return await self.agent.invoke(inputs, config, **kwargs)
        finally:
            active_mcp_session.reset(token_mcp)
            active_session_id.reset(token_sid)
            active_user_words.reset(token_words)
            active_temperature.reset(token_temp)

    async def astream_events(self, inputs, config=None, **kwargs):
        """Proxy astream_events while ensuring the MCP session context var is set."""
        inputs = self._inject_date_context(inputs)
        # Extract thread_id from config to set session_id
        sid = "default"
        if config and isinstance(config, dict):
            sid = config.get("configurable", {}).get("thread_id", "default")
        token_mcp = active_mcp_session.set(self.session)
        token_sid = active_session_id.set(sid)
        token_words = active_user_words.set(self._extract_user_words(inputs))
        tone_map = {
            "Strict Coder": 0.3,
            "Professional": 0.6,
            "Creative": 0.9
        }
        temp = tone_map.get(getattr(self, "tone", "Creative") or "Creative", 0.9)
        token_temp = active_temperature.set(temp)
        try:
            async for event in self.agent.astream_events(inputs, config=config, **kwargs):
                yield event
        finally:
            active_mcp_session.reset(token_mcp)
            active_session_id.reset(token_sid)
            active_user_words.reset(token_words)
            active_temperature.reset(token_temp)

    def __getattr__(self, name):
        return getattr(self.agent, name)


# Keep cached agent reference
_cached_agent = None

def connect_to_mcp_server():
    """
    Connects to the MCP server.
    First tries Streamable HTTP (using environment variable MCP_SERVER_URL or http://127.0.0.1:9000/mcp).
    If that fails, falls back to starting the server in a subprocess via stdio.
    """
    mcp_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:9000/mcp")
    
    # Check if HTTP server is running (quick socket connect to avoid timeout)
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        # Extract host and port
        port = 9000
        if "127.0.0.1:" in mcp_url:
            port = int(mcp_url.split("127.0.0.1:")[1].split("/")[0])
        elif "localhost:" in mcp_url:
            port = int(mcp_url.split("localhost:")[1].split("/")[0])
        s.connect(("127.0.0.1", port))
        s.close()
        logger.info(f"Connecting to MCP server via Streamable HTTP at {mcp_url}")
        return streamablehttp_client(mcp_url)
    except Exception:
        logger.warning("Could not connect to MCP server via Streamable HTTP. Falling back to stdio.")

    # Fallback to stdio command line
    server_script = os.getenv("MCP_SERVER_SCRIPT", "/Users/adamdali/Documents/AI_Agent_MR/comfyui-mcp-server/server.py")
    
    # Dynamically locate the python interpreter inside the comfyui-mcp-server's virtual environment
    mcp_dir = os.path.dirname(server_script)
    venv_python = os.path.join(mcp_dir, ".venv", "bin", "python")
    
    # Fallback if venv python doesn't exist
    if not os.path.exists(venv_python):
        venv_python = "python3"
        
    server_params = StdioServerParameters(
        command=venv_python,
        args=[server_script, "--stdio"],
        env=os.environ.copy()
    )
    logger.info(f"Starting MCP server via stdio using python at {venv_python} and script {server_script}")
    return stdio_client(server_params)

def mcp_tool_to_langchain(mcp_tool):
    tool_name = mcp_tool.name
    tool_desc = mcp_tool.description
    input_schema = mcp_tool.inputSchema
    
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    fields = {}
    for param_name, param_schema in properties.items():
        param_type = param_schema.get("type")
        param_desc = param_schema.get("description", "")
        default = param_schema.get("default")
        
        if param_name == "prompt" and tool_name in ("text_image", "image_reference_and_text_to_image"):
            py_type = IdeogramPrompt
        elif param_type == "string":
            py_type = str
        elif param_type == "integer":
            py_type = int
        elif param_type == "number":
            py_type = float
        elif param_type == "boolean":
            py_type = bool
        else:
            py_type = Any
            
        if param_name in required:
            fields[param_name] = (py_type, Field(description=param_desc))
        else:
            fields[param_name] = (Optional[py_type], Field(default=default, description=param_desc))
            
    args_schema = create_model(f"{tool_name}Args", **fields)
    
    async def _run_tool(**kwargs):
        # 1. Pre-flight path resolution (Directive 2.2)
        resolved_kwargs = {}
        shared_root = str(BASE_WORKSPACE)
        
        for k, v in kwargs.items():
            if isinstance(v, str) and v.startswith("/workspace/"):
                filename = v.replace("/workspace/", "", 1)
                resolved_path = os.path.abspath(os.path.join(shared_root, filename))
                resolved_kwargs[k] = resolved_path
                logger.info(f"Resolved path for parameter '{k}': {v} -> {resolved_path}")
            elif isinstance(v, str) and v.startswith("/sandbox/"):
                filename = v.replace("/sandbox/", "", 1)
                resolved_path = os.path.abspath(os.path.join(shared_root, filename))
                resolved_kwargs[k] = resolved_path
                logger.info(f"Resolved path for parameter '{k}': {v} -> {resolved_path}")
            else:
                resolved_kwargs[k] = v
                
        # Resolve session_id "current" to active session ID
        if "session_id" in resolved_kwargs and resolved_kwargs["session_id"] == "current":
            resolved_kwargs["session_id"] = active_session_id.get()

        # Inject session_id if the tool schema accepts it and it is not already provided
        session_id = active_session_id.get()
        if session_id and "session_id" in args_schema.model_fields and "session_id" not in resolved_kwargs:
            resolved_kwargs["session_id"] = session_id

        # 2. Invoke MCP Tool
        session = active_mcp_session.get()
        if not session:
            raise RuntimeError("No active MCP session found in context.")
            
        logger.info(f"Calling MCP tool '{tool_name}' with args {resolved_kwargs}")
        result = await session.call_tool(tool_name, resolved_kwargs)
        
        if result.isError:
            raise ValueError(f"MCP tool error: {result.content}")
            
        # Parse output content list
        text_val = ""
        for content_item in result.content:
            if content_item.type == "text":
                text_val += content_item.text

        # 3. Response adapter — download generated image from ComfyUI and store under session folder
        if text_val.strip().startswith("{"):
            try:
                data = json.loads(text_val)
                if isinstance(data, dict):
                    filename = data.get("filename")

                    if filename:
                        # Prefer the fully-formed asset_url returned by the MCP tool;
                        # fall back to manually constructing the view URL.
                        asset_url = data.get("asset_url", "")
                        if asset_url and asset_url.startswith("http"):
                            view_url = asset_url
                        else:
                            subfolder = data.get("subfolder", "")
                            folder_type = data.get("folder_type", "output")
                            comfy_url = os.getenv("COMFYUI_URL", "http://localhost:8188").rstrip("/")
                            view_url = f"{comfy_url}/view?filename={filename}&subfolder={subfolder}&type={folder_type}"

                        # Determine output extension from mime_type or filename
                        mime_type = data.get("mime_type", "image/png")
                        ext_map = {
                            "image/png": ".png",
                            "image/jpeg": ".jpg",
                            "image/jpg": ".jpg",
                            "image/webp": ".webp",
                            "image/gif": ".gif",
                            "video/mp4": ".mp4",
                            "audio/mpeg": ".mp3",
                            "audio/wav": ".wav",
                        }
                        ext = ext_map.get(mime_type, os.path.splitext(filename)[1] or ".png")

                        # Save to gen-content/{session_id}/images/
                        base_workspace = str(BASE_WORKSPACE)
                        session_id = active_session_id.get()
                        session_output_dir = os.path.join(base_workspace, session_id, "images")
                        os.makedirs(session_output_dir, exist_ok=True)
                        asset_id = data.get("asset_id", "unknown")
                        output_filename = f"generated_{asset_id}{ext}"
                        output_path = os.path.join(session_output_dir, output_filename)

                        logger.info(f"Downloading generated image asset for {tool_name} from {view_url} to {output_path}...")
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            resp = await client.get(view_url)
                            if resp.status_code == 200:
                                with open(output_path, "wb") as f:
                                    f.write(resp.content)
                                if os.path.exists(output_path):
                                    logger.info(f"Successfully saved generated image asset to {output_path}")
                                    return f"/sandbox/{session_id}/images/{output_filename}\n\n[Asset ID: {asset_id}]"
                            else:
                                logger.error(f"Failed to download generated image. Status: {resp.status_code}, URL: {view_url}")
            except Exception as e:
                logger.error(f"Error executing response adapter for {tool_name}: {e}", exc_info=True)
        return text_val

    return StructuredTool.from_function(
        coroutine=_run_tool,
        name=tool_name,
        description=tool_desc,
        args_schema=args_schema
    )

async def get_marketing_agent(session: ClientSession, session_id: str = "default", tone: Optional[str] = None):
    """
    Dynamically discover, list, and register tools exposed by the MCP server,
    compiling the Deep Agent with dynamic tools and local utilities.
    """
    global _cached_agent
    if _cached_agent is not None:
        _cached_agent.session = session
        _cached_agent._session_id = session_id
        _cached_agent.tone = tone
        return _cached_agent
        
    logger.info("Discovering tools from ComfyUI MCP Server...")
    mcp_tools_list = await session.list_tools()
    
    # Convert MCP tools to LangChain tools (excluding view_image and read_user_document to prevent conflicts)
    lc_mcp_tools = [mcp_tool_to_langchain(t) for t in mcp_tools_list.tools if t.name not in ("view_image", "read_user_document")]
    logger.info(f"Registered {len(lc_mcp_tools)} tools from MCP server dynamically: {[t.name for t in lc_mcp_tools]}")
    
    # Combine with local backend tools
    all_tools = [
        internet_search,
        write_file_to_sandbox,
        read_user_document_tool,
        generate_pdf_in_sandbox
    ] + lc_mcp_tools
    
    import shutil
    # Copy skills folder to the ephemeral workspace directory so SkillsMiddleware can load them via the backend
    src_skills = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "skills")
    dst_skills = os.path.join(workspace_dir, "skills")
    if os.path.exists(src_skills):
        shutil.copytree(src_skills, dst_skills, dirs_exist_ok=True)
        logger.info(f"Copied agent skills from {src_skills} to {dst_skills}")
    else:
        logger.warning(f"Skills source folder not found at {src_skills}")

    raw_agent = create_deep_agent(
        model=agent_llm,
        tools=all_tools,
        backend=backend,
        system_prompt=SYSTEM_PROMPT,
        skills=["/workspace/skills"]
    )
    _cached_agent = AgentSessionProxy(raw_agent)
    _cached_agent.session = session
    _cached_agent._session_id = session_id
    _cached_agent.tone = tone
    return _cached_agent
