# AI Interview Copilot

An AI-assisted technical interview preparation system designed for software engineers and technical candidates. It performs semantic chunking, vector embedding, and RAG retrieval across resumes and target job descriptions to identify skill gaps, generate grounded interview questions, and evaluate responses against staff-level engineering rubrics.

## Key Features

- Document Ingestion and Chunking: Parses PDF, DOCX, and text resumes/JDs and performs section-aware semantic chunking.
- Dual-Engine Vector Embeddings (RAG): Generates dense embeddings using Google Gemini (Cloud API default) or local embedding models (Ollama/SentenceTransformers) via the `LOCAL_EMBED` flag.
- Persistent Vector Store: Indexes resume evidence and job requirements into ChromaDB with cosine similarity retrieval.
- Grounded Question Generation: Generates scenario-based technical questions directly grounded in candidate project claims and target company requirements.
- Rubric-Based Response Evaluation: Evaluates user responses on conceptual depth, system design trade-offs, and practical execution, accompanied by reference answers.
- Session History: Persists interview rounds, question logs, and evaluations in a local SQLite database for progress tracking.

## Tech Stack

- Backend: FastAPI, Pydantic v2, SQLAlchemy, Uvicorn
- AI & Embeddings: Google Gemini API, ChromaDB, NumPy (with local Ollama embedding routing)
- Frontend: Vanilla JavaScript, CSS3, Tailwind CSS, Lucide icons, HTML5 (Jinja2 templates)
- Document Processing: PyPDF, python-docx
- Testing: Pytest

## Project Structure

```text
AI-Interview-Copilot/
├── ai_apps/
│   ├── core/               # Database models, constants, and custom exceptions
│   ├── src/                # Chunker, embedding client, vector store, RAG service, analyzer, and evaluator
│   ├── views.py            # API routes and view controllers
│   └── main.py             # FastAPI entrypoint and static file mounting
├── config/
│   ├── settings.py         # Application settings loaded via Pydantic
│   ├── local.env.example   # Example environment configuration for local dev
│   └── deploy.env.example  # Example environment configuration for production
├── static/                 # Stylesheets, design system, and client-side JavaScript
├── templates/              # HTML layout templates
├── tests/                  # Unit, embedding, and RAG integration test suite
├── deploy/                 # Dockerfile and docker-compose configurations
├── runserver.py            # Local development server startup script
├── requirements.txt        # Project dependencies
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10 or higher (Python 3.11 recommended)
- A Google Gemini API key (obtainable for free from Google AI Studio)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Annu-bot/AI-Interview-Copilot.git
   cd AI-Interview-Copilot
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Copy the sample environment file to create your local configuration:

```bash
# Windows PowerShell
Copy-Item config\local.env.example config\local.env

# Linux / macOS
cp config/local.env.example config/local.env
```

Open `config/local.env` and configure your settings:

```env
USE_OPEN_SOURCE=False
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# RAG & Embedding Routing
LOCAL_EMBED=False
USE_LOCAL_EMBEDDINGS=False
GEMINI_EMBEDDING_MODEL=models/text-embedding-004
LOCAL_EMBEDDING_BASE_URL=http://localhost:11434
LOCAL_EMBEDDING_MODEL=nomic-embed-text
```

### Running the Application

Start the development server:

```bash
python runserver.py
```

Once started, navigate to:
- Web Dashboard: `http://127.0.0.1:8000`
- Interactive API Documentation: `http://127.0.0.1:8000/docs`

## Docker Deployment

To build and run the application containerized:

```bash
docker-compose -f deploy/docker-compose.yml up --build
```

## Running Tests

Execute the automated test suite:

```bash
pytest
```
