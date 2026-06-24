import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import ChatSessionCreate, ChatMessageCreate

async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Optional[ChatSession]:
    """Retrieve a chat session along with its messages."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    return result.scalar_one_or_none()

async def get_sessions_by_user(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
) -> List[ChatSession]:
    """List all chat sessions belonging to a user, ordered by most recently updated."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())

async def create_session(
    db: AsyncSession, user_id: int, session_in: ChatSessionCreate
) -> ChatSession:
    """Create a new chat session."""
    db_session = ChatSession(
        user_id=user_id,
        title=session_in.title or "New Chat Thread",
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session

async def delete_session(db: AsyncSession, session_id: uuid.UUID) -> bool:
    """Delete a chat session (and cascade-delete messages)."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    db_session = result.scalar_one_or_none()
    if db_session:
        await db.delete(db_session)
        await db.commit()
        return True
    return False

async def get_messages_by_session(
    db: AsyncSession, session_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> List[ChatMessage]:
    """Retrieve all messages in a session, ordered chronologically."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())

async def create_message(
    db: AsyncSession, session_id: uuid.UUID, message_in: ChatMessageCreate
) -> ChatMessage:
    """Create a new message inside a chat session, and bump the session's updated_at timestamp."""
    db_message = ChatMessage(
        session_id=session_id,
        role=message_in.role,
        content=message_in.content,
        meta_data=message_in.meta_data,
    )
    db.add(db_message)

    # Touch/update the session's updated_at timestamp to bring it to the top of list
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    db_session = result.scalar_one_or_none()
    if db_session:
        db_session.updated_at = datetime.now(timezone.utc)
        db.add(db_session)

    await db.commit()
    await db.refresh(db_message)
    return db_message
