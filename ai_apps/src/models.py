import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, DateTime, Integer, String, Text
from ai_apps.core.database import Base


class InterviewSession(Base):
    """
    Persists candidate resume, JD, AI skill gap analysis, generated questions, and evaluation scores.
    """
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Overview metadata
    role_title = Column(String(255), default="Engineering Candidate")
    candidate_name = Column(String(255), default="Candidate")
    fit_score_percentage = Column(Integer, default=0)
    status = Column(String(50), default="analyzed")  # "analyzed", "in_progress", "completed"

    # Raw Document Content
    resume_text = Column(Text, nullable=False)
    jd_text = Column(Text, nullable=False)

    # Serialized JSON fields
    analysis_json = Column(Text, nullable=True)     # Stores AnalysisResponse JSON
    questions_json = Column(Text, nullable=True)    # Stores QuestionGenerationResponse JSON
    evaluations_json = Column(Text, default="[]")   # Stores List[AnswerEvaluation] JSON

    def to_dict(self) -> Dict[str, Any]:
        """Converts session object into clean JSON-serializable dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.strftime("%b %d, %Y %I:%M %p") if self.created_at else "",
            "role_title": self.role_title,
            "candidate_name": self.candidate_name,
            "fit_score_percentage": self.fit_score_percentage,
            "status": self.status,
            "resume_text": self.resume_text,
            "jd_text": self.jd_text,
            "analysis": json.loads(self.analysis_json) if self.analysis_json else None,
            "questions": json.loads(self.questions_json) if self.questions_json else None,
            "evaluations": json.loads(self.evaluations_json) if self.evaluations_json else [],
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact summary for session history list."""
        return {
            "id": self.id,
            "created_at": self.created_at.strftime("%b %d, %Y %I:%M %p") if self.created_at else "",
            "role_title": self.role_title,
            "candidate_name": self.candidate_name,
            "fit_score_percentage": self.fit_score_percentage,
            "status": self.status,
            "resume_snippet": (self.resume_text[:80] + "...") if self.resume_text else "",
            "jd_snippet": (self.jd_text[:80] + "...") if self.jd_text else "",
        }
