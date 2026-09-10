"""
RAG (Retrieval-Augmented Generation) Service.
Coordinates chunking, embedding generation, vector storage, and semantic context grounding.
"""

import logging
from typing import Dict, Any, List, Optional

from config.settings import settings
from ai_apps.src.chunker import chunk_resume, chunk_job_description, DocumentChunk
from ai_apps.src.embedding_client import embedding_client
from ai_apps.src.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGService:
    """
    Orchestrates end-to-end RAG grounding for interview sessions.
    """

    def __init__(self):
        self.chunker_resume = chunk_resume
        self.chunker_jd = chunk_job_description
        self.embedder = embedding_client
        self.store = vector_store

    def index_session(
        self,
        session_id: int,
        resume_text: str,
        job_description_text: str
    ) -> Dict[str, Any]:
        """
        Chunks, embeds, and indexes candidate resume and JD into vector database.
        """
        logger.info(f"Indexing RAG documents for session {session_id} (Local Embed: {settings.is_local_embed})")

        # 1. Chunk documents
        resume_chunks = self.chunker_resume(resume_text)
        jd_chunks = self.chunker_jd(job_description_text)
        all_chunks = resume_chunks + jd_chunks

        if not all_chunks:
            return {"status": "empty", "total_chunks": 0}

        # 2. Generate vector embeddings
        texts_to_embed = [c.content for c in all_chunks]
        embeddings = self.embedder.get_embeddings_batch(texts_to_embed)

        # 3. Store in vector database
        indexed_count = self.store.index_documents(session_id, all_chunks, embeddings)

        return {
            "status": "success",
            "session_id": session_id,
            "resume_chunks": len(resume_chunks),
            "jd_chunks": len(jd_chunks),
            "total_indexed": indexed_count,
            "is_local_embed": settings.is_local_embed,
            "embedding_model": settings.LOCAL_EMBEDDING_MODEL if settings.is_local_embed else settings.GEMINI_EMBEDDING_MODEL
        }

    def get_grounding_context(
        self,
        session_id: int,
        topic_or_skill: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Retrieves top relevant resume evidence and JD requirements for a specific skill or topic.
        """
        query_emb = self.embedder.get_embedding(topic_or_skill)

        # Retrieve matching chunks
        resume_matches = self.store.similarity_search(
            session_id=session_id,
            query_embedding=query_emb,
            top_k=top_k,
            source_filter="resume"
        )

        jd_matches = self.store.similarity_search(
            session_id=session_id,
            query_embedding=query_emb,
            top_k=top_k,
            source_filter="job_description"
        )

        # Format human-readable context blocks for LLM prompt
        resume_evidence_lines = []
        for r in resume_matches:
            resume_evidence_lines.append(f"- [{r['section']}]: {r['content']}")

        jd_req_lines = []
        for j in jd_matches:
            jd_req_lines.append(f"- [{j['section']}]: {j['content']}")

        context_prompt_block = (
            f"=== RETRIEVED CANDIDATE RESUME EVIDENCE FOR '{topic_or_skill}' ===\n"
            + ("\n".join(resume_evidence_lines) if resume_evidence_lines else "No direct resume matches found.")
            + f"\n\n=== RETRIEVED JOB DESCRIPTION REQUIREMENTS FOR '{topic_or_skill}' ===\n"
            + ("\n".join(jd_req_lines) if jd_req_lines else "No direct JD matches found.")
        )

        return {
            "topic": topic_or_skill,
            "resume_evidence": resume_matches,
            "jd_requirements": jd_matches,
            "prompt_block": context_prompt_block
        }


# Global Singleton
rag_service = RAGService()
