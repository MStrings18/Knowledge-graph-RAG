# chunker.py

import os
import nltk
import pdfplumber
from nltk.tokenize import sent_tokenize
from typing import List
import hashlib
from config import CHUNKS_PATH, CHUNK_SIZE, CHUNK_OVERLAP, DOCUMENTS_DIR

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")


def split_into_chunks(text: str, page_number: int):
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
            chunk_text = f"Pg_no {page_number}: " + " ".join(current_chunk).strip()
            chunks.append({
                "content": chunk_text,
                "chunk_id": hashlib.md5(chunk_text.encode()).hexdigest()
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

    if current_chunk:
        chunk_text = f"Pg_no {page_number}: " + " ".join(current_chunk).strip()
        chunks.append({
            "content": chunk_text,
            "chunk_id": hashlib.md5(chunk_text.encode()).hexdigest()
        })

    return chunks



def chunk_pdf(file_path: str) -> List[str]:
    """Main entrypoint to extract and chunk PDF pages, saves to chunks.txt instead of JSON."""
    # if os.path.exists(CHUNKS_PATH):
    #     with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    #         return f.read().split('\n\n')

    all_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                page_chunks = split_into_chunks(text, i + 1)
                all_chunks.extend(page_chunks)

    # Deduplicate chunks on the same page
    deduped_chunks = []
    for i, chunk_i in enumerate(all_chunks):
        content_i = chunk_i["content"]
        is_subset = False
        for j, chunk_j in enumerate(all_chunks):
            if i != j:
                content_j = chunk_j["content"]
                if content_i in content_j:
                    is_subset = True
                    break
        if not is_subset:
            deduped_chunks.append(chunk_i)


    # Save to disk as .txt
    os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        f.write("\n\n".join([chunk["content"] for chunk in deduped_chunks]))


    return [chunk["content"] for chunk in deduped_chunks]
