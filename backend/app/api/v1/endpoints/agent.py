import uuid
import os
import shutil
import logging
import socket
import json
import asyncio
from typing import Any, Optional, AsyncGenerator
from fastapi import APIRouter, Depends, BackgroundTasks, status, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.agent.orchestrator import get_marketing_agent, connect_to_mcp_server, connect_to_all_mcp_servers
from app.agent.comfy_router import WorkspaceManager
from mcp import ClientSession
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.chat import create_message
from app.schemas.chat import ChatMessageCreate
# pyrefly: ignore [missing-import]
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from PIL import Image, ImageOps
import hashlib

router = APIRouter()
logger = logging.getLogger("agent_api")


def get_file_hash(path: str) -> str:
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def merge_image_and_mask(original_path: str, mask_path: str, output_path: str):
    """
    Merge original image and mask image into an RGBA PNG.
    In the output alpha channel:
      - Masked (painted) pixels (where mask is white/255) become transparent (alpha = 0).
      - Unmasked (unpainted) pixels (where mask is black/0) remain opaque (alpha = 255).
    """
    orig_img = Image.open(original_path).convert("RGB")
    mask_img = Image.open(mask_path).convert("L")
    
    if mask_img.size != orig_img.size:
        mask_img = mask_img.resize(orig_img.size, Image.Resampling.BILINEAR)
        
    alpha_channel = ImageOps.invert(mask_img)
    
    rgba_img = orig_img.copy()
    rgba_img.putalpha(alpha_channel)
    rgba_img.save(output_path, "PNG")



def _sse(event: str, data: Any) -> str:
    """Format a Server-Sent Event string."""
    payload = json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


class CampaignRequest(BaseModel):
    prompt: str
    thread_id: str

