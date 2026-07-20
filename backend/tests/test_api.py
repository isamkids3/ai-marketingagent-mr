import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_auth_flow_and_chat(client: AsyncClient):
    # 1. Register a new user
    user_email = "test@example.com"
    user_password = "securepassword123"
    
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": user_email, "password": user_password}
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    assert user_data["email"] == user_email
    assert "id" in user_data
    assert user_data["is_active"] is True
    
    # 2. Login to retrieve JWT token
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_email, "password": user_password}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Read user profile
    me_response = await client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == user_email
    
    # 4. Create a chat session
    session_title = "Math Tutor Conversation"
    session_response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": session_title},
        headers=headers
    )
    assert session_response.status_code == 201
    session_data = session_response.json()
    assert session_data["title"] == session_title
    assert "id" in session_data
    
    session_id = session_data["id"]
    
    # 5. List chat sessions
    list_sessions_response = await client.get("/api/v1/chat/sessions", headers=headers)
    assert list_sessions_response.status_code == 200
    sessions = list_sessions_response.json()
    assert len(sessions) > 0
    assert sessions[0]["id"] == session_id
    
    # 6. Post standard message
    user_msg_response = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "role": "user",
            "content": {"text": "Solve 2x + 5 = 15"},
            "meta_data": {"token_count": 8}
        },
        headers=headers
    )
    assert user_msg_response.status_code == 201
    user_msg_data = user_msg_response.json()
    assert user_msg_data["role"] == "user"
    assert user_msg_data["content"] == {"text": "Solve 2x + 5 = 15"}
    assert user_msg_data["meta_data"] == {"token_count": 8}
    
    # 7. Post extensible multimodal/tool message
    # Here we show how JSONB accommodates tool calls and results
    tool_msg_response = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "role": "tool",
            "content": {
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "name": "calculator",
                        "arguments": {"expression": "15 - 5"}
                    }
                ]
            },
            "meta_data": {"model": "gpt-4", "latency": 120}
        },
        headers=headers
    )
    assert tool_msg_response.status_code == 201
    tool_msg_data = tool_msg_response.json()
    assert tool_msg_data["role"] == "tool"
    assert "tool_calls" in tool_msg_data["content"]
    assert tool_msg_data["meta_data"] == {"model": "gpt-4", "latency": 120}
    
    # 8. Retrieve chat history messages
    history_response = await client.get(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers
    )
    assert history_response.status_code == 200
    messages = history_response.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "tool"
    
    # 9. Get detailed session (with eager loaded messages)
    detail_response = await client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers=headers
    )
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert len(detail_data["messages"]) == 2
    assert detail_data["messages"][0]["content"] == {"text": "Solve 2x + 5 = 15"}


@pytest.mark.asyncio
async def test_agent_chat_history_loading(client: AsyncClient):
    # 1. Register and login
    user_email = "agent-history@example.com"
    user_password = "securepassword123"
    await client.post(
        "/api/v1/auth/register",
        json={"email": user_email, "password": user_password}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_email, "password": user_password}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create a session
    session_response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test History Session"},
        headers=headers
    )
    session_id = session_response.json()["id"]
    
    # 3. Post a historical message pair to the session
    # A user message
    await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"role": "user", "content": {"text": "hello first message"}},
        headers=headers
    )
    # An assistant message with tool calls
    await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "role": "assistant",
            "content": {"text": "first response", "tool_calls": [{"name": "some_tool", "args": {}}]}
        },
        headers=headers
    )
    # A tool message
    await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "role": "tool",
            "content": {"text": "tool response output"},
            "meta_data": {"tool_name": "some_tool", "tool_call_id": "call_xyz123"}
        },
        headers=headers
    )
    
    # 4. Trigger `/api/v1/agent/chat` (streaming endpoint) while mocking get_marketing_agent
    from unittest.mock import patch, AsyncMock
    mock_agent = AsyncMock()
    
    # Use a custom async generator and tracking list to capture inputs
    calls = []
    async def mock_astream_events(inputs, **kwargs):
        calls.append((inputs, kwargs))
        yield {"event": "on_chain_end", "data": {"output": {"messages": []}}}
        
    mock_agent.astream_events = mock_astream_events
    
    mock_mcp_ctx = AsyncMock()
    mock_mcp_ctx.__aenter__.return_value = {"comfyui": AsyncMock()}
    mock_mcp_ctx.__aexit__.return_value = None

    with patch("app.api.v1.endpoints.agent.get_marketing_agent", return_value=mock_agent) as mock_get_agent, \
         patch("app.api.v1.endpoints.agent.connect_to_all_mcp_servers", return_value=mock_mcp_ctx):
         
         chat_response = await client.post(
             "/api/v1/agent/chat",
             json={"prompt": "hello second message", "session_id": session_id},
             headers=headers
         )
         
         assert chat_response.status_code == 200
         
         # Assert that get_marketing_agent was called
         mock_get_agent.assert_called_once()
         
         # Assert that agent.astream_events was called with the full history in inputs
         assert len(calls) == 1
         called_inputs = calls[0][0]
         called_messages = called_inputs["messages"]
         
         # We expect:
         # 1. User message 1 ("hello first message")
         # 2. Assistant message 1 ("first response" + tool_calls)
         # 3. Tool message 1 ("tool response output")
         # 4. User message 2 ("hello second message" - the new query)
         # Total 4 messages in history!
         assert len(called_messages) == 4
         assert called_messages[0].content == "hello first message"
         assert called_messages[1].content == "first response"
         
         # Verify tool calls attributes (which got parsed and enriched with UUID and type)
         assert called_messages[1].tool_calls[0]["name"] == "some_tool"
         assert called_messages[1].tool_calls[0]["args"] == {}
         assert "id" in called_messages[1].tool_calls[0]
         
         assert called_messages[2].content == "tool response output"
         assert called_messages[2].name == "some_tool"
         assert called_messages[2].tool_call_id == "call_xyz123"
         assert called_messages[3].content == "hello second message"


