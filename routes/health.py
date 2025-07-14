from fastapi import APIRouter, Depends, Request
from models.chat_models import HealthResponse

health_router = APIRouter()


@health_router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint"""
    memory_store = request.app.state.memory_store

    return HealthResponse(
        status="healthy", active_sessions=memory_store.get_session_count()
    )
