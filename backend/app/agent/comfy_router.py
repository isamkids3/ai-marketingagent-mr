import os
import httpx
import logging
import asyncio
import tempfile
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("comfy_router")
logger.setLevel(logging.INFO)

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
BASE_WORKSPACE = os.path.abspath(
    os.getenv("SHARED_WORKSPACE_ROOT", "/Users/adamdali/Documents/MilleniumRadius/gen-content")
)


class WorkspaceManager:
    """Manages the mapping of virtual /workspace/ paths to the actual temp directories."""
    _workspace_dir: Optional[str] = None

    @classmethod
    def set_workspace_dir(cls, path: str) -> None:
        cls._workspace_dir = path
        logger.info(f"Workspace directory set to: {path}")

    @classmethod
    def get_workspace_dir(cls) -> str:
        if cls._workspace_dir is None:
            # Fallback to system temp directory
            cls._workspace_dir = tempfile.gettempdir()
        return cls._workspace_dir


def resolve_local_path(virtual_path: str) -> str:
    """Resolves a virtual workspace path to a physical filesystem path."""
    if not virtual_path:
        return ""
    if virtual_path.startswith("/workspace/"):
        relative_path = virtual_path.replace("/workspace/", "", 1)
        return os.path.abspath(os.path.join(WorkspaceManager.get_workspace_dir(), relative_path))
    if virtual_path.startswith("/sandbox/"):
        relative_path = virtual_path.replace("/sandbox/", "", 1)
        shared_root = os.getenv("SHARED_WORKSPACE_ROOT", "/Users/adamdali/Documents/MilleniumRadius/gen-content")
        return os.path.abspath(os.path.join(shared_root, relative_path))
    return os.path.abspath(virtual_path)


