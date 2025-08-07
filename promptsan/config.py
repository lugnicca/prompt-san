"""
Configuration module for PromptSan

Defines the SanConfig dataclass that holds all configuration options
for the PromptSanitizer, including strategy selection, custom patterns,
and LLM settings.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel


class StrategyName(str, Enum):
    """Enumeration of available anonymization strategies"""

    regex = "regex"
    dict_ = "dict"
    llm = "llm"


@dataclass(frozen=True, slots=True)
class SanConfig:
    """
    Immutable configuration for PromptSanitizer

    Args:
        strategies: List of strategy names to apply in order
        llm_model: Name of the LLM model to use (required for llm strategy)
        custom_dict: Dictionary of text->label mappings for dict strategy
        regex_patterns: Dictionary of regex->label mappings for regex strategy
        llm_base_url: Base URL for LLM API server
        llm_prompt_template: XML template for LLM anonymization prompt

    Note:
        - frozen=True makes instances immutable after creation
        - slots=True optimizes memory usage and prevents dynamic attributes
    """

    strategies: List[str] = field(default_factory=lambda: ["regex"])
    llm_model: str | None = None
    custom_dict: Dict[str, str] = field(default_factory=dict)
    regex_patterns: Dict[str, str] = field(
        default_factory=lambda: {
            r"\b\d{5}\b": "ZIP",
            r"\b\d{2}/\d{2}/\d{4}\b": "DATE",
            r"\b\d{4}-\d{2}-\d{2}\b": "DATE",
            r"\b\d{2}-\d{2}-\d{4}\b": "DATE",
            r"\b(?:\+33|0)[1-9](?:[.\-\s]?\d{2}){4}\b": "PHONE",
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b": "EMAIL",
        }
    )
    llm_base_url: str = "http://localhost:1234/v1"
    llm_prompt_template: str | None = None
    # Options for dict_strategy
    dict_use_word_boundaries: bool = True
    dict_case_insensitive: bool = False

    def validate(self) -> None:
        """
        Validates the configuration using Pydantic

        Raises:
            ValidationError: If any configuration value is invalid
        """

        class _Schema(BaseModel):
            strategies: List[str]
            llm_model: str | None
            custom_dict: Dict[str, str]
            regex_patterns: Dict[str, str]
            llm_base_url: str
            llm_prompt_template: str | None

        _Schema.model_validate(asdict(self))
