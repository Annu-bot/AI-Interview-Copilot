import pytest
from pydantic import ValidationError
from ai_apps.src.schemas import (
    AnalysisResponse,
    SkillGapDetail,
    InterviewQuestion,
    QuestionCategory,
    DifficultyLevel,
    AnswerEvaluation,
)


def test_analysis_response_schema():
    gap = SkillGapDetail(
        skill_name="Kubernetes",
        importance="Must Have",
        status="Missing",
        reasoning="Not mentioned in the resume projects or skills section."
    )
    analysis = AnalysisResponse(
        candidate_name="Alex",
        estimated_experience_level="Mid-level (3-5 yrs)",
        fit_score_percentage=80,
        executive_summary="Solid Python candidate with modern backend skills.",
        matched_skills=["Python", "FastAPI", "PostgreSQL"],
        missing_skills=["Kubernetes"],
        skill_gap_breakdown=[gap],
        recommended_focus_areas=["Container orchestration with Kubernetes"]
    )
    assert analysis.fit_score_percentage == 80
    assert len(analysis.matched_skills) == 3
    assert analysis.skill_gap_breakdown[0].skill_name == "Kubernetes"


def test_question_schema():
    q = InterviewQuestion(
        id=1,
        stage="Stage 1: Warm-up & Intro",
        category=QuestionCategory.INTRODUCTION,
        target_skill_or_topic="Engineering Background",
        difficulty=DifficultyLevel.EASY,
        spoken_intro="Welcome! Let's start with a brief walk-through of your background.",
        question_text="Could you walk me through your engineering career and a recent complex system you designed?",
        evaluation_criteria="Clear communication, structured summary, mentions production impact."
    )
    assert q.id == 1
    assert q.stage == "Stage 1: Warm-up & Intro"
    assert q.spoken_intro.startswith("Welcome")
    assert q.category == QuestionCategory.INTRODUCTION


def test_evaluation_schema():
    eval_model = AnswerEvaluation(
        score_out_of_10=8.5,
        strengths=["Clear explanation of event loop", "Mentioned threadpool executor"],
        missing_points_and_gaps=["Did not explain blocking CPU-bound tasks"],
        detailed_feedback="Very good answer with strong fundamentals.",
        ideal_model_answer="In FastAPI, 'async def' runs directly on the main event loop...",
        interview_tips=["Mention ProcessPoolExecutor for CPU heavy tasks."]
    )
    assert eval_model.score_out_of_10 == 8.5
    assert len(eval_model.strengths) == 2


def test_invalid_score_validation():
    with pytest.raises(ValidationError):
        AnswerEvaluation(
            score_out_of_10=15.0,
            strengths=[],
            missing_points_and_gaps=[],
            detailed_feedback="Too high",
            ideal_model_answer="",
            interview_tips=[]
        )
