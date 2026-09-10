"""
Custom Exceptions for the AI Interview Copilot
"""


class AIAppException(Exception):
    """Base exception for all AI application errors."""
    pass


class DocumentParsingError(AIAppException):
    """Raised when parsing PDF, DOCX, or text files fails."""
    pass


class LLMInferenceError(AIAppException):
    """Raised when calling LLM API or parsing structured JSON fails."""
    pass


class ValidationError(AIAppException):
    """Raised when input validation fails."""
    pass
