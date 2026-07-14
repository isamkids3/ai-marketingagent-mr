import os
import logging
import tempfile
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables early from backend root directory
_dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_dotenv_path, override=True)

logger = logging.getLogger("comfy_router")
logger.setLevel(logging.INFO)


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
        from app.agent.tools import BASE_WORKSPACE
        relative_path = virtual_path.replace("/sandbox/", "", 1)
        return os.path.abspath(os.path.join(str(BASE_WORKSPACE), relative_path))
    return os.path.abspath(virtual_path)
