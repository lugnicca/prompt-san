"""
Main sanitizer module for PromptSan

Provides the PromptSanitizer class which serves as the primary interface
for text anonymization and deanonymization operations.
"""

from typing import Dict, Generator, NamedTuple

from .config import SanConfig
from .mapping import MappingStore
from .strategies import STRATEGY_MAP, AnonymizationStrategy


class AnonymizeResult(NamedTuple):
    """
    Result of an anonymization operation

    Attributes:
        text: Anonymized text with entities replaced by tokens
        mapping: Dictionary mapping original entities to their tokens
    """

    text: str
    mapping: Dict[str, str]


class PromptSanitizer:
    """
    Main interface for text anonymization and deanonymization

    Supports multiple anonymization strategies that can be combined
    and executed in sequence. Strategies can be dynamically registered
    for extensibility.

    Example:
        >>> config = SanConfig(strategies=["regex", "dict"])
        >>> sanitizer = PromptSanitizer(config)
        >>> result = sanitizer.anonymize("Contact john@email.com")
        >>> print(result.text)  # "Contact __EMAIL_1__"
        >>> restored = sanitizer.deanonymize(result.text, result.mapping)
        >>> print(restored)  # "Contact john@email.com"
    """

    __slots__ = ("cfg", "strategy_map")

    def __init__(self, cfg: SanConfig | None = None):
        """
        Initialize PromptSanitizer with configuration

        Args:
            cfg: Configuration object, uses defaults if None
        """
        self.cfg = cfg or SanConfig()
        self.cfg.validate()

        # Copy strategy map to allow custom registrations per instance
        self.strategy_map: Dict[str, AnonymizationStrategy] = STRATEGY_MAP.copy()

    def register_strategy(self, name: str, func: AnonymizationStrategy) -> None:
        """
        Register a custom anonymization strategy

        Args:
            name: Name to identify the strategy
            func: Strategy function following AnonymizationStrategy protocol
        """
        self.strategy_map[name] = func

    def anonymize(self, text: str) -> AnonymizeResult:
        """
        Anonymize text using configured strategies

        Applies strategies in the order specified in configuration.
        Each strategy operates on the output of the previous strategy.

        Args:
            text: Original text to anonymize

        Returns:
            AnonymizeResult containing anonymized text and entity mappings

        Raises:
            ValueError: If an unknown strategy name is configured
        """
        mapping_store = MappingStore()

        for strategy_name in self.cfg.strategies:
            if strategy_name not in self.strategy_map:
                raise ValueError(f"Unknown strategy: {strategy_name}")

            strategy = self.strategy_map[strategy_name]
            text = strategy(text, mapping_store, self.cfg)

        return AnonymizeResult(text, mapping_store.e2t)

    def deanonymize(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Deanonymize text by replacing tokens with original entities

        Args:
            text: Anonymized text containing tokens
            mapping: Dictionary mapping entities to tokens

        Returns:
            Original text with tokens replaced by entities
        """
        mapping_store = MappingStore.from_dict(mapping)
        return mapping_store.deanonymize(text)

    def deanonymize_stream(
        self,
        gen: Generator[str, None, None],
        mapping: Dict[str, str],
    ) -> Generator[str, None, None]:
        """
        Deanonymize text from a stream/generator

        Useful for processing real-time streams like LLM output where
        tokens might be split across chunks.

        Args:
            gen: Generator yielding text chunks
            mapping: Dictionary mapping entities to tokens

        Yields:
            Deanonymized text chunks
        """
        mapping_store = MappingStore.from_dict(mapping)
        yield from mapping_store.deanonymize_stream(gen)