@router.post("/campaign", status_code=status.HTTP_202_ACCEPTED)
async def trigger_marketing_campaign(
    request: CampaignRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Trigger the multi-step marketing agent in the background for campaign execution."""
    
    async def run_agent_workflow():
        config = {"configurable": {"thread_id": request.thread_id}}
        inputs = {"messages": [{"role": "user", "content": request.prompt}]}
        
        # Connect to all configured MCP servers, dynamically compile agent, and run
        async with connect_to_all_mcp_servers() as sessions:
            agent = await get_marketing_agent(sessions, session_id=request.thread_id)  # type: ignore
            await agent.ainvoke(inputs, config=config)

    background_tasks.add_task(run_agent_workflow)
    
    return {
        "status": "accepted",
        "thread_id": request.thread_id,
        "message": "Marketing AI Agent campaign triggered successfully in background."
    }


@router.post("/chat")
async def chat_with_agent(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streaming chat endpoint. Returns a text/event-stream SSE response.
    Events emitted: agent_thought, tool_start, tool_end, agent_message, error, done.
    Supports both JSON and Multipart Form Data (for uploading images/documents).
    Saves files to the workspace, registers user message, runs agent, saves agent messages.
    """
    content_type = request.headers.get("content-type", "")
    
    prompt = ""
    session_id_str = ""
    tone = None
    image_filename = None
    image2_filename = None
    doc_filename = None
    is_masked = False
    
    shared_root = os.getenv("SHARED_WORKSPACE_ROOT", "/Users/adamdali/Documents/AI_Agent_MR/gen-content")
    os.makedirs(shared_root, exist_ok=True)
    
    if "multipart/form-data" in content_type:
        form = await request.form()
        prompt = str(form.get("prompt", ""))
        session_id_str = str(form.get("session_id", ""))
        tone = form.get("tone")
        if tone:
            tone = str(tone)
            
        temp_workspace = WorkspaceManager.get_workspace_dir()
        
        # Thread directory for keeping uploads isolated per chat session
        thread_dir = os.path.join(shared_root, session_id_str)
        os.makedirs(thread_dir, exist_ok=True)

        image_file = form.get("image")
        image2_file = form.get("image2")
        mask_file = form.get("mask")
        
        if image_file and hasattr(image_file, "filename") and image_file.filename:
            image_filename = image_file.filename
            image_path = os.path.join(thread_dir, image_filename)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            logger.info(f"Saved uploaded image to {image_path}")
            
            # Copy base image to temp workspace
            try:
                temp_image_path = os.path.join(temp_workspace, image_filename)
                shutil.copy2(image_path, temp_image_path)
                logger.info(f"Copied uploaded image to temp workspace: {temp_image_path}")
            except Exception as e:
                logger.warning(f"Could not copy image to temp workspace: {e}")
                
            # If mask is also uploaded, save and merge
            if mask_file and hasattr(mask_file, "filename") and mask_file.filename:
                mask_filename = mask_file.filename
                mask_path = os.path.join(thread_dir, f"mask_{mask_filename}")
                with open(mask_path, "wb") as buffer:
                    shutil.copyfileobj(mask_file.file, buffer)
                logger.info(f"Saved uploaded mask to {mask_path}")
                
                # Merge original image and mask image into an RGBA PNG
                merged_filename = f"masked_{os.path.splitext(image_filename)[0]}.png"
                merged_path = os.path.join(thread_dir, merged_filename)
                try:
                    merge_image_and_mask(image_path, mask_path, merged_path)
                    logger.info(f"Successfully merged image and mask to {merged_path}")
                    
                    # Switch to using merged image
                    image_filename = merged_filename
                    image_path = merged_path
                    is_masked = True
                    
                    # Copy merged image to temp workspace
                    temp_image_path = os.path.join(temp_workspace, image_filename)
                    shutil.copy2(image_path, temp_image_path)
                    logger.info(f"Copied merged image to temp workspace: {temp_image_path}")
                except Exception as merge_err:
                    logger.error(f"Failed to merge image and mask: {merge_err}")

        if image2_file and hasattr(image2_file, "filename") and image2_file.filename:
            image2_filename = image2_file.filename
            image2_path = os.path.join(thread_dir, image2_filename)
            with open(image2_path, "wb") as buffer:
                shutil.copyfileobj(image2_file.file, buffer)
            logger.info(f"Saved uploaded image2 to {image2_path}")
            
            # Copy to temp workspace
            try:
                temp_image2_path = os.path.join(temp_workspace, image2_filename)
                shutil.copy2(image2_path, temp_image2_path)
                logger.info(f"Copied uploaded image2 to temp workspace: {temp_image2_path}")
            except Exception as e:
                logger.warning(f"Could not copy image2 to temp workspace: {e}")
            
        doc_file = form.get("document")
        if doc_file and hasattr(doc_file, "filename") and doc_file.filename:
            doc_filename = doc_file.filename
            doc_path = os.path.join(thread_dir, doc_filename)
            with open(doc_path, "wb") as buffer:
                shutil.copyfileobj(doc_file.file, buffer)
            logger.info(f"Saved uploaded document to {doc_path}")
            
            # Copy to temp workspace dir so local tools can resolve it via /workspace/
            try:
                temp_doc_path = os.path.join(temp_workspace, doc_filename)
                shutil.copy2(doc_path, temp_doc_path)
                logger.info(f"Copied uploaded document to temp workspace: {temp_doc_path}")
            except Exception as e:
                logger.warning(f"Could not copy document to temp workspace: {e}")
    else:
        # JSON Payload
        body = await request.json()
        prompt = body.get("prompt", "")
        session_id_str = body.get("session_id", "")
        tone = body.get("tone")
        
    if not prompt or not session_id_str:
        return {"error": "Missing prompt or session_id"}
        
    try:
        session_id = uuid.UUID(session_id_str)
    except ValueError:
        return {"error": "Invalid session_id UUID format"}
  
    # Formulate custom prompt explaining file locations to the agent if they were uploaded
    custom_prompt = prompt
    if image_filename and image2_filename:
        custom_prompt = (
            f"[Uploaded Reference Image 1: /sandbox/{session_id_str}/{image_filename}]\n"
            f"[Uploaded Reference Image 2: /sandbox/{session_id_str}/{image2_filename}]\n"
            + custom_prompt
        )
    elif image_filename:
        if is_masked:
            custom_prompt = f"[Uploaded Masked Image: /sandbox/{session_id_str}/{image_filename}]\n" + custom_prompt
        else:
            custom_prompt = f"[Uploaded Reference Image: /sandbox/{session_id_str}/{image_filename}]\n" + custom_prompt
    if doc_filename:
        custom_prompt = f"[Uploaded Document: /sandbox/{session_id_str}/{doc_filename}]\n" + custom_prompt

    # 1. Save user message to database
    meta = {}
    if tone:
        meta["tone"] = tone
    if image_filename:
        meta["image_path"] = f"/sandbox/{session_id_str}/{image_filename}"
    if image2_filename:
        meta["image2_path"] = f"/sandbox/{session_id_str}/{image2_filename}"
    if doc_filename:
        meta["doc_path"] = f"/sandbox/{session_id_str}/{doc_filename}"
        meta["doc_name"] = doc_filename

    user_msg_in = ChatMessageCreate(
        role="user",
        content={"text": prompt},
        meta_data=meta if meta else None
    )
    await create_message(db, session_id=session_id, message_in=user_msg_in)
    
    # 2. Load conversation history for this specific thread/session from database
    from app.crud.chat import get_messages_by_session
    db_messages = await get_messages_by_session(db, session_id=session_id)
    
    # Map database messages to LangChain messages for graph state initialization
    formatted_messages = []
    for idx, db_msg in enumerate(db_messages):
        role = db_msg.role
        content = db_msg.content
        
        msg_content = ""
        if isinstance(content, dict):
            if "text" in content:
                msg_content = content["text"]
            elif "parts" in content:
                msg_content = content["parts"]
            else:
                msg_content = str(content)
        else:
            msg_content = str(content)
            
        # For the last message (which is the user query we just saved), replace content with custom_prompt to preserve upload details
        if idx == len(db_messages) - 1 and role == "user":
            msg_content = custom_prompt
            
        if role == "user":
            formatted_messages.append(HumanMessage(content=msg_content))
        elif role == "assistant":
            # Extract tool calls if any
            tool_calls = []
            if isinstance(content, dict) and "tool_calls" in content:
                import copy
                tool_calls = copy.deepcopy(content["tool_calls"])
                for tc in tool_calls:
                    if isinstance(tc, dict) and "id" not in tc:
                        tc["id"] = f"call_{uuid.uuid4().hex[:8]}"
            formatted_messages.append(AIMessage(content=msg_content, tool_calls=tool_calls))
        elif role == "tool":
            tool_name = (db_msg.meta_data or {}).get("tool_name") or "unknown"
            tool_call_id = (db_msg.meta_data or {}).get("tool_call_id") or "call_dummy"
            formatted_messages.append(ToolMessage(content=msg_content, name=tool_name, tool_call_id=tool_call_id))

    # 3. Build agent invocation config
    config = {
        "configurable": {"thread_id": str(session_id)},
        "recursion_limit": 90
    }
    inputs = {"messages": formatted_messages}

    async def event_generator() -> AsyncGenerator[str, None]:
        """Stream agent events as SSE to the client."""
        accumulated_ai_text = ""
        all_new_messages = []

        try:
            async with connect_to_all_mcp_servers() as sessions:
                agent = await get_marketing_agent(sessions, session_id=session_id_str, tone=tone)  # type: ignore

                # Stream events from the agent using LangGraph's astream_events v2
                async for event in agent.astream_events(inputs, config=config, version="v2"):
                    kind = event.get("event", "")
                    
                    # ── Agent thinking / intermediate text token ──
                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content"):
                            text_delta = ""
                            if isinstance(chunk.content, str):
                                text_delta = chunk.content
                            elif isinstance(chunk.content, list):
                                for part in chunk.content:
                                    if isinstance(part, dict) and part.get("type") == "text":
                                        text_delta += part.get("text", "")
                            if text_delta:
                                accumulated_ai_text += text_delta
                                yield _sse("agent_thought", {"delta": text_delta})

                    # ── Tool about to be called ──
                    elif kind == "on_tool_start":
                        tool_name = event.get("name", "unknown_tool")
                        tool_input = event.get("data", {}).get("input", {})
                        logger.info(f"[Stream] Tool starting: {tool_name}")
                        yield _sse("tool_start", {
                            "tool": tool_name,
                            "input": tool_input,
                        })

                    # ── Tool call finished ──
                    elif kind == "on_tool_end":
                        tool_name = event.get("name", "unknown_tool")
                        tool_output = event.get("data", {}).get("output", "")
                        # Trim long outputs to keep SSE payload small
                        output_str = str(tool_output)
                        if len(output_str) > 400:
                            output_str = output_str[:400] + "…"
                        logger.info(f"[Stream] Tool finished: {tool_name}")
                        yield _sse("tool_end", {
                            "tool": tool_name,
                            "output": output_str,
                        })

                    # ── Final model output (complete message) ──
                    elif kind == "on_chain_end" and not event.get("parent_ids"):
                        output = event.get("data", {}).get("output")
                        if isinstance(output, dict):
                            all_new_messages = output.get("messages", [])

            # ── Persist all new messages to the DB ──
            saved_msgs = []
            initial_msg_count = len(formatted_messages)
            for msg in all_new_messages[initial_msg_count:]:
                role = "assistant"
                if msg.__class__.__name__ == "ToolMessage":
                    role = "tool"
                elif msg.__class__.__name__ == "HumanMessage":
                    role = "user"

                content_dict = {}
                if isinstance(msg.content, str):
                    content_dict = {"text": msg.content}
                elif isinstance(msg.content, list):
                    content_dict = {"parts": msg.content}

                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    content_dict["tool_calls"] = msg.tool_calls

                meta = {"tone": tone} if tone else {}
                if role == "tool":
                    tool_name_attr = getattr(msg, "name", None)
                    if tool_name_attr:
                        meta["tool_name"] = tool_name_attr
                    tool_call_id_attr = getattr(msg, "tool_call_id", None)
                    if tool_call_id_attr:
                        meta["tool_call_id"] = tool_call_id_attr

                msg_in = ChatMessageCreate(
                    role=role,
                    content=content_dict,
                    meta_data=meta if meta else None
                )
                db_msg = await create_message(db, session_id=session_id, message_in=msg_in)
                saved_msgs.append(db_msg)

            # Find and emit the final assistant text message
            final_text = ""
            for msg in reversed(all_new_messages):
                if msg.__class__.__name__ == "AIMessage":
                    if isinstance(msg.content, str) and msg.content.strip():
                        final_text = msg.content
                        break
                    elif isinstance(msg.content, list):
                        for part in msg.content:
                            if isinstance(part, dict) and part.get("type") == "text" and part.get("text", "").strip():
                                final_text = part["text"]
                                break
                    if final_text:
                        break

            # Emit the complete agent_message event with the final response
            if final_text:
                yield _sse("agent_message", {"text": final_text, "session_id": session_id_str})
            elif accumulated_ai_text:
                yield _sse("agent_message", {"text": accumulated_ai_text, "session_id": session_id_str})

            yield _sse("done", {"session_id": session_id_str})

        except Exception as e:
            logger.error(f"Agent stream failed: {e}", exc_info=True)
            # Persist the error as an assistant message
            try:
                err_msg_in = ChatMessageCreate(
                    role="assistant",
                    content={"text": f"Error: {str(e)}"},
                    meta_data=None
                )
                await create_message(db, session_id=session_id, message_in=err_msg_in)
            except Exception:
                pass
            yield _sse("error", {"message": str(e)})
            yield _sse("done", {"session_id": session_id_str})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@router.post("/upload/mask")
async def upload_mask(
    image: UploadFile = File(...),
    original_ref: str = Form(...),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Upload a mask image to be applied to an existing original image.
    Merges original and mask into an RGBA PNG and uploads to ComfyUI.
    """
    shared_root = os.getenv("SHARED_WORKSPACE_ROOT", "/Users/adamdali/Documents/AI_Agent_MR/gen-content")
    temp_workspace = WorkspaceManager.get_workspace_dir()
    
    session_id_str = ""
    original_filename = ""
    
    # Try parsing original_ref as JSON
    try:
        ref_data = json.loads(original_ref)
        if isinstance(ref_data, dict):
            session_id_str = ref_data.get("session_id", "")
            original_filename = ref_data.get("filename", "")
    except Exception:
        # Fallback to parsing path-like strings
        if "/" in original_ref:
            parts = original_ref.strip("/").split("/")
            if len(parts) >= 2:
                session_id_str = parts[-2]
                original_filename = parts[-1]
                
    if not session_id_str or not original_filename:
        # Fallback to extracting just filename if no session_id found
        original_filename = os.path.basename(original_ref)
        
    thread_dir = os.path.join(shared_root, session_id_str)
    os.makedirs(thread_dir, exist_ok=True)
    
    original_path = os.path.join(thread_dir, original_filename)
    # If not in thread_dir, check in temp_workspace
    if not os.path.exists(original_path):
        original_path = os.path.join(temp_workspace, original_filename)
        
    if not os.path.exists(original_path):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Original image '{original_filename}' not found on server."
        )
        
    # Save the mask image
    mask_filename = image.filename or f"mask_{uuid.uuid4().hex[:8]}.png"
    mask_path = os.path.join(thread_dir, f"mask_{mask_filename}")
    with open(mask_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    # Merge original image and mask image into an RGBA PNG
    merged_filename = f"masked_{os.path.splitext(original_filename)[0]}.png"
    merged_path = os.path.join(thread_dir, merged_filename)
    
    try:
        merge_image_and_mask(original_path, mask_path, merged_path)
        logger.info(f"Merged mask to {merged_path}")
        
        # Copy to temp workspace dir so local tools can resolve it via /workspace/
        temp_image_path = os.path.join(temp_workspace, merged_filename)
        shutil.copy2(merged_path, temp_image_path)
        logger.info(f"Copied merged image to temp workspace: {temp_image_path}")
    except Exception as e:
        from fastapi import HTTPException
        logger.error(f"Failed to merge image and mask: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error merging mask: {str(e)}"
        )
        
    # Calculate hashes for metadata
    original_hash = get_file_hash(original_path)
    mask_hash = get_file_hash(mask_path)
    
    return {
        "name": mask_filename,
        "subfolder": "",
        "type": "input",
        "metadata": {
            "is_mask": True,
            "original_hash": original_hash,
            "mask_type": "painted_masked",
            "related_files": {
                "mask": mask_hash,
                "paint": "none",
                "painted": merged_filename
            }
        }
    }


@router.get("/status")
async def get_service_status() -> Any:
    """Check the health status of Layer 1 dependencies (FastAPI, MCP Server, ComfyUI)."""
    from urllib.parse import urlparse
    mcp_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:9000/mcp")
    comfy_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
    
    mcp_status = "offline"
    comfy_status = "offline"
    
    # Check MCP Server
    try:
        parsed_mcp = urlparse(mcp_url)
        mcp_host = parsed_mcp.hostname or "127.0.0.1"
        mcp_port = parsed_mcp.port or (443 if parsed_mcp.scheme == "https" else 80)
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        s.connect((mcp_host, mcp_port))
        s.close()
        mcp_status = "online"
    except Exception:
        pass
        
    # Check ComfyUI
    try:
        parsed_comfy = urlparse(comfy_url)
        comfy_host = parsed_comfy.hostname or "localhost"
        comfy_port = parsed_comfy.port or (443 if parsed_comfy.scheme == "https" else 80)
        
        # Quick check using socket first to avoid HTTP timeout delay
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        s.connect((comfy_host, comfy_port))
        s.close()
        comfy_status = "online"
    except Exception:
        pass
        
    return {
        "fastapi": "online",
        "mcp_server": mcp_status,
        "comfyui": comfy_status
    }
