import os
import sys

# Ensure the correct app directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.models import HeptatomoTensor
from core.chroma_store import chroma_store

def verify_chromadb():
    print("--- Starting ChromaDB FVT ---")
    
    # Initialize the GenAI Authenticator so Chroma can generate embeddings
    from core.authenticator import authenticator
    authenticator.initialize()
    
    # 1. Create Mock Content
    doc1_id = "lesson_01"
    doc1_text = "This lesson covers the SUS healthcare system policies and its societal impact."
    doc1_tensor = HeptatomoTensor(
        logos=0.5, techne=0.2, ethos=0.7, bios=0.4, strategos=0.3, polis=0.9, pathos=0.6
    )
    
    doc2_id = "lesson_02"
    doc2_text = "Let's dive into Python coding architecture and data structures for building pipelines."
    doc2_tensor = HeptatomoTensor(
        logos=0.8, techne=0.9, ethos=0.2, bios=0.1, strategos=0.5, polis=0.1, pathos=0.1
    )
    
    doc3_id = "lesson_03"
    doc3_text = "A hybrid lesson on engineering a public health data system."
    doc3_tensor = HeptatomoTensor(
        logos=0.7, techne=0.8, ethos=0.5, bios=0.5, strategos=0.4, polis=0.85, pathos=0.2
    )

    # 2. Index Content
    print("Indexing documents...")
    chroma_store.index_content(doc1_id, doc1_text, doc1_tensor, {"title": "SUS Overview"})
    chroma_store.index_content(doc2_id, doc2_text, doc2_tensor, {"title": "Python Architecture"})
    chroma_store.index_content(doc3_id, doc3_text, doc3_tensor, {"title": "Public Health Engineering"})

    # 3. Query Content (Semantic + Dimensional Filter)
    print("\nQuerying: 'systems planning'")
    print("Filter: POLIS > 0.8 AND TECHNE > 0.4")
    
    # In ChromaDB, the $and operator lets us combine dimensional filters
    dimensional_query = {
        "$and": [
            {"polis": {"$gt": 0.8}},
            {"techne": {"$gt": 0.4}}
        ]
    }
    
    results = chroma_store.query_by_dimensions(
        query_texts=["systems planning"],
        n_results=2,
        where=dimensional_query
    )
    
    print("\nResults:")
    for i, doc_id in enumerate(results['ids'][0]):
        dist = results['distances'][0][i]
        meta = results['metadatas'][0][i]
        text = results['documents'][0][i]
        print(f"[{doc_id}] (Distance: {dist:.4f})")
        print(f"   Text: {text}")
        print(f"   POLIS: {meta['polis']}, TECHNE: {meta['techne']}")
        
    # Assertions
    returned_ids = results['ids'][0]
    if "lesson_03" in returned_ids and "lesson_01" not in returned_ids and "lesson_02" not in returned_ids:
        print("\n✅ FVT PASSED: Only the lesson matching both dimensional constraints was returned!")
    else:
        print("\n❌ FVT FAILED: Dimensional constraints were not strictly applied.")

if __name__ == "__main__":
    verify_chromadb()
