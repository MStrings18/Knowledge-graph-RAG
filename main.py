import os
from time import time

from config import DOCUMENTS_DIR, CHUNKS_PATH, TOP_K_KEYWORDS, MAX_DEPTH
from chunker import chunk_pdf
from ner_extractor import extract_keywords
from graph_builder import KnowledgeGraphBuilder
from graph_retriever import GraphRetriever

import torch


def verify_gpu():
    if torch.cuda.is_available():
        print("✅ PyTorch detected CUDA GPU")
        print(f"Device Count: {torch.cuda.device_count()}")
        print(f"Current Device: {torch.cuda.current_device()}")
        print(f"Device Name: {torch.cuda.get_device_name(torch.cuda.current_device())}")
    else:
        print("❌ No GPU detected; running on CPU")


if __name__ == "__main__":
    start_time = time()
    verify_gpu()

    # --- 1. Chunk PDF ---
    chunks = chunk_pdf(os.path.join(DOCUMENTS_DIR, "sample.pdf"))
    print(f"Loaded {len(chunks)} chunks.")

    # --- 2. Extract keywords from entire doc ---
    keywords = extract_keywords("\n\n".join(chunks))
    print(f"Extracted {len(keywords)} unique keywords/entities")

    # --- 3. Build Knowledge Graph ---
    kg = KnowledgeGraphBuilder()
    kg.clear_graph()
    print("Cleared existing graph.")
    kg.build_graph(chunks, keywords)
    kg.close()
    print("Knowledge graph built successfully.")

    # --- 4. Query the Graph using semantic retriever ---
    from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
    from graph_retriever import GraphRetriever

    retriever = GraphRetriever(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
    query_text = "Tell me about Civil Union Partner"
    retrieved_chunks = retriever.retrieve(query_text)

    print(f"\nRetrieved {len(retrieved_chunks)} chunks for query: '{query_text}'\n")
    for c in retrieved_chunks:
        print(f"Chunk ID: {c['id']}\nContent: {c['content']}\n---")

    retriever.close()

    print(f"\nTotal Script Execution Time: {time() - start_time:.2f} seconds")