@pytest.mark.asyncio
async def test_multi_image_upload(client: AsyncClient):
    # 1. Register and login
    user_email = "multi-image@example.com"
    user_password = "securepassword123"
    await client.post(
        "/api/v1/auth/register",
        json={"email": user_email, "password": user_password}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_email, "password": user_password}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create a session
    session_response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test Multi-Image Session"},
        headers=headers
    )
    session_id = session_response.json()["id"]
    
    # 3. Call /api/v1/agent/chat via multipart form data with image and image2
    from unittest.mock import patch, AsyncMock
    mock_agent = AsyncMock()
    calls = []
    async def mock_astream_events(inputs, **kwargs):
        calls.append((inputs, kwargs))
        yield {"event": "on_chain_end", "data": {"output": {"messages": []}}}
    mock_agent.astream_events = mock_astream_events
    
    mock_mcp_ctx = AsyncMock()
    mock_mcp_ctx.__aenter__.return_value = {"comfyui": AsyncMock()}
    mock_mcp_ctx.__aexit__.return_value = None

    with patch("app.api.v1.endpoints.agent.get_marketing_agent", return_value=mock_agent) as mock_get_agent, \
         patch("app.api.v1.endpoints.agent.connect_to_all_mcp_servers", return_value=mock_mcp_ctx):
         
         # Prepare dummy files
         files = {
             "image": ("ref1.png", b"dummy_bytes_1", "image/png"),
             "image2": ("ref2.png", b"dummy_bytes_2", "image/png"),
         }
         data = {
             "prompt": "generate image based on these reference images",
             "session_id": session_id,
             "tone": "professional",
         }
         
         chat_response = await client.post(
             "/api/v1/agent/chat",
             data=data,
             files=files,
             headers=headers
         )
         
         assert chat_response.status_code == 200
         mock_get_agent.assert_called_once()
         
         # Check the prompt content received by the agent
         assert len(calls) == 1
         called_inputs = calls[0][0]
         called_messages = called_inputs["messages"]
         
         # The last message is the user prompt, which should have the custom prompt format with both images
         user_msg = called_messages[-1]
         assert f"[Uploaded Reference Image 1: /sandbox/{session_id}/ref1.png]" in user_msg.content
         assert f"[Uploaded Reference Image 2: /sandbox/{session_id}/ref2.png]" in user_msg.content
         assert "generate image based on these reference images" in user_msg.content


@pytest.mark.asyncio
async def test_three_image_upload(client: AsyncClient):
    # 1. Register and login
    user_email = "three-image@example.com"
    user_password = "securepassword123"
    await client.post(
        "/api/v1/auth/register",
        json={"email": user_email, "password": user_password}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_email, "password": user_password}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create a session
    session_response = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Test Three-Image Session"},
        headers=headers
    )
    session_id = session_response.json()["id"]
    
    # 3. Call /api/v1/agent/chat via multipart form data with image, image2, and image3
    from unittest.mock import patch, AsyncMock
    mock_agent = AsyncMock()
    calls = []
    async def mock_astream_events(inputs, **kwargs):
        calls.append((inputs, kwargs))
        yield {"event": "on_chain_end", "data": {"output": {"messages": []}}}
    mock_agent.astream_events = mock_astream_events
    
    mock_mcp_ctx = AsyncMock()
    mock_mcp_ctx.__aenter__.return_value = {"comfyui": AsyncMock()}
    mock_mcp_ctx.__aexit__.return_value = None

    with patch("app.api.v1.endpoints.agent.get_marketing_agent", return_value=mock_agent) as mock_get_agent, \
         patch("app.api.v1.endpoints.agent.connect_to_all_mcp_servers", return_value=mock_mcp_ctx):
         
         # Prepare dummy files
         files = {
             "image": ("ref1.png", b"dummy_bytes_1", "image/png"),
             "image2": ("ref2.png", b"dummy_bytes_2", "image/png"),
             "image3": ("ref3.png", b"dummy_bytes_3", "image/png"),
         }
         data = {
             "prompt": "generate image based on three reference images",
             "session_id": session_id,
             "tone": "professional",
         }
         
         chat_response = await client.post(
             "/api/v1/agent/chat",
             data=data,
             files=files,
             headers=headers
         )
         
         assert chat_response.status_code == 200
         mock_get_agent.assert_called_once()
         
         # Check the prompt content received by the agent
         assert len(calls) == 1
         called_inputs = calls[0][0]
         called_messages = called_inputs["messages"]
         
         # The last message is the user prompt, which should have the custom prompt format with all three images
         user_msg = called_messages[-1]
         assert f"[Uploaded Reference Image 1: /sandbox/{session_id}/ref1.png]" in user_msg.content
         assert f"[Uploaded Reference Image 2: /sandbox/{session_id}/ref2.png]" in user_msg.content
         assert f"[Uploaded Reference Image 3: /sandbox/{session_id}/ref3.png]" in user_msg.content
         assert "generate image based on three reference images" in user_msg.content