class ComfyUIWorkflowRouter:
    """
    Handles translation of agent tool inputs into ComfyUI API JSON payloads,
    manages image uploads, triggers execution, and saves output to the FastAPI static folder.
    """

    def __init__(self, base_url: str = COMFYUI_URL, base_workspace: str = BASE_WORKSPACE):
        self.base_url = base_url.rstrip("/")
        self.base_workspace = base_workspace

    async def check_health(self) -> bool:
        """Checks if the ComfyUI API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/system-info")
                return response.status_code == 200
        except Exception:
            return False

    async def upload_image(self, local_path: str) -> Optional[str]:
        """
        Uploads a local image file to ComfyUI.
        Returns the filename used by ComfyUI, or None if the upload failed.
        """
        resolved_path = resolve_local_path(local_path)
        if not os.path.exists(resolved_path):
            logger.error(f"Image upload failed: file does not exist at {resolved_path}")
            return None

        try:
            filename = os.path.basename(resolved_path)
            async with httpx.AsyncClient(timeout=10.0) as client:
                with open(resolved_path, "rb") as f:
                    files = {"image": (filename, f, "image/png")}
                    response = await client.post(f"{self.base_url}/upload/image", files=files)
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return data.get("name")
                else:
                    logger.error(f"ComfyUI upload returned status {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to upload image {resolved_path} to ComfyUI: {e}")
            return None

    def get_aspect_ratio_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        """Maps standard aspect ratio strings to target SDXL resolutions."""
        ratios = {
            "1:1": (1024, 1024),
            "16:9": (1344, 768),
            "9:16": (768, 1344),
            "4:3": (1152, 896),
            "3:4": (896, 1152),
        }
        return ratios.get(aspect_ratio, (1024, 1024))

    def build_text_to_image_payload(self, prompt: str, aspect_ratio: str) -> Dict[str, Any]:
        """Builds a classic Text-to-Image API payload for ComfyUI."""
        width, height = self.get_aspect_ratio_dimensions(aspect_ratio)
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.safetensors"
                }
            },
            "2": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 0]
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "blurry, low quality, distorted, extra limbs, bad anatomy, text, watermark",
                    "clip": ["1", 0]
                }
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": 25,
                    "cfg": 7.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["2", 0]
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                }
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "t2i_output",
                    "images": ["6", 0]
                }
            }
        }

    def build_image_ref_payload(self, prompt: str, reference_image_name: str, structural_fidelity: float) -> Dict[str, Any]:
        """Builds a ControlNet/IP-Adapter style Text-to-Image payload for ComfyUI."""
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.safetensors"
                }
            },
            "2": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 0]
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "blurry, low quality, distorted, extra limbs, bad anatomy",
                    "clip": ["1", 0]
                }
            },
            "5": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": reference_image_name
                }
            },
            "6": {
                "class_type": "ControlNetLoader",
                "inputs": {
                    "control_net_name": "control_v11p_sd15_canny.pth"
                }
            },
            "7": {
                "class_type": "ControlNetApply",
                "inputs": {
                    "strength": structural_fidelity,
                    "conditioning": ["3", 0],
                    "control_net": ["6", 0],
                    "image": ["5", 0]
                }
            },
            "8": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": 25,
                    "cfg": 7.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["7", 0],
                    "negative": ["4", 0],
                    "latent_image": ["2", 0]
                }
            },
            "9": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["8", 0],
                    "vae": ["1", 2]
                }
            },
            "10": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "ref_output",
                    "images": ["9", 0]
                }
            }
        }

    def build_img2img_payload(self, prompt: str, init_image_name: str, denoising_strength: float) -> Dict[str, Any]:
        """Builds an Image-to-Image (Img2Img) API payload for ComfyUI."""
        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.safetensors"
                }
            },
            "2": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": init_image_name
                }
            },
            "3": {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": ["2", 0],
                    "vae": ["1", 2]
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 0]
                }
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "blurry, low quality, distorted, extra limbs, bad anatomy",
                    "clip": ["1", 0]
                }
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": 25,
                    "cfg": 7.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": denoising_strength,
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["3", 0]
                }
            },
            "7": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["1", 2]
                }
            },
            "8": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "img2img_output",
                    "images": ["7", 0]
                }
            }
        }

    async def execute_comfy_workflow(self, payload: Dict[str, Any], session_id: str) -> Optional[str]:
        """
        Submits prompt to ComfyUI, polls for completion,
        and saves output to shares/outputs/{session_id}/generated_asset.png.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Submit workflow
                response = await client.post(f"{self.base_url}/prompt", json={"prompt": payload})
                if response.status_code != 200:
                    logger.error(f"Failed to submit prompt to ComfyUI: {response.text}")
                    return None
                
                prompt_data = response.json()
                prompt_id = prompt_data.get("prompt_id")
                if not prompt_id:
                    logger.error("No prompt_id returned from ComfyUI")
                    return None

                # Poll history to wait for completion
                logger.info(f"Triggered ComfyUI prompt {prompt_id}. Polling for completion...")
                max_polls = 60
                filename = None
                subfolder = ""
                image_type = "output"

                for _ in range(max_polls):
                    await asyncio.sleep(1.0)
                    history_resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                    if history_resp.status_code == 200:
                        history_data = history_resp.json()
                        if prompt_id in history_data:
                            # Finished! Extract image name
                            outputs = history_data[prompt_id].get("outputs", {})
                            for node_id, node_output in outputs.items():
                                if "images" in node_output and len(node_output["images"]) > 0:
                                    img_info = node_output["images"][0]
                                    filename = img_info.get("filename")
                                    subfolder = img_info.get("subfolder", "")
                                    image_type = img_info.get("type", "output")
                                    break
                            if filename:
                                break

                if not filename:
                    logger.error(f"Polling timed out or failed for ComfyUI prompt {prompt_id}")
                    return None

                # Download output image
                import time
                view_url = f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={image_type}"
                img_resp = await client.get(view_url)
                if img_resp.status_code == 200:
                    # Save to gen-content/{session_id}/images/
                    session_output_dir = os.path.join(self.base_workspace, session_id, "images")
                    os.makedirs(session_output_dir, exist_ok=True)
                    # Use timestamp to avoid overwriting previous images in the same session
                    ts = int(time.time())
                    output_filename = f"generated_{ts}.png"
                    output_path = os.path.join(session_output_dir, output_filename)
                    
                    with open(output_path, "wb") as f:
                        f.write(img_resp.content)
                    
                    logger.info(f"Successfully saved ComfyUI output to: {output_path}")
                    return f"/sandbox/{session_id}/images/{output_filename}"
                else:
                    logger.error(f"Failed to download image from {view_url}")
                    return None

        except Exception as e:
            logger.error(f"Exception during ComfyUI workflow execution: {e}")
            return None

    def generate_mock_image(self, session_id: str, tool_name: str, prompt: str, metadata: Dict[str, Any]) -> str:
        """
        Generates a premium visual fallback placeholder image using Pillow
        and saves it to the static folder.
        """
        # Determine size from aspect ratio
        aspect_ratio = metadata.get("aspect_ratio", "1:1")
        width, height = self.get_aspect_ratio_dimensions(aspect_ratio)

        # Create base image with a stylish dark-indigo gradient
        image = Image.new("RGB", (width, height), "#0B0F19")
        draw = ImageDraw.Draw(image)

        # Draw a modern gradient effect using rectangles
        for y in range(height):
            # Gradient from deep indigo/slate to deep purple/blue
            r = int(11 + (40 - 11) * (y / height))
            g = int(15 + (15 - 15) * (y / height))
            b = int(25 + (90 - 25) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Add a subtle border
        draw.rectangle([(10, 10), (width - 10, height - 10)], outline="#312E81", width=3)
        draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#4338CA", width=1)

        # Load font robustly
        try:
            # Try a standard system font
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            font_body = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except Exception:
            try:
                # Try generic linux/mac dejavu font
                font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
                font_body = ImageFont.truetype("DejaVuSans.ttf", 20)
                font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
            except Exception:
                # Fallback to default
                font_title = ImageFont.load_default()
                font_body = ImageFont.load_default()
                font_small = ImageFont.load_default()

        # Write Text details onto the image
        draw.text((40, 50), "MILLENIUM RADIUS", fill="#818CF8", font=font_title)
        draw.text((40, 95), "COMFYUI API WORKFLOW ENGINE (MOCK ACTIVE)", fill="#34D399", font=font_body)
        
        # Tool Type Box
        draw.rectangle([(40, 150), (320, 190)], fill="#1E1B4B", outline="#4F46E5", width=2)
        draw.text((55, 160), f"TOOL: {tool_name.upper()}", fill="#F3F4F6", font=font_body)

        # Prompt & Meta info
        y_offset = 220
        draw.text((40, y_offset), "Target Prompt:", fill="#9CA3AF", font=font_body)
        
        # Wrap prompt text manually to fit the width
        words = prompt.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            # Rough character limit for wrapping
            if len(" ".join(current_line)) > 45:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        y_offset += 30
        for line in lines[:8]:  # Limit lines to prevent overflow
            draw.text((40, y_offset), line, fill="#FFFFFF", font=font_body)
            y_offset += 26

        y_offset += 30
        draw.text((40, y_offset), "Parameters:", fill="#9CA3AF", font=font_body)
        y_offset += 25
        for k, v in metadata.items():
            draw.text((40, y_offset), f"  • {k}: {v}", fill="#E5E7EB", font=font_body)
            y_offset += 24

        # Add timestamp/branding at the bottom
        draw.text((40, height - 50), "Engine: ComfyUI Model Context Protocol Integration", fill="#4B5563", font=font_small)

        # Save to gen-content/{session_id}/images/
        import time
        session_output_dir = os.path.join(self.base_workspace, session_id, "images")
        os.makedirs(session_output_dir, exist_ok=True)
        ts = int(time.time())
        output_filename = f"mock_{ts}.png"
        output_path = os.path.join(session_output_dir, output_filename)
        
        image.save(output_path, "PNG")
        logger.info(f"Generated mock visual fallback image at: {output_path}")

        return f"/sandbox/{session_id}/images/{output_filename}"
