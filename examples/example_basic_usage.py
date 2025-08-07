#!/usr/bin/env python3
"""
Basic PromptSan Usage Examples

This example demonstrates the fundamental features of PromptSan:
- Default configuration (regex strategy)
- Basic anonymization and deanonymization
- Understanding the mapping system
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from promptsan import PromptSanitizer, SanConfig


def main():
    print("PromptSan - Basic Usage Examples")
    print("=" * 50)

    # Example 1: Default configuration
    print("\nExample 1: Default Configuration (Regex Strategy)")
    print("-" * 50)

    sanitizer = PromptSanitizer()  # Uses default config

    text = """
    Hello, I am Keanu Reeves, born on 03/15/1985.
    My email: keanu.reeves@company.com
    Phone: +1-555-123-4567
    ZIP code: 90210
    """

    print(f"Original text:\n{text}")

    # Anonymize
    result = sanitizer.anonymize(text)
    print(f"Anonymized text:\n{result.text}")

    print("Generated mapping:")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")

    # Deanonymize
    restored = sanitizer.deanonymize(result.text, result.mapping)
    print(f"Restored text:\n{restored}")

    # Verify perfect restoration
    assert text.strip() == restored.strip()
    print("✓ Perfect restoration verified!")

    # Example 2: Custom regex patterns
    print("\nExample 2: Custom Regex Patterns")
    print("-" * 50)

    custom_config = SanConfig(
        strategies=["regex"],
        regex_patterns={
            r"\b[A-Z][a-z]+ [A-Z][a-z]+\b": "PERSON",  # Full names
            r"\b[A-Z][a-z]+\b": "NAME",  # Single names/cities
            r"\bSSN:\s*\d{3}-\d{2}-\d{4}\b": "SSN",  # Social Security Numbers
            r"\b\d{1,5}\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd)\b": "ADDRESS",
        },
    )

    sanitizer = PromptSanitizer(custom_config)

    text = """
    Patient: Jane Smith
    Address: 123 Oak Street
    SSN: 123-45-6789
    City: Boston
    """

    print(f"Original text:\n{text}")

    result = sanitizer.anonymize(text)
    print(f"Anonymized text:\n{result.text}")

    print("Custom mapping:")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")

    print("✓ Custom regex patterns working!")


if __name__ == "__main__":
    main()
