"""
Chat Router - Main AI Storytelling Interaction

This is the core endpoint where:
1. User sends their action/dialogue
2. System analyzes the input
3. Characters make decisions
4. AI generates story response
5. Database is updated

This is where the magic happens!
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..database import get_db
from .. import schemas, crud, models
from ..ai.llm_manager import LLMManager
from ..ai.context_builder import ContextBuilder
from ..ai.prompts import PromptTemplates
from ..utils.logger import AppLogger, log_notification, log_error
from ..relationships.updater import RelationshipUpdater
from ..story.progression import StoryProgressionManager

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=schemas.ChatResponse)
async def send_message(request: schemas.ChatRequest, db: Session = Depends(get_db)):
    """
    Main chat endpoint - send a message and get AI story response

    This is the PRIMARY user interaction endpoint.

    Flow:
    1. Validate session
    2. Log user message
    3. Build context
    4. Detect scene changes
    5. Get character decisions
    6. Generate story response
    7. Update relationships (Phase 3.1)
    8. Check story progression (Phase 2.2)
    9. Save everything to database
    10. Return response

    Args:
        request: ChatRequest with session_id and message

    Returns:
        ChatResponse with generated story text and metadata
    """
    logger = AppLogger(db, request.session_id)

    # Step 1: Validate session exists
    session = crud.get_session(db, request.session_id)
    if not session:
        log_error(db, f"Session {request.session_id} not found", "system")
        raise HTTPException(status_code=404, detail="Session not found")

    logger.notification(
        f"=== STARTING CHAT PROCESSING ===",
        "system",
        {
            "session_id": request.session_id,
            "playthrough_id": session.playthrough_id,
            "user_message": request.message
        }
    )

    # Step 2: Save user message to database
    user_conversation = crud.create_conversation(
        db,
        schemas.ConversationCreate(
            session_id=request.session_id,
            playthrough_id=session.playthrough_id,
            speaker_type="user",
            speaker_name="User",
            message=request.message
        )
    )

    logger.notification(
        f"User message saved to database",
        "database",
        {"conversation_id": user_conversation.id}
    )

    # Step 3: Build context
    logger.context(
        "Building full context for AI...",
        "memory"
    )

    context_builder = ContextBuilder(db, request.session_id)
    full_context = context_builder.build_full_context()

    logger.context(
        "FULL CONTEXT BUILT",
        "memory",
        {
            "context_length": len(full_context),
            "context_preview": full_context[:1000] + "..." if len(full_context) > 1000 else full_context
        }
    )

    # Step 4: Detect scene changes (lightweight model)
    logger.ai_decision(
        "Analyzing user input for scene changes...",
        "ai"
    )

    llm_manager = LLMManager(db, request.session_id)

    scene_changes = await llm_manager.detect_scene_changes(
        full_context,
        request.message
    )

    logger.ai_decision(
        "Scene change analysis complete",
        "ai",
        scene_changes
    )

    # Apply scene changes if detected
    if scene_changes.get("location_changed") or scene_changes.get("time_changed"):
        context_builder.update_scene_state(
            location=scene_changes.get("new_location"),
            time_of_day=scene_changes.get("new_time")
        )

        logger.notification(
            "Scene changed - updating state",
            "story",
            {
                "new_location": scene_changes.get("new_location"),
                "new_time": scene_changes.get("new_time")
            }
        )

    # Step 5: Get character decisions (Phase 1.3/2.1)
    characters_in_scene = context_builder.get_all_characters_in_scene_info()

    logger.context(
        f"Characters in scene: {len(characters_in_scene)}",
        "character",
        {
            "characters": [c.get("name", "Unknown") for c in characters_in_scene]
        }
    )

    character_decisions = []

    for char_info in characters_in_scene:
        # Skip user character - they don't make AI decisions
        if char_info.get("type") == "User":
            logger.notification(
                f"Skipping user character: {char_info.get('name')}",
                "character"
            )
            continue

        logger.ai_decision(
            f"Analyzing what {char_info.get('name')} would do...",
            "character",
            {
                "character_name": char_info.get("name"),
                "character_type": char_info.get("type"),
                "personality": char_info.get("personality_traits"),
                "user_action": request.message
            }
        )

        decision = await llm_manager.analyze_character_decision(
            char_info,
            full_context,
            request.message
        )
        decision["character_name"] = char_info.get("name")
        decision["character_id"] = char_info.get("id")
        character_decisions.append(decision)

        logger.ai_decision(
            f"CHARACTER DECISION: {char_info.get('name')}",
            "character",
            {
                "character": char_info.get("name"),
                "action": decision.get("action"),
                "dialogue": decision.get("dialogue"),
                "emotion": decision.get("emotion"),
                "refuses_user": decision.get("refuses"),
                "reasoning": decision.get("reason")
            }
        )

    # Step 6: Generate story response (large model)
    story_info = context_builder.get_story_info()

    logger.ai_decision(
        "Building story generation prompt...",
        "ai",
        {
            "story_title": story_info.get("title"),
            "num_character_decisions": len(character_decisions)
        }
    )

    story_prompt = PromptTemplates.story_generation_prompt(
        full_context,
        request.message,
        character_decisions,
        story_info
    )

    logger.context(
        "FULL STORY PROMPT (what AI sees)",
        "ai",
        {
            "prompt_length": len(story_prompt),
            "prompt_content": story_prompt[:2000] + "..." if len(story_prompt) > 2000 else story_prompt
        }
    )

    # System prompt for story generation
    system_prompt = """You are the narrator of an interactive story. Write engaging, immersive narrative text that:
