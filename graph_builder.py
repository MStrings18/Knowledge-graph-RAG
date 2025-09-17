# graph_builder.py

from neo4j import GraphDatabase
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE, SIM_THRESHOLD

# Load embedding model once
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


class KnowledgeGraphBuilder:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, database=NEO4J_DATABASE):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self):
        self.driver.close()

    def clear_graph(self):
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")

    def build_graph(self, chunks: List[str], keywords: List[str]):
        """
        Build knowledge graph:
        - Chunk nodes
        - Keyword nodes with embeddings
        - APPEARS_IN relationships
        - SIMILAR_TO relationships between keywords (cosine similarity)
        """

        # --- Map keywords to chunks with substring count ---
        keyword_map = {}
        for kw in keywords:
            kw_lower=kw.lower()
            keyword_map[kw_lower] = {}
            for idx, chunk in enumerate(chunks):
                # Case-insensitive count
                count = chunk.lower().count(kw.lower())
                if count > 0:
                    keyword_map[kw][idx] = count

        # --- Compute embeddings for keywords ---
        kw_list = list(keyword_map.keys())
        embeddings = EMBED_MODEL.encode(kw_list, convert_to_numpy=True)
        # Normalize embeddings
        embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)

        # --- Push nodes and relationships to Neo4j ---
        with self.driver.session(database=self.database) as session:

            # 1️⃣ Chunk nodes
            for idx, chunk in enumerate(chunks):
                session.run(
                    "MERGE (c:Chunk {id: $id, content: $content})",
                    id=idx,
                    content=chunk
                )

            # 2️⃣ Keyword nodes with embeddings
            for i, kw in enumerate(kw_list):
                session.run(
                    "MERGE (k:Keyword {name: $name}) SET k.embedding = $embedding",
                    name=kw,
                    embedding=embeddings[i].tolist()
                )

            # 3️⃣ APPEARS_IN relationships
            for kw, chunk_counts in keyword_map.items():
                for idx in chunk_counts.keys():
                    session.run(
                        """
                        MATCH (k:Keyword {name: $kw})
                        MATCH (c:Chunk {id: $cid})
                        MERGE (k)-[:APPEARS_IN]->(c)
                        """,
                        kw=kw,
                        cid=idx
                    )

            # 4️⃣ SIMILAR_TO relationships between keywords
            for i in range(len(kw_list)):
                for j in range(i + 1, len(kw_list)):
                    sim = np.dot(embeddings[i], embeddings[j])
                    if sim >= SIM_THRESHOLD:
                        session.run(
                            """
                            MATCH (k1:Keyword {name: $kw1})
                            MATCH (k2:Keyword {name: $kw2})
                            MERGE (k1)-[:SIMILAR_TO {weight: $sim}]->(k2)
                            MERGE (k2)-[:SIMILAR_TO {weight: $sim}]->(k1)
                            """,
                            kw1=kw_list[i],
                            kw2=kw_list[j],
                            sim=float(sim)
                        )

        print(f"✅ Knowledge graph built with {len(chunks)} chunks and {len(keywords)} keywords.")
