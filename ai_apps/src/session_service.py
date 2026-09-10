import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from config.logging_config import logger
from ai_apps.src.models import InterviewSession
from ai_apps.src.schemas import (
    AnalysisResponse,
    QuestionGenerationResponse,
    AnswerEvaluation,
)


class SessionService:
    """
    Handles database operations for interview sessions, storing resumes, JDs,
    AI analyses, generated questions, and evaluated answers.
    """

    @staticmethod
    def save_analysis(
        db: Session,
        resume_text: str,
        jd_text: str,
        analysis: AnalysisResponse,
        session_id: Optional[int] = None,
    ) -> InterviewSession:
        """Creates or updates a session with the latest skill-gap analysis."""
        analysis_dict = analysis.model_dump()

        if session_id:
            session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
            if session:
                session.resume_text = resume_text
                session.jd_text = jd_text
                session.candidate_name = analysis.candidate_name or session.candidate_name
                session.fit_score_percentage = analysis.fit_score_percentage
                session.analysis_json = json.dumps(analysis_dict)
                db.commit()
                db.refresh(session)
                logger.info(f"Updated existing session ID={session.id}")
                return session

        # Create new session
        session = InterviewSession(
            resume_text=resume_text,
            jd_text=jd_text,
            candidate_name=analysis.candidate_name or "Candidate",
            role_title="AI / Software Engineer",
            fit_score_percentage=analysis.fit_score_percentage,
            analysis_json=json.dumps(analysis_dict),
            status="analyzed",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created new interview session ID={session.id}")
        return session

    @staticmethod
    def save_questions(
        db: Session,
        session_id: int,
        questions_response: QuestionGenerationResponse,
    ) -> Optional[InterviewSession]:
        """Saves generated questions to the session."""
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            return None

        session.questions_json = json.dumps(questions_response.model_dump())
        session.role_title = questions_response.role_title or session.role_title
        session.status = "in_progress"
        db.commit()
        db.refresh(session)
        logger.info(f"Saved {questions_response.total_questions} questions for session ID={session_id}")
        return session

    @staticmethod
    def save_evaluation(
        db: Session,
        session_id: int,
        question_text: str,
        user_answer: str,
        evaluation: AnswerEvaluation,
        question_id: Optional[int] = None,
    ) -> Optional[InterviewSession]:
        """Appends candidate's answer and AI evaluation to the session."""
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            return None

        current_evals = json.loads(session.evaluations_json) if session.evaluations_json else []
        new_eval_entry = {
            "question_id": question_id,
            "question_text": question_text,
            "user_answer": user_answer,
            "score_out_of_10": evaluation.score_out_of_10,
            "strengths": evaluation.strengths,
            "missing_points_and_gaps": evaluation.missing_points_and_gaps,
            "detailed_feedback": evaluation.detailed_feedback,
            "ideal_model_answer": evaluation.ideal_model_answer,
            "interview_tips": evaluation.interview_tips,
        }

        # Check if this question was already evaluated, update or append
        existing_idx = next((i for i, item in enumerate(current_evals) if item.get("question_id") == question_id), None)
        if existing_idx is not None and question_id is not None:
            current_evals[existing_idx] = new_eval_entry
        else:
            current_evals.append(new_eval_entry)

        session.evaluations_json = json.dumps(current_evals)
        db.commit()
        db.refresh(session)
        logger.info(f"Appended answer evaluation to session ID={session_id}")
        return session

    @staticmethod
    def list_sessions(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns list of all stored interview sessions sorted newest first."""
        sessions = db.query(InterviewSession).order_by(InterviewSession.created_at.desc()).limit(limit).all()
        return [s.to_summary_dict() for s in sessions]

    @staticmethod
    def get_session(db: Session, session_id: int) -> Optional[Dict[str, Any]]:
        """Fetches complete session detail including full text, analysis, questions, and scores."""
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        return session.to_dict() if session else None

    @staticmethod
    def delete_session(db: Session, session_id: int) -> bool:
        """Deletes a session from the database."""
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            logger.info(f"Deleted session ID={session_id}")
            return True
        return False


session_service = SessionService()
