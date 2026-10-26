"""Chat CRUD, persistence, and streaming response routes."""

import asyncio
import base64
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.prisma import prisma
from app.db.supabase import get_supabase
from prisma import Json
from app.models.chat import ChatCreateRequest, ChatUpdateRequest, MessageCreateRequest
from app.services.context_manager import context_window_manager
from app.services.document_service import select_relevant_text
from app.services.goldmine_engine import goldmine_engine
from app.services.model_registry import model_registry
from app.services.research_service import ResearchUnavailable, search_web
from app.services.attachment_fallback import (
    claim_attachments,
    get_pending_attachments,
    public_attachment,
)

logger = logging.getLogger(__name__)
router = APIRouter()
_memory_mode = False
_memory_chats: dict[str, dict[str, dict]] = {}


def _activate_memory_mode(exc: Exception) -> None:
    """Keep local development usable if the Supabase Postgres socket drops."""
    global _memory_mode
    _memory_mode = True
    logger.warning("Using temporary in-memory chats because database access failed (%s)", type(exc).__name__)


def enable_memory_mode() -> None:
    """Start in temporary local mode when Postgres is already unavailable."""
    global _memory_mode
    _memory_mode = True
    logger.warning("Starting with temporary in-memory chats because the database is unavailable")


def _user_chats(user_id: str) -> dict[str, dict]:
    return _memory_chats.setdefault(user_id, {})


def _memory_chat_payload(chat: dict) -> dict:
    return {key: chat[key] for key in ("id", "title", "created_at", "updated_at")}


def _needs_team_reasoning(prompt: str, experience_mode: str) -> bool:
    """Use multiple models only when the request benefits from comparison."""
    if experience_mode == "research":
        return True
    cleaned = prompt.strip().lower()
    if experience_mode == "study":
        return len(cleaned.split()) > 5
    if len(cleaned.split()) <= 8 and re.fullmatch(r"[\w\s'?!,.:-]+", cleaned):
        casual = ("hi", "hello", "hey", "hii", "who am i", "what is my name", "thanks", "thank you")
        if any(phrase in cleaned for phrase in casual):
            return False
    team_signals = ("compare", "research", "plan", "strategy", "analyse", "analyze", "explain", "review", "debug", "learn", "study", "pros and cons", "best way")
    return len(cleaned.split()) > 18 or any(signal in cleaned for signal in team_signals)


@router.get("/chats")
async def list_chats(user=Depends(get_current_user)):
    if _memory_mode:
        return sorted((_memory_chat_payload(chat) for chat in _user_chats(user["user_id"]).values()), key=lambda item: item["updated_at"], reverse=True)
    try:
        chats = await prisma.chat.find_many(where={"user_id": user["user_id"]}, order={"updated_at": "desc"})
        return [{"id": str(c.id), "title": c.title, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()} for c in chats]
    except Exception as exc:
        _activate_memory_mode(exc)
        return []


@router.post("/chats")
async def create_chat(body: ChatCreateRequest, user=Depends(get_current_user)):
    if _memory_mode:
        now = datetime.now(timezone.utc).isoformat()
        chat = {"id": str(uuid.uuid4()), "title": body.title or "New Chat", "created_at": now, "updated_at": now, "messages": []}
        _user_chats(user["user_id"])[chat["id"]] = chat
        return _memory_chat_payload(chat)
    try:
        chat = await prisma.chat.create(data={"user_id": user["user_id"], "title": body.title or "New Chat"})
        return {"id": str(chat.id), "title": chat.title, "created_at": chat.created_at.isoformat(), "updated_at": chat.updated_at.isoformat()}
    except Exception as exc:
        _activate_memory_mode(exc)
        return await create_chat(body, user)


