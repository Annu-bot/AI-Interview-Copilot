"""
Views and API Request Handlers for AI Interview Copilot
Handles all incoming web requests, document processing, database persistence, RAG vector indexing, and AI endpoints.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from config.settings import settings
from config.logging_config import logger
from ai_apps.core.database import get_db
from ai_apps.src.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    EvaluationRequest,
    EvaluationResponse,
)
from ai_apps.src.parser import document_parser
from ai_apps.src.analyzer import skill_gap_analyzer
from ai_apps.src.evaluator import answer_evaluator
from ai_apps.src.session_service import session_service
from ai_apps.src.rag_service import rag_service
from ai_apps.src.vector_store import vector_store
from ai_apps.core.exceptions import DocumentParsingError, LLMInferenceError

# Project root templates directory
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Main Router
router = APIRouter()


# ==========================================
# Web Page Views
# ==========================================
@router.get("/", response_class=HTMLResponse, tags=["Web Views"])
async def home_view(request: Request):
    """
    Renders the single-page application dashboard.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "version": "3.0.0",
            "environment": settings.ENVIRONMENT,
        },
    )


# ==========================================
# System Health View
# ==========================================
@router.get("/api/v1/health", tags=["System Health"])
async def health_view():
    """
    Returns system status, active LLM provider, and environment info.
    """
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "version": "3.0.0",
        "environment": settings.ENVIRONMENT,
        "use_open_source": settings.USE_OPEN_SOURCE,
        "provider": "Local Open Source" if settings.USE_OPEN_SOURCE else "Google Gemini (Cloud)",
        "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
        "use_local_embeddings": settings.is_local_embed,
        "embedding_model": settings.LOCAL_EMBEDDING_MODEL if settings.is_local_embed else settings.GEMINI_EMBEDDING_MODEL,
        "rag_vector_engine": "ChromaDB + Cosine Search",
        "voice_capabilities": ["Web Speech Synthesis (TTS)", "Web Speech Recognition (STT)"],
    }


# ==========================================
# Document Processing View
# ==========================================
@router.post("/api/v1/parse-document", tags=["Document Processing"])
async def parse_document_view(file: UploadFile = File(...)):
    """
    Extracts and normalizes text from an uploaded Resume or JD (PDF, DOCX, TXT).
    """
    try:
        content = await file.read()
        extracted_text = document_parser.extract_text_from_upload(file.filename, content)
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extracted document text is empty or too short."
            )
        return {
            "filename": file.filename,
            "character_count": len(extracted_text),
            "text": extracted_text,
        }
    except DocumentParsingError as dpe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(dpe))
    except Exception as e:
        logger.error(f"Error parsing uploaded file {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse file: {str(e)}"
        )