1. Follows character personalities consistently
2. Respects character decisions (they can refuse or disagree)
3. Uses third-person perspective
4. Includes both narration and dialogue
5. Maintains story continuity
6. Is appropriate for the story's tone"""

    logger.ai_decision(
        "Sending prompt to AI for story generation...",
        "ai",
        {"model_size": "large", "system_prompt_length": len(system_prompt)}
    )

    generated_response = await llm_manager.generate_text(
        story_prompt,
        model_size="large",
        system_prompt=system_prompt
    )

    logger.ai_decision(
        "AI GENERATED RESPONSE",
        "ai",
        {
            "response_length": len(generated_response),
            "full_response": generated_response
        }
    )

    # Step 7: Save AI response to database
    ai_conversation = crud.create_conversation(
        db,
        schemas.ConversationCreate(
            session_id=request.session_id,
            playthrough_id=session.playthrough_id,
            speaker_type="narrator",
            speaker_name="Narrator",
            message=generated_response
        )
    )

    # Step 8: Update relationships (Phase 3.1)
    relationship_updates = {}
    try:
        updater = RelationshipUpdater(db, request.session_id)
        relationship_updates = await updater.update_relationships_from_interaction(
            request.message,
            generated_response,
            character_decisions
        )
    except Exception as e:
        logger.error(
            f"Error updating relationships: {str(e)}",
            "character",
            {"error": str(e)}
        )

    # Step 9: Check story progression (Phase 2.2)
    story_flags_set = []
    try:
        progression_manager = StoryProgressionManager(db, session.playthrough_id)
        story_flags_set = await progression_manager.check_progression(
            request.message,
            generated_response,
            character_decisions
        )
    except Exception as e:
        logger.error(
            f"Error checking story progression: {str(e)}",
            "story",
            {"error": str(e)}
        )

    # Step 10: Update session activity
    crud.update_session_activity(db, request.session_id)

    # Build character info for response
    chars_in_scene = []
    for char_info in characters_in_scene:
        chars_in_scene.append(schemas.CharacterInScene(
            character_id=char_info.get("id", 0),
            character_name=char_info.get("name", "Unknown"),
            character_type=char_info.get("type", "Unknown"),
            mood=char_info.get("mood"),
            intent=char_info.get("intent"),
            position=char_info.get("position")
        ))

    # Get current scene info
    current_scene = crud.get_current_scene_state(db, request.session_id)
    current_location = current_scene.location if current_scene else None
    current_time = current_scene.time_of_day if current_scene else None

    logger.notification(
        "Chat response completed successfully",
        "system"
    )

    return schemas.ChatResponse(
        message=generated_response,
        session_id=request.session_id,
        conversation_id=ai_conversation.id,
        characters_in_scene=chars_in_scene if chars_in_scene else None,
        current_location=current_location,
        current_time=current_time,
        relationship_updates=relationship_updates if relationship_updates else None,
        story_flags_set=story_flags_set if story_flags_set else None
    )