@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str, user=Depends(get_current_user)):
    if _memory_mode:
        chat = _user_chats(user["user_id"]).get(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"id": chat["id"], "title": chat["title"], "messages": chat["messages"]}
    chat = await prisma.chat.find_first(where={"id": chat_id, "user_id": user["user_id"]})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = await prisma.message.find_many(where={"chat_id": chat_id, "user_id": user["user_id"]}, order={"created_at": "asc"})
    message_list = []
    for msg in messages:
        data = {
            "id": str(msg.id), "chat_id": str(msg.chat_id), "user_id": str(msg.user_id),
            "role": msg.role, "content": msg.content, "image_urls": msg.image_urls,
            "web_research": msg.web_research, "provider_failures": msg.provider_failures,
            "created_at": msg.created_at.isoformat(),
        }
        if msg.role == "user":
            attachments = await prisma.attachment.find_many(where={"message_id": str(msg.id), "user_id": user["user_id"]})
            data["attachments"] = [{"id": str(a.id), "file_name": a.file_name, "mime_type": a.mime_type, "size_bytes": a.size_bytes} for a in attachments]
        if msg.role == "assistant":
            model_responses = await prisma.modelresponse.find_many(where={"message_id": str(msg.id)})
            selected = next((response for response in model_responses if response.selected), None)
            if selected:
                data.update({
                    "model_id": selected.model_id, "provider": selected.provider,
                    "goldmine_score": selected.goldmine_score,
                    "evaluation_signals": selected.evaluation_signals,
                    "web_verified": selected.web_verified,
                    "selection_explanation": selected.selection_explanation,
                    "response_type": selected.response_type,
                })
            data["all_responses"] = [{
                "id": str(r.id), "model_id": r.model_id, "provider": r.provider,
                "content": r.content, "goldmine_score": r.goldmine_score,
                "evaluation_signals": r.evaluation_signals, "selected": r.selected,
                "latency_ms": r.latency_ms, "web_verified": r.web_verified,
                "response_type": r.response_type,
            } for r in model_responses]
            sources = await prisma.source.find_many(where={"message_id": str(msg.id)})
            data["sources"] = [{"id": str(s.id), "title": s.title, "url": s.url, "domain": s.domain, "relevance_score": s.relevance_score, "support_type": s.support_type} for s in sources]
        message_list.append(data)
    return {"id": str(chat.id), "title": chat.title, "messages": message_list}


@router.patch("/chats/{chat_id}")
async def update_chat(chat_id: str, body: ChatUpdateRequest, user=Depends(get_current_user)):
    if _memory_mode:
        chat = _user_chats(user["user_id"]).get(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if body.title is not None:
            chat["title"] = body.title.strip()
        return {"status": "ok"}
    chat = await prisma.chat.find_first(where={"id": chat_id, "user_id": user["user_id"]})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if body.title is not None:
        await prisma.chat.update(where={"id": chat_id}, data={"title": body.title.strip()})
    return {"status": "ok"}


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, user=Depends(get_current_user)):
    if _memory_mode:
        if _user_chats(user["user_id"]).pop(chat_id, None) is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"status": "deleted"}
    chat = await prisma.chat.find_first(where={"id": chat_id, "user_id": user["user_id"]})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await prisma.chat.delete(where={"id": chat_id})
    return {"status": "deleted"}


async def _completed_response(message, chat_id: str) -> dict:
    responses = await prisma.modelresponse.find_many(where={"message_id": str(message.id)})
    selected = next((response for response in responses if response.selected), None)
    sources = await prisma.source.find_many(where={"message_id": str(message.id)})
    return {
        "chat_id": chat_id, "message_id": str(message.id), "content": message.content,
        "selected_response": selected.model_dump() if selected else None,
        "all_responses": [response.model_dump() for response in responses],
        "sources": [source.model_dump() for source in sources],
        "goldmine_score": selected.goldmine_score if selected else None,
        "selection_explanation": selected.selection_explanation if selected else "",
        "web_verified": False,
        "synthesis_status": selected.response_type if selected else "unknown",
        "provider_failures": message.provider_failures or [],
    }


