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

# Path configuration with environment variable support
DATA_DIR = os.getenv("DATA_DIR") or os.path.join(BASE_DIR, "data")
DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR") or os.path.join(DATA_DIR, "documents")
CHUNKS_PATH = os.getenv("CHUNKS_PATH") or os.path.join(DATA_DIR, "chunks.txt")

# === Chunking Config ===
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# === Keyword Filtering ===
# Define the percentage threshold. Keywords appearing in more than this
# percentage of chunks will be considered too generic and removed.
# A good starting point is between 0.15 (15%) and 0.30 (30%).
FREQUENCY_THRESHOLD = float(os.getenv("FREQUENCY_THRESHOLD", "0.03"))  # 3%

# Define a set of essential keywords to protect from filtering,
# even if they are very frequent.
KEEP_LIST = {}

# === Neo4j settings ===
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# --- Retrieval Settings ---
TOP_K_KEYWORDS = int(os.getenv("TOP_K_KEYWORDS", "1"))      # number of top keyword matches
MAX_DEPTH = int(os.getenv("MAX_DEPTH", "1"))               # maximum graph depth for chunk expansion

# === Reranker Config ===
ENABLE_RERANKING = os.getenv("ENABLE_RERANKING", "false").lower() == "true"

# === Gemini LLM Config ===
PRO_MODEL_NAME = os.getenv("PRO_MODEL_NAME", "gemini-2.5-flash")
FLASH_MODEL_NAME = os.getenv("FLASH_MODEL_NAME", "gemini-2.5-flash-lite")

MAX_TOKENS = int(os.getenv("MAX_TOKENS", "30000"))