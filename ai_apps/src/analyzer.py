from typing import List, Optional
from config.logging_config import logger
from ai_apps.core.constants import SYSTEM_PROMPT_ANALYSIS, SYSTEM_PROMPT_QUESTIONS
from ai_apps.src.schemas import AnalysisResponse, QuestionGenerationResponse
from ai_apps.src.llm_client import llm_client
from ai_apps.src.rag_service import rag_service


class SkillGapAnalyzer:
    """
    Core AI logic for analyzing resumes against job descriptions and generating
    adaptive interview questions grounded in candidate resume projects and JD requirements.
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
        session_id: Optional[int] = None,
    ) -> QuestionGenerationResponse:
        """
        Generates targeted interview questions focusing on gaps and core JD requirements,
        semantically grounded in specific resume project bullet points and job requirements.
        """
        logger.info(f"Generating {num_questions} targeted interview questions (Session: {session_id})...")
        
        gaps_context = ""
        if missing_skills:
            gaps_context = f"\n### IDENTIFIED SKILL GAPS / FOCUS AREAS:\n- " + "\n- ".join(missing_skills)

        # RAG Grounding Context retrieval
        rag_context_block = ""
        if session_id and missing_skills:
            evidence_blocks = []
            for skill in missing_skills[:3]:
                ctx = rag_service.get_grounding_context(session_id=session_id, topic_or_skill=skill, top_k=2)
                if ctx.get("prompt_block"):
                    evidence_blocks.append(ctx["prompt_block"])
            if evidence_blocks:
                rag_context_block = "\n\n### RAG VECTOR RETRIEVAL EVIDENCE:\n" + "\n\n".join(evidence_blocks)

        prompt = f"""### CANDIDATE RESUME:
{resume_text}

### TARGET JOB DESCRIPTION:
{jd_text}
{gaps_context}
{rag_context_block}

### TASK:
Generate exactly {num_questions} distinct, high-impact interview questions.
Ensure the questions are GROUNDED in the candidate's background and target job requirements:
1. Skill Gap Deep-Dives: Target missing or weak competencies identified against the JD.
2. Experience Verification: Reference specific claims, tools, or projects mentioned in the candidate's resume.
3. System Design & Engineering Trade-offs: Test practical judgment and production scenarios relevant to the JD.

Return the result strictly conforming to the QuestionGenerationResponse schema.
"""
        return llm_client.generate_structured_output(
            prompt=prompt,
            response_model=QuestionGenerationResponse,
            system_instruction=SYSTEM_PROMPT_QUESTIONS,
            temperature=0.3,
        )


skill_gap_analyzer = SkillGapAnalyzer()
