import logging
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from core.authenticator import authenticator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sprint 2: Initialize Google AI Authenticator
    logger.info("Starting up ContentOS. Initializing Google AI SDK...")
    try:
        authenticator.initialize()
        logger.info(f"Google AI SDK initialized using {authenticator.auth_layer_used} layer.")
    except Exception as e:
        logger.error(f"Failed to initialize Google AI SDK: {e}")
        # Note: We do not hard-crash the API here so the health check can report the failure
    
    yield
    
    # Clean up (if needed)
    logger.info("Shutting down ContentOS.")

contentos_application = FastAPI(
    title="ContentOS",
    description="High-integrity production pipeline for medical and technical content.",
    version="1.0.0",
    lifespan=lifespan
)

@contentos_application.get("/health")
async def health_check():
    """
    Returns the operational status of the ContentOS backend,
    including the active authentication layer for Google GenAI.
    """
    auth_status = authenticator.get_status()
    
    return {
        "status": "operational",
        "message": "ContentOS backend standing by.",
        "authenticator": auth_status
    }
