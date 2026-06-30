import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcp import ClientSession
from app.agent.orchestrator import connect_to_all_mcp_servers, get_marketing_agent

@pytest.mark.asyncio
async def test_connect_to_all_mcp_servers_no_postiz():
    # Mock connect_to_mcp_server
    comfyui_mock_session = AsyncMock()
    comfyui_mock_session.initialize = AsyncMock()
    
    # Mock context manager of comfyui
    comfyui_cm = MagicMock()
    comfyui_cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
    comfyui_cm.__aexit__ = AsyncMock()
    
    with patch("app.agent.orchestrator.connect_to_mcp_server", return_value=comfyui_cm), \
         patch("app.agent.orchestrator.ClientSession", return_value=comfyui_mock_session), \
         patch.dict(os.environ, {"POSTIZ_API_KEY": ""}):
         
        async with connect_to_all_mcp_servers() as sessions:
            assert "comfyui" in sessions
            assert "postiz" not in sessions
            assert sessions["comfyui"] == comfyui_mock_session

@pytest.mark.asyncio
async def test_connect_to_all_mcp_servers_with_postiz():
    comfyui_mock_session = AsyncMock()
    comfyui_mock_session.initialize = AsyncMock()
    
    postiz_mock_session = AsyncMock()
    postiz_mock_session.initialize = AsyncMock()
    
    # Mock context manager of comfyui
    comfyui_cm = MagicMock()
    comfyui_cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
    comfyui_cm.__aexit__ = AsyncMock()

    # Mock context manager of postiz (streamablehttp_client)
    postiz_cm = MagicMock()
    postiz_cm.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock(), None))
    postiz_cm.__aexit__ = AsyncMock()

    with patch("app.agent.orchestrator.connect_to_mcp_server", return_value=comfyui_cm), \
         patch("app.agent.orchestrator.streamablehttp_client", return_value=postiz_cm), \
         patch("app.agent.orchestrator.ClientSession") as mock_client_session, \
         patch.dict(os.environ, {"POSTIZ_API_KEY": "test_key", "POSTIZ_MCP_URL": "http://mock-postiz/mcp"}):
         
        # Make ClientSession return comfyui mock first, then postiz mock
        mock_client_session.side_effect = [comfyui_mock_session, postiz_mock_session]
         
        async with connect_to_all_mcp_servers() as sessions:
            assert "comfyui" in sessions
            assert "postiz" in sessions
            assert sessions["comfyui"] == comfyui_mock_session
            assert sessions["postiz"] == postiz_mock_session

@pytest.mark.asyncio
async def test_get_marketing_agent_multi_session():
    comfy_tools = MagicMock()
    comfy_tools.tools = [
        MagicMock(name="tool1", description="desc1", inputSchema={"properties": {}})
    ]
    comfy_tools.tools[0].name = "text_image"
    
    postiz_tools = MagicMock()
    postiz_tools.tools = [
        MagicMock(name="tool2", description="desc2", inputSchema={"properties": {}})
    ]
    postiz_tools.tools[0].name = "integrationList"
    
    comfyui_mock_session = AsyncMock()
    comfyui_mock_session.list_tools = AsyncMock(return_value=comfy_tools)
    
    postiz_mock_session = AsyncMock()
    postiz_mock_session.list_tools = AsyncMock(return_value=postiz_tools)
    
    sessions = {
        "comfyui": comfyui_mock_session,
        "postiz": postiz_mock_session
    }
    
    # We clear the cached agent to force rediscovery
    with patch("app.agent.orchestrator._cached_agent", None), \
         patch("app.agent.orchestrator.create_deep_agent") as mock_create_agent:
         
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        agent = await get_marketing_agent(sessions, session_id="test_id")
        
        # Verify that create_deep_agent was called with tools from both servers
        called_args, called_kwargs = mock_create_agent.call_args
        tools_passed = called_kwargs["tools"]
        
        # Find tools by name
        tool_names = [t.name for t in tools_passed]
        assert "text_image" in tool_names
        assert "integrationList" in tool_names
