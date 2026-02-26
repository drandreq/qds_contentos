import logging
import json
import os
from typing import Optional
from langchain_core.tools import tool
from core.chroma_store import chroma_store
from core.atomic_filesystem import atomic_fs

logger = logging.getLogger(__name__)

@tool
def search_knowledge_tool(query: str, dimension_filter: Optional[str] = None) -> str:
    """
    Search the ContentOS Vault (via ChromaDB) for relevant facts, previous lessons, or concepts to bridge knowledge gaps.
    
    Args:
        query: The semantic search query (e.g., "cortisol limit in dogs", "how to hook on linkedin").
        dimension_filter: Optional. A specific Heptatomo dimension to filter by (e.g., "logos", "techne").
                          If provided, only returns results where that dimension has a weight > 0.0.
    """
    logger.info(f"Agent executing search_knowledge_tool for query: '{query}', filter: {dimension_filter}")
    try:
        where_clause = None
        if dimension_filter:
            # Enforce lowercase for schema matching
            dim = dimension_filter.lower()
            if dim in ["logos", "techne", "ethos", "bios", "strategos", "polis", "pathos"]:
                where_clause = {dim: {"$gt": 0.0}}
                
        results = chroma_store.query_by_dimensions(
            query_texts=[query],
            n_results=3,
            where=where_clause
        )
        
        # Format results for the LLM
        if not results or not results.get("documents") or not results["documents"][0]:
            return "No relevant knowledge found in the Vault for this query."
            
        formatted_results = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            doc_id = results["ids"][0][i]
            formatted_results.append(f"--- Document ID: {doc_id} ---\n{doc}\n(Metadata: {meta})")
            
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Search knowledge tool failed: {e}")
        return f"Error executing search: {str(e)}"

@tool
def apply_dimension_tool(filepath: str, dimension_to_inject: str, instructions: str) -> str:
    """
    Actively rewrite a specific file in the Vault by injecting or enhancing a specific Heptatomo dimension.
    The updated text is saved atomically back to the file system.
    
    Args:
        filepath: The absolute or Vault-relative path to the raw text or JSON file (e.g., "03_voice/voice_123.json").
        dimension_to_inject: The Heptatomo dimension to focus on (e.g., "LOGOS", "TECHNE").
        instructions: Specific instructions on how to rewrite the text (e.g., "Add a paragraph explaining the biological process of cortisol to ground the PATHOS with LOGOS").
    """
    logger.info(f"Agent executing apply_dimension_tool on {filepath} for dimension {dimension_to_inject}")
    try:
        vault_base = "/vault"
        # Sanitize and resolve path
        safe_path = filepath
        if safe_path.startswith("/vault/"):
            safe_path = safe_path.replace("/vault/", "", 1)
        elif safe_path.startswith("vault/"):
            safe_path = safe_path.replace("vault/", "", 1)
            
        full_path = os.path.abspath(os.path.join(vault_base, safe_path))
        if not full_path.startswith(vault_base):
            return "Error: Cannot access files outside the Vault."
            
        # Read the artifact
        content = atomic_fs.read_file(safe_path)
        
        # Extract text if it's JSON
        is_json = safe_path.endswith(".json")
        raw_text = content
        metadata_dict = {}
        
        if is_json:
            metadata_dict = json.loads(content)
            # Find the text payload (either Slides or Raw Text)
            if "raw_text" in metadata_dict:
                raw_text = metadata_dict["raw_text"]
            elif "slides" in metadata_dict:
                # Naive join for simplicity
                raw_text = "\n\n".join([s.get("content", "") for s in metadata_dict["slides"]])
            elif "raw_markdown" in metadata_dict:
                raw_text = metadata_dict["raw_markdown"]
            else:
                return "Error: JSON format not supported for direct rewriting."

        # Use Gemini to perform the actual rewrite
        from core.authenticator import authenticator
        from google.genai import types
        
        prompt = (
            f"Você é um Ghostwriter especialista na Teoria Heptatomo. "
            f"Reescreva o texto abaixo para injetar e fortalecer a dimensão '{dimension_to_inject.upper()}'.\n"
            f"Instruções Específicas: {instructions}\n\n"
            f"Integre a nova dimensão de forma orgânica. Não mude o idioma original.\n\n"
            f"TEXTO ORIGINAL:\n{raw_text}"
        )
        
        response = authenticator.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
        
        rewritten_text = response.text
        
        # Save it back
        if is_json:
            # Update the appropriate field
            if "raw_text" in metadata_dict:
                metadata_dict["raw_text"] = rewritten_text
            elif "raw_markdown" in metadata_dict:
                metadata_dict["raw_markdown"] = rewritten_text
            # Increment the version hash to respect atomic tracking
            atomic_fs.write_file(safe_path, json.dumps(metadata_dict, indent=2))
        else:
            atomic_fs.write_file(safe_path, rewritten_text)
            
        return f"Success. Document {filepath} has been rewritten and saved atomically with enhanced {dimension_to_inject.upper()}."

    except FileNotFoundError:
        return f"Error: File {filepath} not found in the Vault."
    except Exception as e:
        logger.error(f"Apply dimension tool failed: {e}", exc_info=True)
        return f"Error applying dimension override: {str(e)}"
