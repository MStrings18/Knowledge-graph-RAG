# graph_retriever.py

import numpy as np
from neo4j import GraphDatabase
from sklearn.metrics.pairwise import cosine_similarity
from config import TOP_K_KEYWORDS, MAX_DEPTH, SIM_THRESHOLD, STORE_EMBED
from embeddings import get_embedding
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

        # 2. Embed extracted keywords
        if STORE_EMBED:
            query_embeddings = [get_embedding(kw) for kw in query_keywords]
            # 3. Fetch all stored keywords + embeddings from Neo4j
            with self.driver.session(database=self.database) as session:
                result = session.run("MATCH (k:Keyword) RETURN k.name AS name, k.embedding AS embedding")
                stored_keywords = [(r["name"], np.array(r["embedding"])) for r in result]

            if not stored_keywords:
                print("⚠ No stored keywords in Neo4j")
                return []

            # 4. Semantic similarity search
            matched_keywords = []
            for q_emb, q_kw in zip(query_embeddings, query_keywords):
                sims = cosine_similarity([q_emb], [kw_emb for _, kw_emb in stored_keywords])[0]
                top_indices = np.argsort(sims)[::-1][:TOP_K_KEYWORDS]
                for idx in top_indices:
                    sim_score = sims[idx]
                    if sim_score >= SIM_THRESHOLD:  # ✅ filter by threshold
                        matched_keywords.append(stored_keywords[idx][0])  # keyword name


            matched_keywords = list(set(matched_keywords))  # deduplicate
            print(f'Matched keywords: {matched_keywords}')
        
        else:
            matched_keywords = query_keywords
        
        if not matched_keywords:
                print("⚠ No matches found for query keywords")
                return []

        # 5. Retrieve primary chunks connected to matched keywords
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

        # 6. Expand with MAX_DEPTH
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