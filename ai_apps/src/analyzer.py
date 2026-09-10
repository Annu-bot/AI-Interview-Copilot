from typing import List, Optional
from config.logging_config import logger
from ai_apps.core.constants import SYSTEM_PROMPT_ANALYSIS, SYSTEM_PROMPT_QUESTIONS
from ai_apps.src.schemas import AnalysisResponse, QuestionGenerationResponse
from ai_apps.src.llm_client import llm_client


class SkillGapAnalyzer:
    """
    Core AI logic for analyzing resumes against job descriptions and generating
    adaptive interview questions targeting identified skill gaps.
    """

    def analyze_resume_and_jd(self, resume_text: str, jd_text: str) -> AnalysisResponse:
        """
        Compares resume against job description and extracts skill gap matrix & fit score.
        """
        logger.info("Starting Resume vs JD Skill Gap Analysis...")
        prompt = f"""### CANDIDATE RESUME:
{resume_text}

### TARGET JOB DESCRIPTION:
{jd_text}

### TASK:
Perform a comprehensive skill-gap analysis comparing the candidate's resume with the job description.
Return the structured analysis strictly adhering to the specified schema.
"""
        return llm_client.generate_structured_output(
            prompt=prompt,
            response_model=AnalysisResponse,
            system_instruction=SYSTEM_PROMPT_ANALYSIS,
            temperature=0.2,
        )

    def generate_interview_questions(
        self,
        resume_text: str,
        jd_text: str,
        missing_skills: Optional[List[str]] = None,
        num_questions: int = 5,
    ) -> QuestionGenerationResponse:
        """
        Generates targeted interview questions focusing on gaps and core JD requirements.
        """
        logger.info(f"Generating {num_questions} targeted interview questions...")
        gaps_context = ""
        if missing_skills:
            gaps_context = f"\n### IDENTIFIED SKILL GAPS / FOCUS AREAS:\n- " + "\n- ".join(missing_skills)

        prompt = f"""### CANDIDATE RESUME:
{resume_text}

### TARGET JOB DESCRIPTION:
{jd_text}
{gaps_context}

### TASK:
Generate exactly {num_questions} distinct, high-impact interview questions.
Ensure the questions cover:
1. Skill Gap Deep-Dives (targeting missing or weak competencies).
2. Project and experience verification based on claims in the resume.
3. System design or practical engineering trade-offs.

Return the result strictly conforming to the QuestionGenerationResponse schema.
"""
        return llm_client.generate_structured_output(
            prompt=prompt,
            response_model=QuestionGenerationResponse,
            system_instruction=SYSTEM_PROMPT_QUESTIONS,
            temperature=0.3,
        )


skill_gap_analyzer = SkillGapAnalyzer()
