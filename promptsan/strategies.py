"""
Anonymization strategies for PromptSan

Implements pluggable anonymization strategies:
- RegexStrategy: Pattern-based anonymization using regular expressions
- DictStrategy: Dictionary-based replacement of known sensitive terms
- LLMStrategy: AI-powered contextual anonymization using local LLM

All strategies follow the AnonymizationStrategy protocol for consistency.
"""

import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from typing import Any, Dict, List, Protocol, Tuple

from pydantic import BaseModel, ValidationError

from .config import SanConfig
from .mapping import MappingStore


class AnonymizationStrategy(Protocol):
    """Protocol defining the interface for anonymization strategies"""

    def __call__(self, text: str, mapping: MappingStore, cfg: SanConfig) -> str:
        """
        Anonymize text using this strategy

        Args:
            text: Input text to anonymize
            mapping: Bidirectional mapping store for entities/tokens
            cfg: Configuration object with strategy-specific settings

        Returns:
            Text with sensitive entities replaced by anonymization tokens
        """
        ...


def _apply_replacements_non_overlapping(
    text: str, replacements: List[Tuple[int, int, str]]
) -> str:
    """
    Apply a list of replacements to the text without overlap.

    replacements: list of tuples (start, end, replacement)
    Assumes replacements are non-overlapping and sorted by start index.
    """
    if not replacements:
        return text

    result_parts: List[str] = []
    cursor = 0
    for start, end, repl in replacements:
        if start < cursor:
            # Skip overlapping replacement
            continue
        result_parts.append(text[cursor:start])
        result_parts.append(repl)
        cursor = end
    result_parts.append(text[cursor:])
    return "".join(result_parts)


def regex_strategy(text: str, mapping: MappingStore, cfg: SanConfig) -> str:
    """
    Anonymize text using regular expression patterns

    Uses configurable regex patterns from cfg.regex_patterns to detect
    and replace entities like emails, phone numbers, dates, etc.

    Args:
        text: Input text to anonymize
        mapping: Mapping store to track entity->token relationships
        cfg: Configuration containing regex_patterns dict

    Returns:
        Text with pattern matches replaced by tokens
    """
    for pattern, label in cfg.regex_patterns.items():
        # Build all matches with positions, using the full match
        try:
            matches = list(re.finditer(pattern, text))
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern '{pattern}': {exc}")

        # Convert to non-overlapping replacements (left-to-right)
        replacements: List[Tuple[int, int, str]] = []
        for m in matches:
            full_match = m.group(0)
            if not full_match:
                continue
            token = mapping.add(full_match, label)
            replacements.append((m.start(), m.end(), token))

        if replacements:
            text = _apply_replacements_non_overlapping(text, replacements)
    return text


def dict_strategy(text: str, mapping: MappingStore, cfg: SanConfig) -> str:
    """
    Anonymize text using dictionary-based replacement

    Replaces exact string matches from cfg.custom_dict with anonymization
    tokens. Useful for domain-specific entities like company names,
    project codenames, or classification levels.

    Args:
        text: Input text to anonymize
        mapping: Mapping store to track entity->token relationships
        cfg: Configuration containing custom_dict mappings

    Returns:
        Text with dictionary matches replaced by tokens
    """
    use_word_boundaries = getattr(cfg, "dict_use_word_boundaries", True)
    case_insensitive = getattr(cfg, "dict_case_insensitive", False)

    flags = re.IGNORECASE if case_insensitive else 0
    replacements: List[Tuple[int, int, str]] = []

    # Collect all occurrences for all entities, then apply non-overlapping
    for entity, label in cfg.custom_dict.items():
        if not entity:
            continue
        escaped = re.escape(entity)
        if use_word_boundaries:
            pattern = rf"\b{escaped}\b"
        else:
            pattern = escaped

        for m in re.finditer(pattern, text, flags):
            token = mapping.add(m.group(0), label)
            replacements.append((m.start(), m.end(), token))

    # Sort by start index to apply deterministically
    replacements.sort(key=lambda r: r[0])
    text = _apply_replacements_non_overlapping(text, replacements)
    return text


# Pydantic models for LLM response validation
class Entity(BaseModel):
    """Represents an entity found by the LLM"""

    original: str
    token: str
    label: str


class LLMOutput(BaseModel):
    """Expected structure of LLM anonymization response"""

    anonymized: str
    entities: list[Entity]


@lru_cache(maxsize=2)
def _load_llm(model_id: str, base_url: str) -> Any:
    """
    Load and cache LLM client

    Args:
        model_id: Name/ID of the language model
        base_url: Base URL of the LLM API server

    Returns:
        Configured ChatOpenAI client
    """
    # Import locally to make langchain an optional dependency unless LLM is used
    from langchain_openai import ChatOpenAI  # type: ignore

    client = ChatOpenAI(
        model=model_id,
        base_url=base_url,
        api_key="not-needed",
    )
    return client


def llm_strategy(
    text: str, mapping: MappingStore, cfg: SanConfig, max_retries: int = 10
) -> str:
    """
    Anonymize text using local LLM with XML-based prompting

    Uses a language model to intelligently identify and anonymize entities
    based on context. Includes retry mechanism for robustness.

    Args:
        text: Input text to anonymize
        mapping: Mapping store to track entity->token relationships
        cfg: Configuration with LLM settings and prompt template
        max_retries: Maximum number of retry attempts if LLM fails

    Returns:
        Text with LLM-identified entities replaced by tokens

    Raises:
        ValueError: If LLM model or prompt template not configured
        ValueError: If LLM fails after maximum retry attempts
    """
    if not cfg.llm_model:
        raise ValueError("LLM model not specified in config")

    if not cfg.llm_prompt_template:
        raise ValueError("LLM prompt template not specified in config")

    # Import locally to avoid mandatory dependency unless used
    from langchain.prompts import ChatPromptTemplate  # type: ignore

    llm = _load_llm(cfg.llm_model, cfg.llm_base_url)
    prompt = ChatPromptTemplate.from_template(cfg.llm_prompt_template)

    feedback = ""

    for attempt in range(max_retries):
        try:
            # Get LLM response
            response = llm.invoke(prompt.format(text=text) + feedback)

            # Parse XML response
            root = ET.fromstring(response.content)
            anon_node = root.find("anonymized")
            anonymized = (anon_node.text or "").strip() if anon_node is not None else ""

            # Extract entities from XML
            entities = []
            for ent_elem in root.findall(".//entity"):
                original = ent_elem.get("original") or ""
                token = ent_elem.get("token") or ""
                label = ent_elem.get("label") or ""
                ent = Entity(original=original, token=token, label=label)
                entities.append(ent)

            # Validate response structure
            output = LLMOutput(anonymized=anonymized, entities=entities)

            # Apply entity mappings to text
            for entity in output.entities:
                token = mapping.add(entity.original, entity.label)
                text = text.replace(entity.original, token)

            return text

        except (ET.ParseError, ValidationError, Exception) as e:
            feedback = (
                f"\nPrevious output had errors: {str(e)}. Fix it and output valid XML."
            )
            if attempt == max_retries - 1:
                raise ValueError(
                    f"LLM anonymization failed after {max_retries} attempts: {str(e)}"
                )

    return text


# Strategy registry mapping names to functions
STRATEGY_MAP: Dict[str, AnonymizationStrategy] = {
    "regex": regex_strategy,
    "dict": dict_strategy,
    "llm": llm_strategy,
}
