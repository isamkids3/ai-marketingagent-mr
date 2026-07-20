import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcp import ClientSession
from app.agent.orchestrator import connect_to_all_mcp_servers, get_marketing_agent

@pytest.mark.asyncio
async def test_connect_to_all_mcp_servers_no_postiz():
    comfyui_mock_session = AsyncMock()
    with patch("app.agent.orchestrator.get_global_mcp_sessions", return_value={"comfyui": comfyui_mock_session}):
        async with connect_to_all_mcp_servers() as sessions:
            assert "comfyui" in sessions
            assert "postiz" not in sessions
            assert sessions["comfyui"] == comfyui_mock_session

@pytest.mark.asyncio
async def test_connect_to_all_mcp_servers_with_postiz():
    comfyui_mock_session = AsyncMock()
    postiz_mock_session = AsyncMock()
    with patch("app.agent.orchestrator.get_global_mcp_sessions", return_value={"comfyui": comfyui_mock_session, "postiz": postiz_mock_session}):
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
    with patch("app.agent.orchestrator._cached_raw_agent", None), \
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

@pytest.mark.asyncio
async def test_active_sessions_lookup():
    from app.agent.orchestrator import active_sessions, mcp_tool_to_langchain
    from mcp import ClientSession
    from mcp.types import CallToolResult, TextContent
    
    mock_session_closure = AsyncMock(spec=ClientSession)
    mock_session_active = AsyncMock(spec=ClientSession)
    
    # Setup call_tool return value
    mock_session_active.call_tool = AsyncMock(return_value=CallToolResult(content=[TextContent(type="text", text="success_active")], isError=False))
    mock_session_closure.call_tool = AsyncMock(return_value=CallToolResult(content=[TextContent(type="text", text="success_closure")], isError=False))
    
    # Create the langchain tool wrapping the mock session closure
    mcp_tool = MagicMock()
    mcp_tool.name = "my_tool"
    mcp_tool.description = "my desc"
    mcp_tool.inputSchema = {"properties": {}}
    
    lc_tool = mcp_tool_to_langchain(mcp_tool, mock_session_closure)
    
    # Call 1: ContextVar not set -> Fallback to mock_session_closure
    res_fallback = await lc_tool.ainvoke({})
    assert "success_closure" in res_fallback
    mock_session_closure.call_tool.assert_called_once()
    
    # Call 2: ContextVar set -> Use active session
    token = active_sessions.set({"comfyui": mock_session_active})
    try:
        res_active = await lc_tool.ainvoke({})
        assert "success_active" in res_active
        mock_session_active.call_tool.assert_called_once()
    finally:
        active_sessions.reset(token)


