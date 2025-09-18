# graph_builder.py

from neo4j import GraphDatabase
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer

# Import the new STORE_EMBED flag from your config file
from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
    SIM_THRESHOLD,
    STORE_EMBED # <-- Import the new flag
)

# Load embedding model once
# We can load it conditionally as well to save memory if embeddings are not needed
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2") if STORE_EMBED else None


class KnowledgeGraphBuilder:
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD, database=NEO4J_DATABASE):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self):
        self.driver.close()

    def clear_graph(self):
        print("🧹 Clearing the graph...")
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✅ Graph cleared.")

    def build_graph_from_map(self, keyword_to_chunks_map: Dict[str, List[str]]):
        """
        Builds a knowledge graph from a map of keywords to chunks.
        Embedding and similarity calculations are controlled by the STORE_EMBED flag.
        """
        print(f"Building graph from map with {len(keyword_to_chunks_map)} keywords...")
        print(f"Store embeddings: {STORE_EMBED}")

        # --- 1. Extract unique chunks and keywords ---
        all_keywords = list(keyword_to_chunks_map.keys())
        unique_chunks_set = set(chunk for chunks in keyword_to_chunks_map.values() for chunk in chunks)
        all_chunks = list(unique_chunks_set)
        chunk_to_id = {chunk: i for i, chunk in enumerate(all_chunks)}
        
        # --- 2. (Conditional) Compute embeddings ---
        embeddings = None
        if STORE_EMBED:
            print("Computing keyword embeddings...")
            embeddings = EMBED_MODEL.encode(all_keywords, convert_to_numpy=True, show_progress_bar=True)
            embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # --- 3. Push nodes and relationships to Neo4j ---
        with self.driver.session(database=self.database) as session:
            # Create all Chunk nodes
            print("Creating Chunk nodes...")
            for i, chunk in enumerate(all_chunks):
                session.run(
                    "MERGE (c:Chunk {id: $id}) SET c.content = $content",
                    id=i, content=chunk
                )

            # Create all Keyword nodes, conditionally adding embeddings
            print("Creating Keyword nodes...")
            for i, kw in enumerate(all_keywords):
                if STORE_EMBED:
                    session.run(
                        "MERGE (k:Keyword {name: $name}) SET k.embedding = $embedding",
                        name=kw, embedding=embeddings[i].tolist()
                    )
                else:
                    # Create node without the embedding property
                    session.run("MERGE (k:Keyword {name: $name})", name=kw)

            # Create APPEARS_IN relationships (this is always done)
            print("Creating APPEARS_IN relationships...")
            for kw, chunks in keyword_to_chunks_map.items():
                for chunk in chunks:
                    chunk_id = chunk_to_id[chunk]
                    session.run(
                        """
                        MATCH (k:Keyword {name: $kw_name})
                        MATCH (c:Chunk {id: $c_id})
                        MERGE (k)-[:APPEARS_IN]->(c)
                        """,
                        kw_name=kw, c_id=chunk_id
                    )

            # (Conditional) Create SIMILAR_TO relationships
            if STORE_EMBED:
                print("Creating SIMILAR_TO relationships...")
                for i in range(len(all_keywords)):
                    for j in range(i + 1, len(all_keywords)):
                        sim = np.dot(embeddings[i], embeddings[j])
                        if sim >= SIM_THRESHOLD:
                            session.run(
                                """
                                MATCH (k1:Keyword {name: $kw1})
                                MATCH (k2:Keyword {name: $kw2})
                                MERGE (k1)-[r:SIMILAR_TO]-(k2)
                                SET r.weight = $sim
                                """,
                                kw1=all_keywords[i], kw2=all_keywords[j], sim=float(sim)
                            )
        
        print(f"\n✅ Knowledge graph built successfully with {len(all_chunks)} chunks and {len(all_keywords)} keywords.")
    
    # You can apply the same logic to the original build_graph method if you plan to keep it.