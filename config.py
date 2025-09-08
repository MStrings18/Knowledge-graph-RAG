# config.py

import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# === Credentials ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")

# === Base Paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")
CHUNKS_PATH = os.path.join(DATA_DIR, "chunks.json")
BM25_PATH = os.path.join(DATA_DIR, "bm25_corpus.pkl")

VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore")
LANCEDB_DIR = os.path.join(VECTORSTORE_DIR, "lancedb")
LANCEDB_TABLE_NAME = "pandas_docs"  # optional, used if needed
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "vectorstore", "faiss_index")

# === Chunking Config ===
CHUNK_SIZE = 600
CHUNK_OVERLAP = 150

# === Hybrid Retriever Config ===
ALPHA = 0.5  # Weight for vector score in ensemble retriever

# === Reranker Config ===
ENABLE_RERANKING = False

# === Gemini LLM Config ===
PRO_MODEL_NAME = "gemini-2.5-flash"
FLASH_MODEL_NAME = "gemini-2.5-flash-lite"

MAX_TOKENS = 30000