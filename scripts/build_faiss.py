"""
build_faiss.py – Build both agriculture and schemes FAISS indexes.
"""
import sys
import os

# Allow importing rag package from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.config import logger
from rag.document_loader import load_documents
from rag.chunker import chunk_document
from rag.embeddings import EmbeddingModel
from rag.faiss_store import build_index


def main():
    logger.info("=" * 60)
    logger.info("NAMMA KRUSHI – FAISS Index Builder")
    logger.info("=" * 60)

    # Step 1: Load documents
    docs = load_documents()
    logger.info(f"Loaded {len(docs)} documents")

    # Step 2: Chunk documents and separate by index
    # taxonomy: agriculture index gets agriculture, disease, pest, farmer_advisory
    # schemes index gets scheme
    agriculture_cats = {"agriculture", "disease", "pest", "farmer_advisory"}
    scheme_cats = {"scheme"}

    ag_chunks = []
    sc_chunks = []
    ag_doc_count = 0
    sc_doc_count = 0

    for doc in docs:
        chunks = chunk_document(doc)
        cat = doc["category"]
        if cat in agriculture_cats:
            ag_chunks.extend(chunks)
            ag_doc_count += 1
        elif cat in scheme_cats:
            sc_chunks.extend(chunks)
            sc_doc_count += 1
        else:
            # Default to agriculture
            ag_chunks.extend(chunks)
            ag_doc_count += 1

    logger.info(f"Agriculture: {ag_doc_count} docs -> {len(ag_chunks)} chunks")
    logger.info(f"Schemes:     {sc_doc_count} docs -> {len(sc_chunks)} chunks")

    # Step 3: Load embedding model
    model = EmbeddingModel.get()

    # Step 4: Embed and build agriculture index
    logger.info("Embedding agriculture chunks...")
    ag_texts = [c.text for c in ag_chunks]
    ag_embeddings = model.embed(ag_texts)
    build_index(ag_chunks, ag_embeddings, "agriculture", ag_doc_count)

    # Step 5: Embed and build schemes index
    logger.info("Embedding schemes chunks...")
    sc_texts = [c.text for c in sc_chunks]
    sc_embeddings = model.embed(sc_texts)
    build_index(sc_chunks, sc_embeddings, "schemes", sc_doc_count)

    # Step 6: Summary
    logger.info("=" * 60)
    logger.info("BUILD COMPLETE")
    logger.info(f"  Agriculture: {len(ag_chunks)} chunks, dim={ag_embeddings.shape[1]}")
    logger.info(f"  Schemes:     {len(sc_chunks)} chunks, dim={sc_embeddings.shape[1]}")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Build failed: {e}")
        sys.exit(1)
