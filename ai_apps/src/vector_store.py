"""
Vector Database & Semantic Storage Engine for RAG pipeline.
Stores and indexes Resume & JD chunks using ChromaDB with fast vector cosine search.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

from config.settings import settings
from ai_apps.src.chunker import DocumentChunk

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Manages vector storage and semantic retrieval for candidate interview sessions.
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self._chroma_client = None
        self._in_memory_store: Dict[int, List[Dict[str, Any]]] = {}
        self._init_db()

    def _init_db(self):
        """Initializes ChromaDB client with persistent local storage."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._chroma_client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            logger.info(f"Initialized ChromaDB persistent vector store at: {self.persist_dir}")
        except Exception as e:
            logger.warning(f"Could not initialize ChromaDB ({e}), falling back to in-memory vector store")
            self._chroma_client = None

    def _get_collection_name(self, session_id: int) -> str:
        return f"session_{session_id}"

    def index_documents(
        self,
        session_id: int,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ) -> int:
        """
        Stores document chunks and their corresponding embeddings for a session.
        """
        if not chunks or not embeddings or len(chunks) != len(embeddings):
            return 0

        # 1. Try ChromaDB
        if self._chroma_client:
            try:
                coll_name = self._get_collection_name(session_id)
                # Delete existing collection for clean session index
                try:
                    self._chroma_client.delete_collection(name=coll_name)
                except Exception:
                    pass

                collection = self._chroma_client.create_collection(
                    name=coll_name,
                    metadata={"session_id": session_id}
                )

                ids = [f"{session_id}_{c.source}_{i}_{c.chunk_id}" for i, c in enumerate(chunks)]
                documents = [c.content for c in chunks]
                metadatas = [
                    {
                        "source": c.source,
                        "section": c.section,
                        "chunk_id": c.chunk_id,
                        "session_id": session_id,
                        "raw_text": c.metadata.get("raw_text", c.content)
                    }
                    for c in chunks
                ]

                collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                logger.info(f"Indexed {len(chunks)} chunks in ChromaDB for session {session_id}")
            except Exception as e:
                logger.error(f"Failed indexing to ChromaDB: {e}, storing in-memory fallback")

        # 2. In-memory backup
        self._in_memory_store[session_id] = []
        for chunk, emb in zip(chunks, embeddings):
            self._in_memory_store[session_id].append({
                "chunk": chunk,
                "embedding": np.array(emb, dtype=np.float32),
                "source": chunk.source,
                "section": chunk.section,
                "content": chunk.content
            })

        return len(chunks)

    def similarity_search(
        self,
        session_id: int,
        query_embedding: List[float],
        top_k: int = 4,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the top_k most semantically relevant chunks for a given query embedding.
        Optionally filters by source ('resume' or 'job_description').
        """
        # 1. Try ChromaDB
        if self._chroma_client:
            try:
                coll_name = self._get_collection_name(session_id)
                collection = self._chroma_client.get_collection(name=coll_name)
                
                where_filter = {"source": source_filter} if source_filter else None

                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, collection.count() or 1),
                    where=where_filter
                )

                retrieved = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
                    distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)

                    for doc, meta, dist in zip(docs, metas, distances):
                        retrieved.append({
                            "content": doc,
                            "source": meta.get("source", "unknown"),
                            "section": meta.get("section", "General"),
                            "score": float(1.0 - dist) if dist is not None else 1.0,
                            "metadata": meta
                        })
                return retrieved
            except Exception as e:
                logger.debug(f"Chroma query failed ({e}), searching in-memory store")

        # 2. In-memory cosine similarity fallback
        session_data = self._in_memory_store.get(session_id, [])
        if not session_data:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        scored = []
        for item in session_data:
            if source_filter and item["source"] != source_filter:
                continue
            
            doc_vec = item["embedding"]
            d_norm = np.linalg.norm(doc_vec)
            if d_norm == 0:
                continue
            
            cos_sim = float(np.dot(q_vec, doc_vec) / (q_norm * d_norm))
            scored.append({
                "content": item["content"],
                "source": item["source"],
                "section": item["section"],
                "score": cos_sim,
                "metadata": item["chunk"].metadata
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete_session(self, session_id: int):
        """Cleans up vectors for a deleted session."""
        if self._chroma_client:
            try:
                coll_name = self._get_collection_name(session_id)
                self._chroma_client.delete_collection(name=coll_name)
            except Exception:
                pass

        if session_id in self._in_memory_store:
            del self._in_memory_store[session_id]


# Global Singleton VectorStore
vector_store = VectorStore()
