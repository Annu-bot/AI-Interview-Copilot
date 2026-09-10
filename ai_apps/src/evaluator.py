from typing import Optional
from config.logging_config import logger
from ai_apps.core.constants import SYSTEM_PROMPT_EVALUATION
from ai_apps.src.schemas import AnswerEvaluation, EvaluationResponse
from ai_apps.src.llm_client import llm_client
from ai_apps.src.rag_service import rag_service


class AnswerEvaluator:
    """
    Evaluates candidate responses against interview questions and evaluation criteria.
    Provides strict scoring, constructive feedback, and benchmark model answers,
    grounded in resume context and job requirements.
    """

    def evaluate_candidate_answer(
        self,
        question_text: str,
        evaluation_criteria: str,
        user_answer: str,
        target_skill: str = "",
        session_id: Optional[int] = None,
    ) -> EvaluationResponse:
        """
        Evaluates a candidate's response and returns detailed feedback and score.
        """
        logger.info(f"Evaluating response for question: '{question_text[:50]}...' (Session: {session_id})")

        rag_context_block = ""
        if session_id and target_skill:
            try:
                ctx = rag_service.get_grounding_context(session_id=session_id, topic_or_skill=target_skill, top_k=2)
                if ctx.get("prompt_block"):
                    rag_context_block = f"\n\n### RAG RETRIEVED CONTEXT (RESUME EVIDENCE & JD STANDARDS):\n{ctx['prompt_block']}"
            except Exception as e:
                logger.debug(f"RAG retrieval skipped for evaluation: {e}")

        prompt = f"""### INTERVIEW QUESTION:
{question_text}

### TARGET TOPIC / SKILL:
{target_skill if target_skill else 'General Engineering'}

### EXPECTED EVALUATION CRITERIA:
{evaluation_criteria}

### CANDIDATE'S SUBMITTED ANSWER:
{user_answer}
{rag_context_block}

### TASK:
Critique the candidate's answer using the rubric and grounded context.
Identify:
1. Score out of 10.0 (float).
2. Exact strengths observed.
3. Missing technical points, depth deficiencies, or inaccuracies.
4. Detailed feedback explaining the score.
5. Ideal model answer (how a Staff/Principal engineer would answer succinctly and powerfully).
6. Practical tips for answering in real interviews.

Return the result strictly conforming to the AnswerEvaluation schema.
"""
        evaluation = llm_client.generate_structured_output(
            prompt=prompt,
            response_model=AnswerEvaluation,
            system_instruction=SYSTEM_PROMPT_EVALUATION,
            temperature=0.2,
        )

        return EvaluationResponse(success=True, evaluation=evaluation)


answer_evaluator = AnswerEvaluator()
