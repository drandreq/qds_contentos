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

class ExportRequest(BaseModel):
    filepath: str # Path to the compiled .json file in the vault
    slide_index: int = 0

@contentos_application.post("/v1/export/png")
async def export_png(request: ExportRequest):
    """
    Sprint 8: Asset Factory
    Receives a path to a compiled JSON inside the vault and a slide index.
    Returns the generated PNG bytes.
    """
    try:
        from core.asset_factory import asset_factory
        from core.models import LessonMetadata
        import json
        from fastapi.responses import Response
        
        vault_base = "/vault"
        full_path = os.path.abspath(os.path.join(vault_base, request.filepath))
        
        if not full_path.startswith(vault_base) or not full_path.endswith(".json"):
            raise HTTPException(status_code=400, detail="Invalid JSON filepath.")
            
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        metadata = LessonMetadata(**data)
        
        if metadata.type != "lesson" or not metadata.slides:
            raise HTTPException(status_code=400, detail="Requested file is not a sequence with slides.")
            
        if request.slide_index < 0 or request.slide_index >= len(metadata.slides):
            raise HTTPException(status_code=404, detail="Slide index out of range.")
            
        slide = metadata.slides[request.slide_index]
        png_bytes = asset_factory.generate_png(slide)
        
        return Response(content=png_bytes, media_type="image/png")
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")
    except Exception as e:
        logger.error(f"Generate PNG failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@contentos_application.post("/v1/export/pptx")
async def export_pptx(request: ExportRequest):
    """
    Sprint 8: Asset Factory
    Receives a path to a compiled JSON inside the vault.
    Returns the entire PPTX presentation bytes.
    """
    try:
        from core.asset_factory import asset_factory
        from core.models import LessonMetadata
        import json
        from fastapi.responses import Response
        
        vault_base = "/vault"
        full_path = os.path.abspath(os.path.join(vault_base, request.filepath))
        
        if not full_path.startswith(vault_base) or not full_path.endswith(".json"):
            raise HTTPException(status_code=400, detail="Invalid JSON filepath.")
            
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        metadata = LessonMetadata(**data)
        
        if metadata.type != "lesson":
            raise HTTPException(status_code=400, detail="Requested file is not a compatible presentation sequence.")
            
        pptx_bytes = asset_factory.generate_pptx(metadata)
        
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename=presentation_{os.path.basename(request.filepath).split('.')[0]}.pptx"
            }
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="JSON File not found.")
    except Exception as e:
        logger.error(f"Generate PPTX failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class AgentAnalyzeRequest(BaseModel):
    filepath: str # Path to the JSON file in the vault

@contentos_application.post("/v1/agent/analyze")
async def analyze_content_agent(request: AgentAnalyzeRequest):
    """
    Sprint 11: Agentic Connectome
    Invokes the Heptatomo LangGraph Agent on a specific vault file.
    """
    try:
        from core.agent_graph import contentos_agent
        from core.models import LessonMetadata, TranscriptionMetadata
        from langchain_core.messages import HumanMessage
        import json
        
        vault_base = "/vault"
        full_path = os.path.abspath(os.path.join(vault_base, request.filepath))
        
        if not full_path.startswith(vault_base) or not full_path.endswith(".json"):
            raise HTTPException(status_code=400, detail="Invalid JSON filepath.")
            
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Extract raw text depending on model type
        raw_text = ""
        if "slides" in data:
            metadata = LessonMetadata(**data)
            raw_text = metadata.raw_markdown or ""
        elif "raw_text" in data:
            meta = TranscriptionMetadata(**data)
            raw_text = meta.raw_text
        else:
            raise HTTPException(status_code=400, detail="Unsupported JSON type. Expected LessonMetadata or TranscriptionMetadata.")
            
        if not raw_text:
            raise HTTPException(status_code=400, detail="No raw text found in the payload to analyze.")
            
        logger.info(f"Invoking Agent for: {request.filepath}")
        
        # Build initial state and run graph
        initial_state = {
            "messages": [HumanMessage(content=raw_text)],
            "document_id": request.filepath
        }
        
        # Async invoke on LangGraph
        result = await contentos_agent.ainvoke(initial_state)
        
        # The last message is the agent's critique
        critique = result["messages"][-1].content
        
        return {
            "source_file": request.filepath,
            "heptatomo_critique": critique
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")
    except Exception as e:
        logger.error(f"Agent analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
