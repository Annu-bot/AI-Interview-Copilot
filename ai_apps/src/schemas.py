from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# --- Analysis Schemas ---
class SkillGapDetail(BaseModel):
    skill_name: str = Field(description="Name of the skill, technology, or domain concept")
    importance: str = Field(description="'Must Have', 'Nice to Have', or 'Bonus'")
    status: str = Field(description="'Matched', 'Missing', or 'Needs Improvement'")
    reasoning: str = Field(description="Brief explanation based on the resume")


class AnalysisRequest(BaseModel):
    resume_text: str = Field(..., min_length=10, description="Raw text extracted from candidate's resume")
    job_description_text: str = Field(..., min_length=10, description="Raw text of the target job description")
    session_id: Optional[int] = Field(default=None, description="Optional existing session ID to update")


class AnalysisResponse(BaseModel):
    session_id: Optional[int] = Field(default=None, description="Database Session ID for history tracking")
    candidate_name: Optional[str] = Field(default="Candidate", description="Detected candidate name")
    estimated_experience_level: str = Field(description="e.g. 'Junior (0-2 yrs)', 'Mid-level (3-5 yrs)', 'Senior (5+ yrs)'")
    fit_score_percentage: int = Field(ge=0, le=100, description="Matching score from 0 to 100")
    executive_summary: str = Field(description="Summary of candidate fit against the JD")
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both resume and JD")
    missing_skills: List[str] = Field(default_factory=list, description="JD requirements missing or weak in resume")
    skill_gap_breakdown: List[SkillGapDetail] = Field(default_factory=list, description="Breakdown per skill")
    recommended_focus_areas: List[str] = Field(default_factory=list, description="Top technical areas to test")


# --- Question Generation Schemas ---
class QuestionCategory(str, Enum):
    INTRODUCTION = "Warm-up & Background Introduction"
    PROJECT_VERIFICATION = "Project & Experience Verification"
    SKILL_GAP = "Skill Gap Deep-Dive"
    SYSTEM_DESIGN = "System Design & Architecture"
    CODING_PROBLEM_SOLVING = "Coding & Problem Solving"
    BEHAVIORAL = "Behavioral & Engineering Culture"


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class InterviewQuestion(BaseModel):
    id: int = Field(..., description="Unique sequential question number (1 to 10)")
    stage: str = Field(default="Core Technical Deep-Dive", description="Interview phase or stage name")
    category: QuestionCategory = Field(description="Category of the interview question")
    target_skill_or_topic: str = Field(description="Target skill tested")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="Difficulty level")
    spoken_intro: Optional[str] = Field(default="", description="Conversational spoken transition for TTS before asking the question")
    question_text: str = Field(..., description="The interview question text")
    evaluation_criteria: str = Field(..., description="Key concepts required for an ideal answer")


class QuestionGenerationRequest(BaseModel):
    resume_text: str = Field(..., min_length=10)
    job_description_text: str = Field(..., min_length=10)
    missing_skills: Optional[List[str]] = Field(default_factory=list, description="Skill gaps to prioritize")
    num_questions: int = Field(default=10, ge=1, le=10, description="Total questions to generate (up to 10)")
    session_id: Optional[int] = Field(default=None, description="Database Session ID")


class QuestionGenerationResponse(BaseModel):
    session_id: Optional[int] = Field(default=None, description="Database Session ID")
    role_title: str = Field(default="Candidate Role", description="Identified role title")
    total_questions: int = Field(..., description="Total questions generated")
    questions: List[InterviewQuestion] = Field(default_factory=list, description="Generated questions")


# --- Unified 1-Click Start Interview Schemas ---
class StartInterviewRequest(BaseModel):
    resume_text: str = Field(..., min_length=10, description="Candidate resume text")
    job_description_text: str = Field(..., min_length=10, description="Job description text")
    num_questions: int = Field(default=10, ge=3, le=10, description="Total questions for full mock interview (3 to 10)")
    session_id: Optional[int] = Field(default=None, description="Optional existing session ID")


class StartInterviewResponse(BaseModel):
    session_id: int
    candidate_name: str
    role_title: str
    fit_score_percentage: int
    matched_skills: List[str]
    missing_skills: List[str]
    executive_summary: str
    total_questions: int
    questions: List[InterviewQuestion]


# --- Answer Evaluation Schemas ---
class EvaluationRequest(BaseModel):
    question_text: str = Field(..., min_length=5, description="Interview question")
    evaluation_criteria: str = Field(..., description="Expected criteria for the answer")
    user_answer: str = Field(..., min_length=1, description="Candidate's answer")
    target_skill_or_topic: Optional[str] = Field(default="", description="Target skill evaluated")
    session_id: Optional[int] = Field(default=None, description="Database Session ID")
    question_id: Optional[int] = Field(default=None, description="Question sequential number")


class AnswerEvaluation(BaseModel):
    score_out_of_10: float = Field(ge=0.0, le=10.0, description="Evaluation score 0.0 to 10.0")
    strengths: List[str] = Field(default_factory=list, description="Key points answered well")
    missing_points_and_gaps: List[str] = Field(default_factory=list, description="Missing concepts or gaps")
    detailed_feedback: str = Field(..., description="Constructive feedback explaining the score")
    ideal_model_answer: str = Field(..., description="Concise, senior engineer benchmark answer under 120 words")
    interview_tips: List[str] = Field(default_factory=list, description="Communication and technical tips")


class EvaluationResponse(BaseModel):
    success: bool = True
    session_id: Optional[int] = None
    evaluation: AnswerEvaluation
