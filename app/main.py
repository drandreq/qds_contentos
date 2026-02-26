import logging
import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from contextlib import asynccontextmanager
from core.authenticator import authenticator
from core.mp_dialect_parser import compiler
from core.atomic_filesystem import atomic_fs
from core.telegram_handler import telegram_bot

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
        
    # Sprint 5: Initialize and Start Telegram Bot
    try:
        telegram_bot.initialize()
        await telegram_bot.start_ptb()
    except Exception as e:
        logger.error(f"Failed to start Telegram Bot: {e}")
    
    yield
    
    # Clean up (if needed)
    logger.info("Shutting down ContentOS.")
    await telegram_bot.stop_ptb()

contentos_application = FastAPI(
    title="ContentOS",
    description="High-integrity production pipeline for medical and technical content.",
    version="1.0.0",
    lifespan=lifespan
)

@contentos_application.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    Sprint 5: Telegram Webhook Ingestion
    Receives payloads directly from the Telegram API.
    """
    return await telegram_bot.process_update(request)

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

class CompileRequest(BaseModel):
    filepath: str

@contentos_application.post("/v1/compile")
async def compile_markdown(request: CompileRequest):
    """
    Sprint 4: Atomic Versioning & Compilation
    Compiles a Markdown file into a JSON Sovereign Pair.
    Saves the JSON back to the vault atomically.
    """
    try:
        # Resolve path
        vault_base = "/vault"
        # Prevent traversal
        full_path = os.path.abspath(os.path.join(vault_base, request.filepath))
        if not full_path.startswith(vault_base):
            raise HTTPException(status_code=400, detail="Invalid filepath: Cannot traverse outside /vault")
            
        logger.info(f"Received compile request for: {full_path}")
        
        # Compile via MPDialectParser (Sprint 3)
        try:
            metadata = compiler.parse_markdown_file(full_path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"File not found: {request.filepath}")
            
        # Sprint 4: Atomic Write
        # Determine the JSON sovereign path
        json_filename = os.path.splitext(request.filepath)[0] + ".json"
        json_content = metadata.model_dump_json(indent=2)
        
        # Use AtomicFileSystem to securely write
        written_path = atomic_fs.write_file(json_filename, json_content)
        
        # Conform to CompilationResult model defined in models.py
        from core.models import CompilationResult
        result = CompilationResult(
            source_path=request.filepath,
            metadata_path=json_filename,
            metadata=metadata
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compilation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
