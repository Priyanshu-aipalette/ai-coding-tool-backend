from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import google.generativeai as genai
from routes.chat import chat_router
from routes.health import health_router
from memory_store import MemoryStore

# Load environment variables
load_dotenv()

# Initialize memory store
memory_store = MemoryStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Gemini API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")

    genai.configure(api_key=api_key)

    # Store memory_store in app state for access in routes
    app.state.memory_store = memory_store

    yield

    # Cleanup if needed
    pass


# Initialize FastAPI app
app = FastAPI(
    title="AI Coding Agent API",
    description="A Claude-style AI Coding Agent backend using Gemini 2.5 API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],  # React dev servers
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "AI Coding Agent API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
