"""
PromptSan - Minimal yet powerful text anonymization library

A micro-library for anonymizing and deanonymizing text with pluggable strategies.
Supports regex patterns, custom dictionaries, and LLM-based anonymization.

Basic usage:
    >>> from promptsan import PromptSanitizer, SanConfig
    >>> sanitizer = PromptSanitizer()
    >>> result = sanitizer.anonymize("Keanu Reeves lives at john@email.com")
    >>> print(result.text)  # "Keanu Reeves lives at __EMAIL_1__"
    >>> restored = sanitizer.deanonymize(result.text, result.mapping)
    >>> print(restored)  # "Keanu Reeves lives at john@email.com"
"""

from .config import SanConfig, StrategyName
from .sanitizer import AnonymizeResult, PromptSanitizer

__version__ = "1.0.1"
__author__ = "Lugnicca"
__email__ = "lugnicca@gmail.com"

__all__ = [
    "PromptSanitizer",
    "AnonymizeResult",
    "SanConfig",
    "StrategyName",
]