def test_adapt_postiz_schedule_payload():
    from app.agent.orchestrator import adapt_postiz_schedule_payload
    
    with patch.dict(os.environ, {"CLOUDFLARE_BUCKET_URL": "https://pub-37fda8d9481c4deda4a0f807036404f0.r2.dev"}):
        # 1. Payload with no attachments inside postsAndComments and empty dicts inside settings
        social_post = [
            {
                "integrationId": "cmr123",
                "postsAndComments": [
                    {
                        "content": "<p>My text</p>"
                    }
                ],
                "settings": [
                    {},
                    {"key": "privacy_level", "value": True}
                ]
            }
        ]
        
        adapted = adapt_postiz_schedule_payload(social_post)
        
        assert len(adapted) == 1
        post = adapted[0]
        # Verify attachments populated
        assert post["postsAndComments"][0]["attachments"] == []
        # Verify settings cleaned up, privacy_level converted, and ALL defaults injected
        # Expected: privacy_level (from input) + 7 auto-injected TikTok defaults + post_type = 9
        settings_dict = {s["key"]: s["value"] for s in post["settings"]}
        assert len(post["settings"]) == 9
        assert settings_dict["privacy_level"] == "SELF_ONLY"
        assert settings_dict["duet"] is False
        assert settings_dict["stitch"] is False
        assert settings_dict["comment"] is True
        assert settings_dict["autoAddMusic"] == "yes"
        assert settings_dict["brand_content_toggle"] is False
        assert settings_dict["brand_organic_toggle"] is True
        assert settings_dict["content_posting_method"] == "DIRECT_POST"
        assert settings_dict["post_type"] == "post"
        
        # 2. Payload with nested settings inside postsAndComments[0].post
        nested_social_post = [
            {
                "integrationId": "cmr4d32en0001n26yltm4qo9g",
                "postsAndComments": [
                    {
                        "post": {
                            "settings": {
                                "autoAddMusic": "yes",
                                "privacy_level": True,
                                "duet": False
                            }
                        }
                    }
                ]
            }
        ]
        
        adapted_nested = adapt_postiz_schedule_payload(nested_social_post)
        
        assert len(adapted_nested) == 1
        post_nested = adapted_nested[0]
        # Check that settings were extracted to root and privacy_level was converted
        settings_dict = {s["key"]: s["value"] for s in post_nested["settings"]}
        assert settings_dict["autoAddMusic"] == "yes"
        assert settings_dict["privacy_level"] == "SELF_ONLY"
        assert settings_dict["duet"] is False
        assert settings_dict["post_type"] == "post"
        # Ensure nested keys are removed from post item to avoid extraProperties validation issues
        assert "post" not in post_nested["postsAndComments"][0]
        
        # 3. Payload with root-level dictionary settings and root-level attachments
        root_dict_post = [
            {
                "integrationId": "cmr456",
                "attachments": [
                    "https://example.com/image.png"
                ],
                "settings": {
                    "duet": True,
                    "stitch": False
                },
                "postsAndComments": [
                    {
                        "content": "<p>Direct settings</p>",
                        "attachments": []
                    }
                ]
            }
        ]
        adapted_root_dict = adapt_postiz_schedule_payload(root_dict_post)
        assert len(adapted_root_dict) == 1
        post_root_dict = adapted_root_dict[0]
        # Check that settings were flattened from dict to list of key/value pairs
        settings_dict = {s["key"]: s["value"] for s in post_root_dict["settings"]}
        # Verify default privacy_level injected because it was missing
        assert settings_dict["privacy_level"] == "PUBLIC_TO_EVERYONE"
        assert settings_dict["duet"] is True   # explicitly provided
        assert settings_dict["stitch"] is False  # explicitly provided
        assert settings_dict["comment"] is True  # auto-injected default
        assert settings_dict["autoAddMusic"] == "yes"  # auto-injected default
        assert settings_dict["brand_content_toggle"] is False  # auto-injected default
        assert settings_dict["brand_organic_toggle"] is True  # auto-injected default
        assert settings_dict["content_posting_method"] == "DIRECT_POST"  # auto-injected default
        assert settings_dict["post_type"] == "post"
        # Verify attachments extracted and merged into postsAndComments[0]['attachments']
        assert post_root_dict["postsAndComments"][0]["attachments"] == ["https://example.com/image.png"]
        # Verify root-level attachments popped to avoid validation failures
        assert "attachments" not in post_root_dict

        # 4. Payload with list of dictionary maps in settings (like generated by the agent)
        list_map_post = [
            {
                "integrationId": "cmr789",
                "postsAndComments": [
                    {
                        "content": "<p>Stay refreshed! 💧❄️</p>",
                        "attachments": ["https://example.com/image.png"]
                    }
                ],
                "settings": [
                    {
                        "privacy_level": "SELF_ONLY",
                        "duet": False,
                        "stitch": False,
                        "comment": True,
                        "autoAddMusic": "yes",
                        "brand_content_toggle": False,
                        "brand_organic_toggle": True,
                        "content_posting_method": "DIRECT_POST",
                        "post_type": "post"
                    }
                ]
            }
        ]
        adapted_list_map = adapt_postiz_schedule_payload(list_map_post)
        assert len(adapted_list_map) == 1
        post_list_map = adapted_list_map[0]
        settings_dict = {s["key"]: s["value"] for s in post_list_map["settings"]}
        assert settings_dict["privacy_level"] == "SELF_ONLY"
        assert settings_dict["duet"] is False
        assert settings_dict["stitch"] is False
        assert settings_dict["comment"] is True
        assert settings_dict["autoAddMusic"] == "yes"
        assert settings_dict["brand_content_toggle"] is False
        assert settings_dict["brand_organic_toggle"] is True
        assert settings_dict["content_posting_method"] == "DIRECT_POST"
        assert settings_dict["post_type"] == "post"

        # 5. Payload with truncated/malformed R2 bucket domain in attachments (copy-paste error)
        malformed_url_post = [
            {
                "integrationId": "cmr999",
                "postsAndComments": [
                    {
                        "content": "<p>Truncated R2 domain test</p>",
                        "attachments": [
                            "https://pub-37fda8d94a0f807036404f0.r2.dev/1tCI7ws2zy.png"
                        ]
                    }
                ]
            }
        ]
        adapted_malformed = adapt_postiz_schedule_payload(malformed_url_post)
        assert len(adapted_malformed) == 1
        post_malformed = adapted_malformed[0]
        # The domain should be corrected back to pub-37fda8d9481c4deda4a0f807036404f0.r2.dev
        assert post_malformed["postsAndComments"][0]["attachments"] == [
            "https://pub-37fda8d9481c4deda4a0f807036404f0.r2.dev/1tCI7ws2zy.png"
        ]



