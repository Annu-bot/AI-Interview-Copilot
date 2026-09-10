"""
Unit Tests for Document Chunker (V2 RAG).
"""

from ai_apps.src.chunker import chunk_resume, chunk_job_description, DocumentChunk


def test_chunk_resume_sections():
    resume_text = """
    JOHN DOE
    john@example.com

    TECHNICAL SKILLS
    Python, FastAPI, Docker, Kubernetes, PostgreSQL, Redis

    WORK EXPERIENCE
    Senior Software Engineer at Acme Corp (2021 - Present)
    - Designed and implemented microservices handling 50k requests/sec.
    - Optimized PostgreSQL database queries reducing latency by 40%.

    PROJECTS
    Distributed Cache Engine
    - Built an in-memory distributed cache in Go with consistent hashing.

    EDUCATION
    B.S. in Computer Science
    """
    chunks = chunk_resume(resume_text)
    assert len(chunks) >= 3

    sources = [c.source for c in chunks]
    assert all(s == "resume" for s in sources)

    sections = [c.section for c in chunks]
    assert any("Skills" in s for s in sections)
    assert any("Experience" in s for s in sections)
    assert any("Projects" in s for s in sections)


def test_chunk_job_description_sections():
    jd_text = """
    SENIOR BACKEND ENGINEER
    About the Role:
    We are looking for a Senior Engineer to scale our distributed core platform.

    RESPONSIBILITIES:
    - Lead architecture of asynchronous message processing systems.
    - Implement resilient data pipelines using Apache Kafka.

    REQUIREMENTS:
    - 5+ years of production experience in Python or Go.
    - Hands-on expertise with Kafka, Docker, and Kubernetes.
    - Strong understanding of database indexing and query optimization.
    """
    chunks = chunk_job_description(jd_text)
    assert len(chunks) >= 2

    sources = [c.source for c in chunks]
    assert all(s == "job_description" for s in sources)

    sections = [c.section for c in chunks]
    assert any("Responsibilities" in s or "Requirements" in s for s in sections)


def test_chunk_empty_inputs():
    assert chunk_resume("") == []
    assert chunk_resume("   ") == []
    assert chunk_job_description("") == []
