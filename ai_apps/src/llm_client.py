import json
import re
from typing import Type, TypeVar, Optional, List
from pydantic import BaseModel, ValidationError
import google.generativeai as genai
from config.settings import settings
from config.logging_config import logger
from ai_apps.core.exceptions import LLMInferenceError

T = TypeVar("T", bound=BaseModel)

# Verified active Gemini models with independent free-tier quotas
CANDIDATE_MODELS: List[str] = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]


class LLMClient:
    """
    LLM Client handling model calls, schema validation, provider routing,
    and automatic rate-limit & model fallback.
    """

    def __init__(self):
        self.use_open_source = settings.USE_OPEN_SOURCE
        self._gemini_initialized = False

    def _init_gemini(self):
        """Lazy initialization of Google Gemini SDK."""
        if not self._gemini_initialized:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                raise LLMInferenceError(
                    "GEMINI_API_KEY is not set. Please add your free API key to config/local.env. "
                    "You can generate a free key at https://aistudio.google.com/"
                )
            genai.configure(api_key=api_key)
            self._gemini_initialized = True
            logger.info("Initialized Google Gemini client.")

    def _clean_json_string(self, text: str) -> str:
        """Strips markdown code blocks from JSON output."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def generate_structured_output(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """
        Generates structured output matching a Pydantic schema.
        Routes to Cloud API or Local LLM based on USE_OPEN_SOURCE flag.
        """
        if self.use_open_source:
            logger.warning("USE_OPEN_SOURCE=True: Routing to Local Open-Source LLM...")
            raise NotImplementedError(
                f"Local Open-Source LLM integration ({settings.LOCAL_LLM_MODEL} at {settings.LOCAL_LLM_BASE_URL}) "
                "is reserved for future versions. Keep USE_OPEN_SOURCE=False in config/local.env for Cloud API."
            )

        return self._call_gemini_with_fallback(
            prompt=prompt,
            response_model=response_model,
            system_instruction=system_instruction,
            temperature=temperature,
        )

    def _call_gemini_with_fallback(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """
        Calls Gemini API with automatic model fallback in case of rate limits (429) or model deprecation (404).
        """
        self._init_gemini()

        # Build candidate list with configured model first
        models_to_try = [settings.GEMINI_MODEL]
        for m in CANDIDATE_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        json_schema_str = json.dumps(response_model.model_json_schema(), indent=2)
        enhanced_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: Respond ONLY with valid JSON strictly conforming to this JSON Schema:\n"
            f"{json_schema_str}\n"
        )

        for model_name in models_to_try:
            try:
                logger.info(f"Dispatching prompt to Gemini ({model_name})...")
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={
                        "temperature": temperature,
                        "response_mime_type": "application/json",
                    },
                    system_instruction=system_instruction,
                )

                response = model.generate_content(enhanced_prompt)
                raw_text = response.text or ""
                cleaned_json = self._clean_json_string(raw_text)

                parsed_data = json.loads(cleaned_json)
                validated = response_model.model_validate(parsed_data)
                logger.info(f"Successfully validated {response_model.__name__} using {model_name}")
                return validated

            except (json.JSONDecodeError, ValidationError) as parse_err:
                logger.error(f"JSON validation failed on {model_name}: {parse_err}")
                last_error = parse_err
                break  # Don't switch models if response arrived but schema had error

            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Model {model_name} failed with: {err_msg[:120]}. Switching to next fallback model...")
                last_error = e
                continue

        logger.error(f"All candidate Gemini models failed. Last error: {last_error}")
        raise LLMInferenceError(f"Gemini API Error: {str(last_error)}")


llm_client = LLMClient()
