"""
Unit and Integration Tests for RAG Vector Store & Context Grounding Service.
"""

from ai_apps.src.rag_service import rag_service
from ai_apps.src.vector_store import vector_store


def test_rag_index_and_retrieval():
    session_id = 999
    resume = """
    EXPERIENCE
    - Senior Engineer at Fintech Inc. Built Redis caching layer handling 100k ops/sec.
    - Designed database partitioning scheme in PostgreSQL.

    SKILLS
    Python, FastAPI, Redis, Docker, PostgreSQL
    """

    jd = """
    REQUIREMENTS
    - Deep expertise in Redis caching architectures and distributed state.
    - Experience in high-throughput database sharding and query tuning.
    """

    # 1. Index session
    index_res = rag_service.index_session(
        session_id=session_id,
        resume_text=resume,
        job_description_text=jd
    )

    assert index_res["status"] == "success"
    assert index_res["total_indexed"] > 0
    assert index_res["resume_chunks"] > 0
    assert index_res["jd_chunks"] > 0

    # 2. Retrieve grounding context for a specific topic
    ctx = rag_service.get_grounding_context(session_id=session_id, topic_or_skill="Redis Caching", top_k=2)

    assert "topic" in ctx
    assert ctx["topic"] == "Redis Caching"
    assert len(ctx["resume_evidence"]) > 0
    assert "prompt_block" in ctx
    assert "RETRIEVED CANDIDATE RESUME EVIDENCE" in ctx["prompt_block"]

    # 3. Clean up
    vector_store.delete_session(session_id)
