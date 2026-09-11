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
        num_questions: int = 10,
        session_id: Optional[int] = None,
    ) -> QuestionGenerationResponse:
        """
        Generates targeted interview questions focusing on gaps and core JD requirements,
        semantically grounded in specific resume project bullet points and job requirements,
        structured across realistic interview stages (Warm-up, Project Deep-Dive, Skill Gaps, System Design, Culture).
        """
        logger.info(f"Generating {num_questions} targeted interview questions (Session: {session_id})...")
        
        gaps_context = ""
        if missing_skills:
            gaps_context = f"\n### IDENTIFIED SKILL GAPS / FOCUS AREAS:\n- " + "\n- ".join(missing_skills)

        # RAG Grounding Context retrieval
        rag_context_block = ""
        if session_id and missing_skills:
            evidence_blocks = []
            for skill in missing_skills[:4]:
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
Generate exactly {num_questions} distinct, high-impact interview questions simulating a complete real-life technical interview loop:
1. Question 1 (Warm-up): Welcoming intro asking the candidate to introduce their background and recent engineering achievements.
2. Questions 2-{min(4, num_questions)} (Project Deep-Dive): Verify concrete resume projects, tools, and implementation decisions.
3. Questions {min(5, num_questions)}-{min(7, num_questions)} (Skill Gaps & Core JD): Probe directly on missing or weak competencies required by the JD.
4. Questions {min(8, num_questions)}-{min(9, num_questions)} (System Design): Scalability, concurrency, failure modes, caching, and trade-offs.
5. Question {num_questions} (Engineering Culture): Production outage handling, architectural trade-off disagreements, and candidate wrap-up.

For every question provide:
- `id`: Sequential integer (1 to {num_questions})
- `stage`: Name of the interview stage
- `category`: Question category enum
- `target_skill_or_topic`: Target skill/area tested
- `difficulty`: Easy / Medium / Hard
- `spoken_intro`: A natural conversational sentence for AI Voice TTS before stating the question
- `question_text`: The full technical question
- `evaluation_criteria`: Criteria for scoring

Return the result strictly conforming to the QuestionGenerationResponse schema.
"""
        return llm_client.generate_structured_output(
            prompt=prompt,
            response_model=QuestionGenerationResponse,
            system_instruction=SYSTEM_PROMPT_QUESTIONS,
            temperature=0.3,
        )


skill_gap_analyzer = SkillGapAnalyzer()
