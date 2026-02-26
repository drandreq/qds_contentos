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
def save_document_tool(filepath: str, updated_content: str) -> str:
    """
    Actively save the rewritten or repurposed text back into the Vault file.
    Use this tool ONLY after you have analyzed and rewritten the text yourself.
    
    Args:
        filepath: The absolute or Vault-relative path to the file (e.g., "03_voice/voice_123.json").
        updated_content: The fully rewritten text that should replace the old text in the file.
    """
    logger.info(f"Agent executing save_document_tool on {filepath}")
    try:
        vault_base = "/vault"
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
        is_json = safe_path.endswith(".json")
        
        if is_json:
            metadata_dict = json.loads(content)
            if "raw_text" in metadata_dict:
                metadata_dict["raw_text"] = updated_content
            elif "raw_markdown" in metadata_dict:
                metadata_dict["raw_markdown"] = updated_content
            else:
                return "Error: JSON format not supported for direct rewriting."
                
            atomic_fs.write_file(safe_path, json.dumps(metadata_dict, indent=2))
        else:
            atomic_fs.write_file(safe_path, updated_content)
            
        return f"Success. Document {filepath} has been successfully updated and saved."

    except FileNotFoundError:
        return f"Error: File {filepath} not found in the Vault."
    except Exception as e:
        logger.error(f"Save document tool failed: {e}", exc_info=True)
        return f"Error applying override: {str(e)}"