# ==========================================
# Unified 1-Click Start Interview (RAG Vector Indexing + Analysis + Grounded Questions)
# ==========================================
@router.post("/api/v1/start-interview", response_model=StartInterviewResponse, tags=["AI Interview"])
async def start_interview_view(request: StartInterviewRequest, db: Session = Depends(get_db)):
    """
    1-Click Start:
    1. Analyzes resume vs JD for skill gaps and fit score.
    2. Saves session to SQLite.
    3. Indexes resume & JD chunks into RAG Vector Store (Cloud or Local embeddings).
    4. Generates up to 10 structured questions across interview stages (Warm-up, Projects, Gaps, System Design, Culture).
    """
    try:
        # Step 1: Analyze Skills & Fit
        analysis_result = skill_gap_analyzer.analyze_resume_and_jd(
            resume_text=request.resume_text,
            jd_text=request.job_description_text,
        )

        # Step 2: Save Initial Session to SQLite Database to obtain Session ID
        saved_session = session_service.save_analysis(
            db=db,
            resume_text=request.resume_text,
            jd_text=request.job_description_text,
            analysis=analysis_result,
            session_id=request.session_id,
        )

        # Step 3: RAG Document Chunking & Vector Indexing
        try:
            rag_service.index_session(
                session_id=saved_session.id,
                resume_text=request.resume_text,
                job_description_text=request.job_description_text
            )
        except Exception as rag_err:
            logger.warning(f"RAG vector indexing encountered non-fatal error: {rag_err}")

        # Step 4: Generate RAG Grounded Questions (Up to 10 Questions with Intro & Stages)
        num_q = request.num_questions if request.num_questions else 10
        questions_result = skill_gap_analyzer.generate_interview_questions(
            resume_text=request.resume_text,
            jd_text=request.job_description_text,
            missing_skills=analysis_result.missing_skills,
            num_questions=num_q,
            session_id=saved_session.id,
        )

        # Step 5: Save Questions to DB
        session_service.save_questions(
            db=db,
            session_id=saved_session.id,
            questions_response=questions_result,
        )

        return StartInterviewResponse(
            session_id=saved_session.id,
            candidate_name=analysis_result.candidate_name or "Candidate",
            role_title=questions_result.role_title or "AI / Software Engineer",
            fit_score_percentage=analysis_result.fit_score_percentage,
            matched_skills=analysis_result.matched_skills,
            missing_skills=analysis_result.missing_skills,
            executive_summary=analysis_result.executive_summary,
            total_questions=questions_result.total_questions,
            questions=questions_result.questions,
        )

    except (LLMInferenceError, ValueError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as e:
        logger.error(f"Error starting interview session: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# AI Analysis View (Optional direct call)
# ==========================================
@router.post("/api/v1/analyze", response_model=AnalysisResponse, tags=["AI Analysis"])
async def analyze_skills_view(request: AnalysisRequest, db: Session = Depends(get_db)):
    """
    Performs skill gap analysis comparing candidate's resume with JD, indexes vectors, and saves to Database.
    """
    try:
        analysis_result = skill_gap_analyzer.analyze_resume_and_jd(
            resume_text=request.resume_text,
            jd_text=request.job_description_text,
        )

        saved_session = session_service.save_analysis(
            db=db,
            resume_text=request.resume_text,
            jd_text=request.job_description_text,
            analysis=analysis_result,
            session_id=request.session_id,
        )
        
        # Index chunks for RAG
        try:
            rag_service.index_session(
                session_id=saved_session.id,
                resume_text=request.resume_text,
                job_description_text=request.job_description_text
            )
        except Exception as e:
            logger.warning(f"RAG indexing warning: {e}")

        analysis_result.session_id = saved_session.id
        return analysis_result

    except (LLMInferenceError, ValueError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as e:
        logger.error(f"Error during skill gap analysis: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# AI Question Generation View
# ==========================================
@router.post("/api/v1/generate-questions", response_model=QuestionGenerationResponse, tags=["AI Questions"])
async def generate_questions_view(request: QuestionGenerationRequest, db: Session = Depends(get_db)):
    """
    Generates RAG-grounded interview questions (up to 10) and links them to the active session in DB.
    """
    try:
        num_q = request.num_questions if request.num_questions else 10
        questions_result = skill_gap_analyzer.generate_interview_questions(
            resume_text=request.resume_text,
            jd_text=request.job_description_text,
            missing_skills=request.missing_skills,
            num_questions=num_q,
            session_id=request.session_id,
        )

        if request.session_id:
            session_service.save_questions(
                db=db,
                session_id=request.session_id,
                questions_response=questions_result,
            )
            questions_result.session_id = request.session_id

        return questions_result

    except (LLMInferenceError, ValueError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as e:
        logger.error(f"Error generating interview questions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# AI Evaluation View
# ==========================================
@router.post("/api/v1/evaluate-answer", response_model=EvaluationResponse, tags=["AI Evaluation"])
async def evaluate_answer_view(request: EvaluationRequest, db: Session = Depends(get_db)):
    """
    Evaluates candidate's response with RAG grounding and persists evaluation into DB.
    """
    try:
        eval_result = answer_evaluator.evaluate_candidate_answer(
            question_text=request.question_text,
            evaluation_criteria=request.evaluation_criteria,
            user_answer=request.user_answer,
            target_skill=request.target_skill_or_topic or "",
            session_id=request.session_id,
        )

        if request.session_id:
            session_service.save_evaluation(
                db=db,
                session_id=request.session_id,
                question_text=request.question_text,
                user_answer=request.user_answer,
                evaluation=eval_result.evaluation,
                question_id=request.question_id,
            )
            eval_result.session_id = request.session_id

        return eval_result

    except (LLMInferenceError, ValueError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as e:
        logger.error(f"Error evaluating candidate answer: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==========================================
# Session History Views
# ==========================================
@router.get("/api/v1/sessions", tags=["Session History"])
async def list_sessions_view(db: Session = Depends(get_db)):
    """
    Returns list of past interview and analysis sessions.
    """
    return session_service.list_sessions(db=db)


@router.get("/api/v1/sessions/{session_id}", tags=["Session History"])
async def get_session_detail_view(session_id: int, db: Session = Depends(get_db)):
    """
    Fetches full data for a specific session to restore resume, JD, questions, and scores.
    """
    session_data = session_service.get_session(db=db, session_id=session_id)
    if not session_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session_data


@router.delete("/api/v1/sessions/{session_id}", tags=["Session History"])
async def delete_session_view(session_id: int, db: Session = Depends(get_db)):
    """
    Deletes a session from history and cleans up stored vectors in ChromaDB.
    """
    success = session_service.delete_session(db=db, session_id=session_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Clean up vector database collections
    try:
        vector_store.delete_session(session_id)
    except Exception as e:
        logger.warning(f"Vector deletion warning: {e}")

    return {"success": True, "message": f"Session {session_id} deleted."}
