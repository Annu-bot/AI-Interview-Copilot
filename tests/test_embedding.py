"""
Unit Tests for Vector Embedding Client (V2 RAG).
"""

from ai_apps.src.embedding_client import embedding_client


def test_embedding_dimension():
    text = "Experience with Python FastAPI and PostgreSQL database design."
    vec = embedding_client.get_embedding(text)
    assert isinstance(vec, list)
    assert len(vec) in (768, 1536, 3072)
    assert any(v != 0.0 for v in vec)


def test_embedding_batch():
    texts = [
        "Distributed microservices architecture in Python",
        "Experience leading technical roadmaps and mentoring junior engineers"
    ]
    vecs = embedding_client.get_embeddings_batch(texts)
    assert len(vecs) == 2
    assert len(vecs[0]) in (768, 1536, 3072)
    assert len(vecs[1]) in (768, 1536, 3072)


def test_empty_embedding():
    vec = embedding_client.get_embedding("")
    assert isinstance(vec, list)
    assert len(vec) in (768, 1536, 3072)