async def _execute_memory_chat(body: MessageCreateRequest, user: dict, emit=None) -> dict:
    """Generate a response without Postgres persistence during a DB outage."""
    chats = _user_chats(user["user_id"])
    if body.chat_id:
        chat = chats.get(body.chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        now = datetime.now(timezone.utc).isoformat()
        chat = {"id": str(uuid.uuid4()), "title": body.content[:60], "created_at": now, "updated_at": now, "messages": []}
        chats[chat["id"]] = chat

    if len(set(body.attachment_ids)) != len(body.attachment_ids):
        raise HTTPException(status_code=422, detail="Duplicate attachment IDs are not allowed")
    attachments = get_pending_attachments(user["user_id"], body.attachment_ids) if body.attachment_ids else []
    if attachments is None:
        raise HTTPException(status_code=404, detail="One or more uploads are unavailable or already attached")
    image_attachments = [item for item in attachments if item["mime_type"].startswith("image/")]
    if len(image_attachments) > 4:
        raise HTTPException(status_code=413, detail="Attach up to 4 images per message")
    image_bytes_total = sum(len(item["data"]) for item in image_attachments)
    if image_bytes_total > 16 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Combined image size must be 16 MB or less")
    image_urls = [
        f"data:{item['mime_type']};base64,{base64.b64encode(item['data']).decode('ascii')}"
        for item in image_attachments
    ]

    use_web_research = body.web_research or (body.experience_mode == "research" and bool(settings.search_api_key))
    research_results = []
    if use_web_research:
        try:
            research_results = await search_web(body.content)
        except ResearchUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    now = datetime.now(timezone.utc).isoformat()
    user_message_id = str(uuid.uuid4())
    user_message = {"id": user_message_id, "chat_id": chat["id"], "role": "user", "content": body.content, "created_at": now, "web_research": use_web_research, "attachments": [public_attachment(item) for item in attachments]}
    documents = [{"file_name": item["file_name"], "text": item.get("extracted_text") or ""} for item in attachments if not item["mime_type"].startswith("image/")]
    context_messages = await context_window_manager.build_context(
        user_id=user["user_id"], prior_messages=[], current_user_prompt=body.content,
        experience_mode=body.experience_mode, documents=documents,
        research_results=research_results, image_urls=image_urls or None,
    )
    effective_mode = "single" if body.mode == "goldmine" and not _needs_team_reasoning(body.content, body.experience_mode) else body.mode
    selected_model_id = body.model_id
    if image_urls and effective_mode == "single" and selected_model_id:
        selected_model = await model_registry.get_model(selected_model_id)
        if not selected_model or not selected_model.supports_vision:
            vision_models = await model_registry.get_vision_models()
            if not vision_models:
                raise HTTPException(status_code=422, detail="No image-capable model is configured")
            selected_model_id = vision_models[0].id
    result = await goldmine_engine.process(
        messages=context_messages, user_prompt=body.content, chat_id=chat["id"],
        message_id=str(uuid.uuid4()), model_id=selected_model_id, mode=effective_mode,
        has_image=bool(image_urls),
        progress_callback=emit,
    )
    assistant_message = {
        "id": result.message_id, "chat_id": chat["id"], "role": "assistant",
        "content": result.selected_response.content, "created_at": datetime.now(timezone.utc).isoformat(),
        "model_id": result.selected_response.model_id, "provider": result.selected_response.provider,
        "goldmine_score": result.goldmine_score, "response_type": result.selected_response.response_type,
        "sources": [{key: item[key] for key in ("title", "url", "domain")} for item in research_results],
    }
    chat["messages"].extend((user_message, assistant_message))
    claim_attachments(user["user_id"], body.attachment_ids, user_message_id)
    chat["updated_at"] = assistant_message["created_at"]
    return {
        "chat_id": chat["id"], "message_id": result.message_id, "content": result.selected_response.content,
        "selected_response": result.selected_response.model_dump(), "all_responses": [item.model_dump() for item in result.all_responses],
        "sources": assistant_message["sources"], "goldmine_score": result.goldmine_score,
        "selection_explanation": result.selection_explanation, "web_verified": False,
        "synthesis_model_id": result.synthesis_model_id, "synthesis_status": result.synthesis_status,
        "provider_failures": result.provider_failures,
    }


async def _execute_chat(body: MessageCreateRequest, user: dict, emit=None) -> dict:
    if _memory_mode:
        return await _execute_memory_chat(body, user, emit)
    user_id = user["user_id"]
    request_id = str(body.request_id) if body.request_id else str(uuid.uuid4())
    if body.image_urls:
        raise HTTPException(status_code=422, detail="Image attachments are not supported")
    if body.mode == "single":
        if not body.model_id:
            raise HTTPException(status_code=422, detail="Choose a model for single-model mode")
        selected_model = await model_registry.get_model(body.model_id)
        if not selected_model:
            raise HTTPException(status_code=422, detail="The selected model is not configured or available")

    if body.attachment_ids:
        if len(set(body.attachment_ids)) != len(body.attachment_ids):
            raise HTTPException(status_code=422, detail="Duplicate attachment IDs are not allowed")
        attachments = await prisma.attachment.find_many(where={"id": {"in": body.attachment_ids}, "user_id": user_id})
        if len(attachments) != len(body.attachment_ids) or any(item.message_id for item in attachments):
            raise HTTPException(status_code=404, detail="One or more attachments are unavailable")
    else:
        attachments = []

    image_attachments = [item for item in attachments if (item.mime_type or "").startswith("image/")]
    if len(image_attachments) > 4:
        raise HTTPException(status_code=413, detail="Attach up to 4 images per message")
    image_urls = []
    image_bytes_total = 0
    if image_attachments:
        storage = get_supabase()
        if storage is None:
            raise HTTPException(status_code=503, detail="Private image storage is unavailable")
        for attachment in image_attachments:
            try:
                raw_image = await asyncio.to_thread(
                    storage.storage.from_("chat-attachments").download,
                    attachment.storage_path,
                )
            except Exception as exc:
                raise HTTPException(status_code=502, detail="An attached image could not be read") from exc
            image_bytes_total += len(raw_image)
            if image_bytes_total > 16 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Combined image size must be 16 MB or less")
            encoded = base64.b64encode(raw_image).decode("ascii")
            image_urls.append(f"data:{attachment.mime_type};base64,{encoded}")

    selected_model_id = body.model_id
    if image_urls and body.mode == "single":
        selected_model = await model_registry.get_model(body.model_id)
        if not selected_model or not selected_model.supports_vision:
            vision_models = await model_registry.get_vision_models()
            if not vision_models:
                raise HTTPException(status_code=422, detail="No image-capable model is configured")
            selected_model_id = vision_models[0].id

    use_web_research = body.web_research or (body.experience_mode == "research" and bool(settings.search_api_key))
    research_results = []
    if use_web_research:
        try:
            research_results = await search_web(body.content)
        except ResearchUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    prior_request = await prisma.message.find_first(where={"client_request_id": request_id, "user_id": user_id})
    if prior_request:
        if prior_request.content:
            return await _completed_response(prior_request, str(prior_request.chat_id))
        raise HTTPException(status_code=409, detail="This request is already being processed")

    chat_id = body.chat_id
    if chat_id:
        chat = await prisma.chat.find_first(where={"id": chat_id, "user_id": user_id})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
    else:
        chat = await prisma.chat.create(data={"user_id": user_id, "title": body.content[:60]})
        chat_id = str(chat.id)

    user_message = await prisma.message.create(data={
        "chat_id": chat_id, "user_id": user_id, "role": "user", "content": body.content,
        "web_research": use_web_research,
    })

    assistant_message = await prisma.message.create(data={
        "chat_id": chat_id, "user_id": user_id, "role": "assistant", "content": "",
        "client_request_id": request_id, "web_research": use_web_research,
    })
    try:
        prior_messages = await prisma.message.find_many(
            where={"chat_id": chat_id, "user_id": user_id, "id": {"not_in": [str(assistant_message.id), str(user_message.id)]}},
            order={"created_at": "desc"}, take=30,
        )
        documents = [{"file_name": item.file_name, "text": item.extracted_text or ""} for item in attachments]
        context_messages = await context_window_manager.build_context(
            user_id=user_id, prior_messages=prior_messages,
            current_user_prompt=body.content, experience_mode=body.experience_mode,
            documents=documents, research_results=research_results,
            image_urls=image_urls or None,
        )
        effective_mode = body.mode
        if body.mode == "goldmine" and not _needs_team_reasoning(body.content, body.experience_mode):
            effective_mode = "single"
        result = await goldmine_engine.process(
            messages=context_messages, user_prompt=body.content,
            chat_id=chat_id, message_id=str(assistant_message.id),
            model_id=selected_model_id, mode=effective_mode,
            has_image=bool(image_urls),
            progress_callback=emit,
        )
        for attachment in attachments:
            await prisma.attachment.update(where={"id": str(attachment.id)}, data={"message_id": str(user_message.id)})
        await prisma.message.update(where={"id": str(assistant_message.id)}, data={
            "content": result.selected_response.content,
            "provider_failures": Json(result.provider_failures) if result.provider_failures else None,
        })
        # The message content is the durable user-facing result. Detailed model
        # analytics must never make a completed answer disappear if their schema
        # is temporarily out of sync with the deployed database.
        try:
            for response in result.all_responses:
                response_data = {
                    "id": response.id, "message_id": str(assistant_message.id),
                    "model_id": response.model_id, "provider": response.provider,
                    "content": response.content, "goldmine_score": response.goldmine_score,
                    "selected": response.selected, "latency_ms": response.latency_ms,
                    "web_verified": False, "response_type": response.response_type,
                    "selection_explanation": result.selection_explanation if response.selected else None,
                }
                if response.evaluation_signals:
                    response_data["evaluation_signals"] = Json(response.evaluation_signals.model_dump())
                await prisma.modelresponse.create(data=response_data)
            for source in research_results:
                await prisma.source.create(data={
                    "id": str(uuid.uuid4()), "message_id": str(assistant_message.id),
                    "title": source["title"], "url": source["url"], "domain": source["domain"],
                    "relevance_score": source["relevance_score"], "support_type": source["support_type"],
                })
        except Exception as exc:
            logger.exception("Could not persist optional Goldmine metadata (%s)", type(exc).__name__)
        await prisma.chat.update(where={"id": chat_id}, data={"title": chat.title})
        persisted_responses = [response.model_dump() for response in result.all_responses]
        source_payload = [{key: source[key] for key in ("title", "url", "domain", "relevance_score", "support_type")} for source in research_results]
        return {
            "chat_id": chat_id, "message_id": str(assistant_message.id),
            "content": result.selected_response.content,
            "selected_response": result.selected_response.model_dump(),
            "all_responses": persisted_responses,
            "sources": source_payload,
            "goldmine_score": result.goldmine_score,
            "selection_explanation": result.selection_explanation,
            "web_verified": False,
            "synthesis_model_id": result.synthesis_model_id,
            "synthesis_status": result.synthesis_status,
            "provider_failures": result.provider_failures,
        }
    except HTTPException:
        await prisma.message.delete(where={"id": str(assistant_message.id)})
        raise
    except asyncio.CancelledError:
        await prisma.message.delete(where={"id": str(assistant_message.id)})
        raise
    except Exception as exc:
        logger.exception("Goldmine response generation failed (%s)", type(exc).__name__)
        await prisma.message.delete(where={"id": str(assistant_message.id)})
        raise HTTPException(status_code=500, detail="Goldmine could not generate a response. Check provider configuration and try again.") from exc


@router.post("/chat")
async def send_message(body: MessageCreateRequest, user=Depends(get_current_user)):
    return await _execute_chat(body, user)


@router.post("/chat/stream")
async def stream_message(body: MessageCreateRequest, user=Depends(get_current_user)):
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict):
        await queue.put(event)

    async def event_stream():
        task = asyncio.create_task(_execute_chat(body, user, emit=emit))
        try:
            while not task.done() or not queue.empty():
                if not queue.empty():
                    item = queue.get_nowait()
                    yield f"data: {json.dumps({'event': 'progress', 'data': item}, ensure_ascii=False)}\n\n"
                    continue
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.2)
                    yield f"data: {json.dumps({'event': 'progress', 'data': item}, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    continue
            payload = await task
            yield f"data: {json.dumps({'event': 'complete', 'data': payload}, ensure_ascii=False)}\n\n"
        except HTTPException as exc:
            yield f"data: {json.dumps({'event': 'error', 'data': {'detail': exc.detail, 'status': exc.status_code}}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            task.cancel()
            raise
        except Exception as exc:
            logger.error("Streaming chat failed (%s)", type(exc).__name__)
            if type(exc).__name__ == "DataError":
                detail = "The chat database schema is out of date. Apply Supabase migration 008_research_upload_synthesis.sql, then retry."
            else:
                detail = "The response was interrupted. Please retry."
            yield f"data: {json.dumps({'event': 'error', 'data': {'detail': detail}}, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive",
    })