@router.post("/generate-more", response_model=schemas.ChatResponse)
async def generate_more(
    request: schemas.GenerateMoreRequest,
    db: Session = Depends(get_db)
):
    """
    Generate more story content without user input

    Phase 3.2 feature: GENERATE MORE option
    The AI continues the story without requiring user action
    """
    logger = AppLogger(db, request.session_id)

    # Validate session
    session = crud.get_session(db, request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.notification(
        "Generate more request received",
        "system"
    )

    # Build context
    context_builder = ContextBuilder(db, request.session_id)
    full_context = context_builder.build_full_context()

    # Get last narrative message
    history = crud.get_conversation_history(db, request.session_id, limit=1)
    last_narrative = ""
    if history:
        for msg in reversed(history):
            if msg.speaker_type == "narrator":
                last_narrative = msg.message
                break

    # Get characters in scene
    characters_in_scene = context_builder.get_all_characters_in_scene_info()

    # Generate continuation
    llm_manager = LLMManager(db, request.session_id)

    prompt = PromptTemplates.generate_more_prompt(
        full_context,
        last_narrative,
        characters_in_scene
    )

    system_prompt = """You are continuing an interactive story. Write a brief continuation that:
1. Advances the story slightly
2. Maintains character personalities
3. Leaves room for user interaction
4. Is engaging and immersive"""

    generated_response = await llm_manager.generate_text(
        prompt,
        model_size="large",
        max_tokens=1000,  # Shorter than regular response
        system_prompt=system_prompt
    )

    logger.ai_decision(
        "Generated continuation",
        "ai",
        {"response_length": len(generated_response)}
    )

    # Save to database
    ai_conversation = crud.create_conversation(
        db,
        schemas.ConversationCreate(
            session_id=request.session_id,
            playthrough_id=session.playthrough_id,
            speaker_type="narrator",
            speaker_name="Narrator",
            message=generated_response
        )
    )

    # Update session activity
    crud.update_session_activity(db, request.session_id)

    return schemas.ChatResponse(
        message=generated_response,
        session_id=request.session_id,
        conversation_id=ai_conversation.id
    )


@router.get("/history/{session_id}", response_model=List[schemas.ConversationResponse])
async def get_chat_history(
    session_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get conversation history for a session

    Phase 3.2 feature: SHOW CHAT HISTORY
    Used when resuming a session
    """
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    history = crud.get_conversation_history(db, session_id, limit=limit)

    log_notification(
        db,
        f"Retrieved chat history",
        "system",
        {"session_id": session_id, "message_count": len(history)},
        session_id
    )

    return history


@router.get("/playthrough-history/{playthrough_id}", response_model=List[schemas.ConversationResponse])
async def get_playthrough_history(
    playthrough_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all conversation history for a playthrough (across all sessions)

    Useful for seeing the complete story so far
    """
    playthrough = crud.get_playthrough(db, playthrough_id)
    if not playthrough:
        raise HTTPException(status_code=404, detail="Playthrough not found")

    history = crud.get_all_playthrough_conversations(db, playthrough_id, limit=limit)

    log_notification(
        db,
        f"Retrieved playthrough history",
        "system",
        {"playthrough_id": playthrough_id, "message_count": len(history)}
    )

    return history
