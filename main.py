import os
from time import time

from config import DOCUMENTS_DIR, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
from chunker import chunk_pdf
from ner_extractor import map_keywords_to_chunks
from keyword_filter import filter_keys
from graph_builder import KnowledgeGraphBuilder
from graph_retriever import GraphRetriever
from gemini_client import generate_answer
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
    key_chunk_map = map_keywords_to_chunks(chunks)
    print(f"NER keywords {len(key_chunk_map.keys())} unique keywords/entities")
    filtered_map = filter_keys(key_chunk_map,len(chunks))
    print(f"Filterd {len(filtered_map.keys())} unique keywords/entities")
    keywords = sorted(filtered_map.keys())
    # for key in keywords:
    #     print(key)

    # --- 3. Build Knowledge Graph ---
    kg = KnowledgeGraphBuilder()
    kg.clear_graph()
    print("Cleared existing graph.")
    kg.build_graph_from_map(filtered_map)
    kg.close()
    print("Knowledge graph built successfully.")
    print(f"\nTotal Preprocessing: {time() - start_time:.2f} seconds")

    # --- 4. Query the Graph using semantic retriever ---    
    retriever = GraphRetriever(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE, keywords)
    query_text = "What are considered high risk hobbies?"
    retrieved_chunks = retriever.retrieve(query_text)

    print(f"\nRetrieved {len(retrieved_chunks)} chunks for query: '{query_text}'\n")
    # for c in retrieved_chunks:
    #     print(f"Chunk ID: {c['id']}\nContent: {c['content']}\n---")
    retriever.close()

    # --- 5. Augmented Generation ---
    answer = generate_answer(query_text,retrieved_chunks)
    print('----------')
    print('ANSWER:')
    print(answer)
    print('----------')

    print(f"\nTotal Script Execution Time: {time() - start_time:.2f} seconds")
