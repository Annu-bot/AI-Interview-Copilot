"""
Core module for AI Application containing exceptions, constants, and utilities.
"""
from ai_apps.core.constants import (
    SYSTEM_PROMPT_ANALYSIS,
    SYSTEM_PROMPT_QUESTIONS,
    SYSTEM_PROMPT_EVALUATION,
)
from ai_apps.core.exceptions import (
    AIAppException,
    DocumentParsingError,
    LLMInferenceError,
    ValidationError,
)

__all__ = [
    "SYSTEM_PROMPT_ANALYSIS",
    "SYSTEM_PROMPT_QUESTIONS",
    "SYSTEM_PROMPT_EVALUATION",
    "AIAppException",
    "DocumentParsingError",
    "LLMInferenceError",
    "ValidationError",
]
