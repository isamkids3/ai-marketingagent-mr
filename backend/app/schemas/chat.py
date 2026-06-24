import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class ChatMessageBase(BaseModel):
    role: str = Field(
        ...,
        description="Role of the message sender: system, user, assistant, or tool"
    )
    content: Dict[str, Any] = Field(
        ...,
        description="Extensible content payload (e.g., {'text': '...'} or multimodal layouts)",
    )
    meta_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Extensible metadata (token counts, timestamps, trace ids)",
    )

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class ChatSessionBase(BaseModel):
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="The chat session title (optional)"
    )

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSessionResponse(ChatSessionBase):
    id: uuid.UUID
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatSessionDetailResponse(ChatSessionResponse):
    messages: List[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
