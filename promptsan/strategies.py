"""
Anonymization strategies for PromptSan

Implements pluggable anonymization strategies:
- RegexStrategy: Pattern-based anonymization using regular expressions
- DictStrategy: Dictionary-based replacement of known sensitive terms
- LLMStrategy: AI-powered contextual anonymization using local LLM

All strategies follow the AnonymizationStrategy protocol for consistency.
"""

from typing import Protocol, Dict
import re
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError
import xml.etree.ElementTree as ET

from .mapping import MappingStore
from .config import SanConfig


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
        for match in re.findall(pattern, text):
            token = mapping.add(match, label)
            text = text.replace(match, token)
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
    for entity, label in cfg.custom_dict.items():
        if entity in text:
            token = mapping.add(entity, label)
            text = text.replace(entity, token)
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
def _load_llm(model_id: str, base_url: str) -> ChatOpenAI:
    """
    Load and cache LLM client
    
    Args:
        model_id: Name/ID of the language model
        base_url: Base URL of the LLM API server
        
    Returns:
        Configured ChatOpenAI client
    """
    return ChatOpenAI(
        model_name=model_id,
        base_url=base_url,
        api_key="not-needed"  # Local LLM doesn't require real API key
    )


def llm_strategy(text: str, mapping: MappingStore, cfg: SanConfig, max_retries: int = 10) -> str:
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
    
    llm = _load_llm(cfg.llm_model, cfg.llm_base_url)
    prompt = ChatPromptTemplate.from_template(cfg.llm_prompt_template)
    
    feedback = ""
    
    for attempt in range(max_retries):
        try:
            # Get LLM response
            response = llm.invoke(prompt.format(text=text) + feedback)
            
            # Parse XML response
            root = ET.fromstring(response.content)
            anonymized = root.find('anonymized').text.strip()
            
            # Extract entities from XML
            entities = []
            for ent_elem in root.findall('.//entity'):
                ent = Entity(
                    original=ent_elem.get('original'),
                    token=ent_elem.get('token'),
                    label=ent_elem.get('label')
                )
                entities.append(ent)
            
            # Validate response structure
            output = LLMOutput(anonymized=anonymized, entities=entities)
            
            # Apply entity mappings to text
            for entity in output.entities:
                token = mapping.add(entity.original, entity.label)
                text = text.replace(entity.original, token)
            
            return text
            
        except (ET.ParseError, ValidationError, Exception) as e:
            feedback = f"\nPrevious output had errors: {str(e)}. Fix it and output valid XML."
            if attempt == max_retries - 1:
                raise ValueError(f"LLM anonymization failed after {max_retries} attempts: {str(e)}")
    
    return text


# Strategy registry mapping names to functions
STRATEGY_MAP: Dict[str, AnonymizationStrategy] = {
    "regex": regex_strategy,
    "dict": dict_strategy,
    "llm": llm_strategy,
}