# gemini_client.py
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key="AIzaSyBY_9HJewap03dpZxzt5Ktj_U-7koC1SHg")

model = genai.GenerativeModel("gemini-2.5-flash-lite")

def extract_keywords(query: str, max_keywords: int = 5):
    """
    Extract important keywords from the query using Gemini.
    Returns a list of strings.
    """
    prompt = f"""
    Extract {max_keywords} most important entities from the following query.
    Return ONLY the keywords as a comma-separated list. No explanations.
    All keywords should be exactly present in the query.

    ### EXAMPLE Query: 'Tell me about Civil Union Partner and its benefits.'
    REQUIRED Keywords: ['Civil Union Partner', 'benefits']

    Query: "{query}"
    """

    response = model.generate_content(prompt)
    if not response or not response.text:
        return []

    # Post-process response into keyword list
    keywords = [kw.strip() for kw in response.text.split(",")]
    return [kw for kw in keywords if kw]  # remove empty strings