# ner_extractor.py

import re
from typing import List
import string

import spacy
import yake
from nltk.corpus import stopwords
import nltk
from spacy.tokens import Doc, Span, Token

nltk.download("stopwords", quiet=True)
STOPWORDS = set(stopwords.words("english"))
STOPWORDS.add('pg_no') # Standardized to lowercase
STOPWORDS.add('cnk')

YAKE_MAX_NGRAM_SIZE = 3
YAKE_NUM_KEYWORDS = 40
YAKE_DEDUP_THRESHOLD = 0.9

# --- OPTIMIZATION 1: Use a faster spaCy model ---
# en_core_web_trf is very slow. 'lg' is a great balance of speed and accuracy.
print("Loading spaCy model...")
nlp = spacy.load("en_core_web_lg")
print("Model loaded.")


# ----------------------------
# Preprocessing
# ----------------------------
def clean_text(text: str) -> str:
    # These regexes are fine, no major changes needed
    text = re.sub(r"\n\d+\s*\n", " ", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ----------------------------
# Helpers (Refactored for efficiency)
# ----------------------------

# --- OPTIMIZATION 2: Normalize from pre-processed spaCy objects, not raw strings ---
def normalize_span(span: Span) -> str:
    """
    Normalizes a spaCy Span object by lemmatizing its nouns/proper nouns.
    This avoids re-running the nlp pipeline.
    """
    tokens = [
        token.lemma_.lower()
        for token in span
        if token.pos_ in {"NOUN", "PROPN"} and token.text.lower() not in STOPWORDS
    ]
    if not tokens:
        return ""
    
    normalized = " ".join(tokens)
    # Punctuation and space cleaning remains the same
    normalized = normalized.translate(str.maketrans("", "", string.punctuation))
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()

def is_valid_keyword(kw: str) -> bool:
    kw = kw.strip()
    if not kw:
        return False
    tokens = kw.split()
    if all(t in STOPWORDS or t in string.punctuation for t in tokens):
        return False
    # Check character length *after* removing spaces
    if len("".join(tokens)) <= 2:
        return False
    return True

# ----------------------------
# Extractor Functions (Refactored to accept a spaCy Doc)
# ----------------------------

def extract_yake(text: str) -> List[str]:
    kw_extractor = yake.KeywordExtractor(
        lan="en",
        n=YAKE_MAX_NGRAM_SIZE,
        dedupLim=YAKE_DEDUP_THRESHOLD,
        top=YAKE_NUM_KEYWORDS,
        features=None,
    )
    keywords = kw_extractor.extract_keywords(text)
    cleaned = []
    for kw, score in keywords:
        # We still need to process YAKE's raw strings, but this is the only place.
        # We use nlp.pipe for efficiency if we were processing many at once.
        # For now, a single nlp() call per keyword is acceptable here.
        doc = nlp(kw)
        phrase = normalize_span(doc[:]) # Pass the whole doc as a span
        if is_valid_keyword(phrase):
            cleaned.append(phrase)
    return cleaned


def extract_names_regex(text: str) -> List[str]:
    candidates = set()
    proper_case = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b", text)
    candidates.update(proper_case)
    all_caps = re.findall(r"\b(?:[A-Z]{2,}(?:\s|$)){2,}\b", text)
    candidates.update([a.strip() for a in all_caps])
    
    normalized = []
    # Use nlp.pipe for batch processing, which is much faster than a loop
    docs = nlp.pipe(list(candidates))
    for doc in docs:
        phrase = normalize_span(doc[:]) # Pass the whole doc as a span
        if is_valid_keyword(phrase):
            normalized.append(phrase)
    return normalized


def extract_spacy(doc: Doc) -> List[str]:
    """
    This function now accepts a pre-processed spaCy Doc object.
    This is the most significant optimization.
    """
    results = set() # Use a set to handle duplicates automatically

    # Named entities
    for ent in doc.ents:
        phrase = normalize_span(ent)
        if is_valid_keyword(phrase):
            results.add(phrase)

    # Noun chunks
    for chunk in doc.noun_chunks:
        if chunk.root.pos_ in {"NOUN", "PROPN"}:
            phrase = normalize_span(chunk)
            if is_valid_keyword(phrase):
                results.add(phrase)

    # Single token nouns/proper nouns
    for token in doc:
        if token.pos_ in {"NOUN", "PROPN"} and not token.is_stop:
            lemma = token.lemma_.lower()
            if is_valid_keyword(lemma):
                results.add(lemma)

    return list(results)


# ----------------------------
# Deduplication (This logic is generally fine, but can be slow on very large lists)
# ----------------------------
def deduplicate_keywords(keywords: List[str]) -> List[str]:
    """Keeps longer phrases that are not subsets of other phrases."""
    # Sort by length descending
    keywords.sort(key=len, reverse=True)
    
    # Use a set of words for faster checking
    final_keywords = []
    superstrings = set()

    for kw in keywords:
        # Check if the keyword is a substring of any already added longer keyword
        if not any(kw in s for s in superstrings):
            final_keywords.append(kw)
            superstrings.add(kw)
            
    return final_keywords


# ----------------------------
# Unified (Refactored and Consolidated)
# ----------------------------
def extract_keywords(text: str) -> List[str]:
    """Extracts, normalizes, and deduplicates keywords from a raw text string."""
    clean_doc_text = clean_text(text)

    # --- OPTIMIZATION 3: Process the document ONCE with spaCy ---
    doc = nlp(clean_doc_text)

    # Run extractors
    yake_keywords = extract_yake(clean_doc_text)
    spacy_entities = extract_spacy(doc) # Pass the Doc object
    regex_names = extract_names_regex(clean_doc_text)

    # Combine and get unique keywords
    combined = set(yake_keywords + spacy_entities + regex_names)
    
    # Deduplicate by subset filtering
    final_keywords = deduplicate_keywords(list(combined))

    return final_keywords

# --- Renamed for clarity and consolidated logic ---
def extract_keywords_from_document(file_path: str) -> List[str]:
    """Extracts keywords from a document file."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return extract_keywords(text)


# ----------------------------
# Example
# ----------------------------
if __name__ == "__main__":
    file_path = "data/chunks.txt"  # Make sure this file exists
    try:
        keywords = extract_keywords_from_document(file_path=file_path)
        print(f"Extracted {len(keywords)} final keywords/entities:\n")
        for kw in keywords:
            print("-", kw)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")