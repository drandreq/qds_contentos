import os
import logging
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.config import Settings
from core.authenticator import authenticator
from core.models import HeptatomoTensor

logger = logging.getLogger(__name__)

class ChromaManager:
    """
    Sprint 9: Dimensional Memory using ChromaDB.
    Persists data in vault/.chroma/ and uses HeptatomoTensor for metadata.
    """
    def __init__(self):
        # Establish persistence path inside the Vault volume
        self.persist_directory = os.path.abspath(os.path.join(os.getcwd(), "vault", ".chroma"))
        os.makedirs(self.persist_directory, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB connection at {self.persist_directory}")
        
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # We will use Chroma's highly efficient default embedding function (all-MiniLM-L6-v2) for now 
        # to guarantee robust offline indexing behavior while ensuring structural layout.
        from chromadb.utils import embedding_functions
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create the main dimension collection
        self.collection = self.client.get_or_create_collection(
            name="contentos_heptatomo",
            embedding_function=self.embedding_function,
            metadata={"description": "The 7D Connectome Vault"}
        )

    def index_content(self, document_id: str, text: str, tensor: HeptatomoTensor, additional_metadata: Dict[str, Any] = None):
        """
        Indexes a piece of content into Chroma using Gemini embeddings, 
        saving its 7D Tensor weights explicitly as metadata for semantic filtering.
        """
        if additional_metadata is None:
            additional_metadata = {}
            
        # Serialize the Heptatomo Tensor directly into the top-level metadata dict
        # This enables powerful filtering syntax like `{"polis": {"$gt": 0.8}}`
        metadata = {
            "logos": tensor.logos,
            "techne": tensor.techne,
            "ethos": tensor.ethos,
            "bios": tensor.bios,
            "strategos": tensor.strategos,
            "polis": tensor.polis,
            "pathos": tensor.pathos,
            **additional_metadata
        }
        
        logger.info(f"Indexing document {document_id} into ChromaDB...")
        
        self.collection.add(
            ids=[document_id],
            documents=[text],
            metadatas=[metadata]
        )
        logger.info(f"Successfully indexed document {document_id}.")

    def query_by_dimensions(self, query_texts: List[str], n_results: int = 5, where: Dict[str, Any] = None) -> Any:
        """
        Perform a semantic similarity search, filtered by exact Heptatomo dimensional constraints.
        Example where clause: {"polis": {"$gt": 0.8}}
        """
        logger.info(f"Querying ChromaDB. n_results={n_results}, filter={where}")
        results = self.collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where
        )
        return results

# Singleton instance
chroma_store = ChromaManager()
