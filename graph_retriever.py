# graph_retriever.py

from neo4j import GraphDatabase
from config import MAX_DEPTH
from gemini_client import extract_keywords  # wrapper for Gemini API


class GraphRetriever:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_pass, neo4j_db, keywords):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
        self.database = neo4j_db
        self.keywords = keywords

    def close(self):
        self.driver.close()

    # --- Core Retrieval ---
    def retrieve(self, query: str):

        # 1. Extract keywords from query via Gemini
        query_keywords = extract_keywords(query, self.keywords)
        print(f'Extracted keywords: {query_keywords}')
        if not query_keywords:
            print("⚠ No keywords extracted from query")
            return []

        matched_keywords = query_keywords
        
        if not matched_keywords:
                print("⚠ No matches found for query keywords")
                return []

        # 2. Retrieve primary chunks connected to matched keywords
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                // Part 1: Calculate the score for each chunk and find the single highest score.
                MATCH (k:Keyword)-[:APPEARS_IN]->(c:Chunk)
                WHERE k.name IN $keywords
                WITH c, count(k) AS score
                ORDER BY score DESC
                LIMIT 1
                WITH score AS max_score

                // Part 2: Find all chunks that have a score equal to that max_score.
                MATCH (k2:Keyword)-[:APPEARS_IN]->(c2:Chunk)
                WHERE k2.name IN $keywords
                WITH c2, count(k2) AS final_score, max_score
                WHERE final_score = max_score
                RETURN c2.id AS id, c2.content AS content
            """, {
                "keywords": matched_keywords
            })
            
            primary_chunks = [{"id": r["id"], "content": r["content"]} for r in result]

        # 3. Expand with MAX_DEPTH
        retrieved_chunks = primary_chunks.copy()
        visited = set([c["id"] for c in primary_chunks])
        frontier = [c["id"] for c in primary_chunks]

        for depth in range(MAX_DEPTH):
            if not frontier:
                break
            with self.driver.session(database=self.database) as session:
                result = session.run("""
                    // Case A: shared keyword
                    MATCH (c:Chunk)<-[:APPEARS_IN]-(k:Keyword)-[:APPEARS_IN]->(n:Chunk)
                    WHERE c.id IN $frontier
                    RETURN DISTINCT n.id AS id, n.content AS content
                    UNION
                    // Case B: keyword similarity
                    MATCH (c:Chunk)<-[:APPEARS_IN]-(k1:Keyword)-[:SIMILAR_TO]-(k2:Keyword)-[:APPEARS_IN]->(n:Chunk)
                    WHERE c.id IN $frontier
                    RETURN DISTINCT n.id AS id, n.content AS content
                """, {"frontier": frontier})

                neighbors = [{"id": r["id"], "content": r["content"]} for r in result if r["id"] not in visited]

            retrieved_chunks.extend(neighbors)
            visited.update([n["id"] for n in neighbors])
            frontier = [n["id"] for n in neighbors]

        return retrieved_chunks