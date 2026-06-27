"""
Chat Router - thin HTTP shell around ChatPipeline.

The per-turn pipeline lives in `app.pipeline.chat_pipeline.ChatPipeline`.
This module's only jobs are:
- parse/validate the request,
- look up sessions/playthroughs for history endpoints,
- shape the response.

Any new pipeline-stage logic belongs in ChatPipeline, not here.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..pipeline import ChatPipeline
from ..utils.logger import log_notification

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=schemas.ChatResponse)
async def send_message(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Run a full chat turn through ChatPipeline."""
    pipeline = ChatPipeline(db, request.session_id)
    return await pipeline.run(request.message)


@router.post("/generate-more", response_model=schemas.ChatResponse)
async def generate_more(
    request: schemas.GenerateMoreRequest,
    db: Session = Depends(get_db),
):
    """Continue the story without user input."""
    pipeline = ChatPipeline(db, request.session_id)
    return await pipeline.generate_more()


@router.get("/history/{session_id}", response_model=List[schemas.ConversationResponse])
async def get_chat_history(
    session_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get conversation history for a session (used when resuming)."""
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    history = crud.get_conversation_history(db, session_id, limit=limit)

    log_notification(
        db,
        "Retrieved chat history",
        "system",
        {"session_id": session_id, "message_count": len(history)},
        session_id,
    )

    return history


@router.get(
    "/playthrough-history/{playthrough_id}",
    response_model=List[schemas.ConversationResponse],
)
async def get_playthrough_history(
    playthrough_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get all conversation history for a playthrough (across all sessions)."""
    playthrough = crud.get_playthrough(db, playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    history = crud.get_all_playthrough_conversations(db, playthrough_id, limit=limit)

    log_notification(
        db,
        "Retrieved playthrough history",
        "system",
        {"playthrough_id": playthrough_id, "message_count": len(history)},
    )

    return history
