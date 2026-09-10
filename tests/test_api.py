from fastapi.testclient import TestClient
from ai_apps.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data
    assert "use_open_source" in data


def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Interview Copilot" in response.text
    assert "Candidate Resume" in response.text


def test_parse_document_endpoint():
    files = {"file": ("test_resume.txt", b"Python Developer with FastAPI and Docker experience.", "text/plain")}
    response = client.post("/api/v1/parse-document", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "Python Developer" in data["text"]
    assert data["character_count"] > 0


def test_sessions_endpoint():
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_session_not_found():
    response = client.get("/api/v1/sessions/999999")
    assert response.status_code == 404
