# gemini_client.py
import google.generativeai as genai
import re

# Configure Gemini
genai.configure(api_key="AIzaSyBY_9HJewap03dpZxzt5Ktj_U-7koC1SHg")
model = genai.GenerativeModel("gemini-2.5-flash-lite")

def extract_keywords(query: str, keywords: list):
    """
    Extract important keywords from the query using Gemini.
    Returns a list of strings.
    """
    prompt = f"""
From the given list of keywords, extract all the keywords which are HIGHLY relevant to the given query.
Return ONLY the relevant keywords as a comma-separated list. No explanations.
All relevant keywords should be EXACTLY present in the list of keywords provided.
#####
EXAMPLE 1:
- Query: 'Tell me about the benefits of Civil Union Partner and its benefits.'
- List of keywords: ['civil union', 'civil union partner', 'civil union partnership', 'drug addiction', 'due', 'dune buggy', 'duty']
- Relevant keywords: ['civil union partner']
EXAMPLE 2:
- Query: 'How are medical predictive diagnostics improving?'
- List of keywords: ['healthcare', 'prediction', 'analysis', 'machine learning', 'drug abuse']
- Relevant keywords: ['healthcare', 'machine learning']
####
Query: '{query}'
List of keywords: {keywords}
    """
    response = model.generate_content(prompt)
    if not response or not response.text:
        return []
    return clean_keywords_output(response.text)

def filter_keywords(query: str, keywords: list):
    """
    Extract important keywords from the query using Gemini.
    Returns a list of strings.
    """
    prompt = f"""
From the given list of keywords, extract all the keywords which are HIGHLY relevant to the given query.
Return ONLY the relevant keywords as a comma-separated list. No explanations.
All relevant keywords should be EXACTLY present in the list of keywords provided.
Note that these relevant keywords will be used to find information related to the query in a legal document.

#####
EXAMPLE 1:
- Query: 'Tell me about the benefits of Civil Union Partner and its benefits.'
- List of keywords: ['civil union', 'civil union partner', 'civil union partnership', 'drug addiction', 'due', 'dune buggy', 'duty']
- Relevant keywords: ['civil union partner']
EXAMPLE 2:
- Query: 'How are medical predictive diagnostics improving?'
- List of keywords: ['healthcare', 'prediction', 'analysis', 'machine learning', 'drug abuse']
- Relevant keywords: ['healthcare', 'machine learning']
####

Query: '{query}'
List of keywords: {keywords}
    """
    response = model.generate_content(prompt)
    if not response or not response.text:
        return []
    return clean_keywords_output(response.text)


def filter_keywords(query: str, keywords: list):
    """
    Extract important keywords from the query using Gemini.
    Returns a list of strings.
    """
    prompt = f"""
From the given list of keywords, extract all the keywords which are HIGHLY relevant to the given query.
Return ONLY the relevant keywords as a comma-separated list. No explanations.
All relevant keywords should be EXACTLY present in the list of keywords provided.
Note that these relevant keywords will be used to find information related to the query in a legal document.

#####
EXAMPLE 1:
- Query: 'Tell me about the benefits of Civil Union Partner and its benefits.'
- List of keywords: ['civil union', 'civil union partner', 'civil union partnership', 'drug addiction', 'due', 'dune buggy', 'duty']
- Relevant keywords: ['civil union partner']
EXAMPLE 2:
- Query: 'How are medical predictive diagnostics improving?'
- List of keywords: ['healthcare', 'prediction', 'analysis', 'machine learning', 'drug abuse']
- Relevant keywords: ['healthcare', 'machine learning']
####

Query: '{query}'
List of keywords: {keywords}
    """
    response = model.generate_content(prompt)
    if not response or not response.text:
        return []
    return clean_keywords_output(response.text)

def clean_keywords_output(llm_response):
    """
    Robustly post-processes the Gemini LLM comma-separated output string/list into a strict Python list of keywords.
    Handles irregular formatting, extra lines, and accidental punctuation.
    """
    if isinstance(llm_response, list):
        # Already a list; clean whitespace and filter empties
        return [kw.strip(" \"'[]") for kw in llm_response if kw.strip(" \"'[]")]
    if not llm_response or not isinstance(llm_response, str):
        return []
    # Extract the first bracketed section if present (handles accidental ['kw1', 'kw2'])
    bracket_match = re.search(r"\[(.*?)\]", llm_response)
    if bracket_match:
        text = bracket_match.group(1)
    else:
        text = llm_response
    # Split by comma and clean up entries
    keywords = [kw.strip(" \"'[]\n") for kw in text.split(",")]
    # Filter out any non-empty strings
    return [kw for kw in keywords if kw]

def generate_answer(query: str, chunks: list):
    """
    Generate answer of query based on chunks.
    Returns a string
    """
    context = "\n".join([c['content'] for c in chunks])
    prompt = f"""
Based on the context provided answer the query that follows.
The answer MUST be simple enough for a common man to understand while being legally and technically correct.

###
CONTEXT:
{context}
###

QUERY: {query}
    """
    response = model.generate_content(prompt)
    return response.text