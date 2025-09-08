# chunker.py

import os
import json
import nltk
from typing import List, Dict
import pdfplumber
from nltk.tokenize import sent_tokenize
from config import CHUNKS_PATH, CHUNK_SIZE, CHUNK_OVERLAP, DOCUMENTS_DIR

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')


def split_into_chunks(text: str, page_number: int) -> List[Dict]:
    """Split text into semantic-aware overlapping chunks with page metadata."""
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = []
    total_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if total_len + sentence_len <= CHUNK_SIZE:
            current_chunk.append(sentence)
            total_len += sentence_len
        else:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "metadata": {"page": page_number}
                })

            # Start new chunk with overlap
            overlap_sentences = []
            overlap_len = 0
            for s in reversed(current_chunk):
                overlap_len += len(s)
                overlap_sentences.insert(0, s)
                if overlap_len >= CHUNK_OVERLAP:
                    break

            current_chunk = overlap_sentences + [sentence]
            total_len = sum(len(s) for s in current_chunk)

    # Add last chunk
    if current_chunk:
        chunks.append({
            "content": " ".join(current_chunk).strip(),
            "metadata": {"page": page_number}
        })

    return chunks


def chunk_pdf(file_path: str) -> List[Dict]:
    """Main entrypoint to extract and chunk PDF pages."""
    if os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    all_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                page_chunks = split_into_chunks(text, i + 1)
                all_chunks.extend(page_chunks)

    # === Deduplication: Remove chunks that are subsets of others on the same page ===
    deduped_chunks = []
    for i, chunk_i in enumerate(all_chunks):
        content_i = chunk_i["content"]
        page_i = chunk_i["metadata"]["page"]
        is_subset = False

        for j, chunk_j in enumerate(all_chunks):
            if i != j and chunk_j["metadata"]["page"] == page_i:
                content_j = chunk_j["content"]
                if content_i in content_j:
                    is_subset = True
                    break

        if not is_subset:
            deduped_chunks.append(chunk_i)

    # Save to disk
    # os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
    # with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
    #     json.dump(deduped_chunks, f, ensure_ascii=False, indent=2)

    return deduped_chunks

