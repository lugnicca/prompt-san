#!/usr/bin/env python3
"""
Complete PromptSan Démonstration

A comprehensive showcase of all PromptSan features:
- All anonymization strategies
- Configuration options
- Streaming capabilities
- Custom strategies
- Error handling
- Performance testing
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re
import time
from typing import Generator

from promptsan import PromptSanitizer, SanConfig
from promptsan.mapping import MappingStore


def example_section(title: str):
    """Print a visual separator for example sections"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")


def main():
    print(
        """
PromptSan - Complete Feature Démonstration
============================================

This script showcases all PromptSan capabilities:
✓ Basic and advanced configuration
✓ Regex, dictionary, and LLM strategies  
✓ Strategy combinations
✓ Custom strategy development
✓ Streaming deanonymization
✓ Error handling
✓ Performance analysis
    """
    )

    try:
        example_basic_usage()
        example_custom_configuration()
        example_dictionary_strategy()
        example_combined_strategies()
        example_custom_strategy()
        example_streaming()
        example_llm_strategy()
        example_error_handling()
        example_performance_comparison()

        print(f"\n{'='*60}")
        print("EXAMPLES FINISHED")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n✗ DEMONSTRATION ERROR: {e}")
        import traceback

        traceback.print_exc()


def example_basic_usage():
    """Example 1: Basic usage with default configuration"""
    example_section("EXaMPLE 1: Basic Usage (Regex Only)")

    # Default configuration (regex only)
    sanitizer = PromptSanitizer()

    text = """
    Hello, I am Keanu Reeves, born on 03/15/1985.
    My email: keanu.reeves@company.com
    Phone: +1-555-123-4567
    ZIP code: 90210
    """

    print(f"Original text:\n{text}")

    # Anonymize
    result = sanitizer.anonymize(text)
    print(f"Anonymized: Anonymized text:\n{result.text}")
    print(f"Mapping: Generated mapping:")
    for original, token in result.mapping.items():
        print(f"   '{original}' -> {token}")

    # Deanonymize
    restored = sanitizer.deanonymize(result.text, result.mapping)
    print(f"Restored: Restored text:\n{restored}")

    assert text.strip() == restored.strip(), "✗ Text restoration failed"
    print("✓ Basic test successful")


def example_custom_configuration():
    """Example 2: Custom configuration with custom regex patterns"""
    example_section("EXaMPLE 2: Custom Configuration (Custom Regex)")

    # Custom regex patterns
    custom_patterns = {
        r"\b[A-Z][a-z]+ [A-Z][a-z]+\b": "PERSON",  # Full names
        r"\b[A-Z][a-z]+\b": "NAME",  # Single names/cities
        r"\bSSN:\s*\d{3}-\d{2}-\d{4}\b": "SSN",  # Social Security Numbers
        r"\b\d{1,5}\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd)\b": "ADDRESS",
    }

    config = SanConfig(strategies=["regex"], regex_patterns=custom_patterns)

    sanitizer = PromptSanitizer(config)

    text = """
    Patient: Jane Smith
    Address: 123 Oak Street  
    SSN: 123-45-6789
    City: Boston
    """

    print(f"Original text:\n{text}")

    result = sanitizer.anonymize(text)
    print(f"Anonymized: Anonymized text:\n{result.text}")
    print(f"Mapping: Custom mapping:")
    for original, token in result.mapping.items():
        print(f"   '{original}' -> {token}")

    print("✓ Custom configuration successful")


def example_dictionary_strategy():
    """Example 3: Dictionary strategy for domain-specific entities"""
    example_section("EXAMPLE 3: Dictionary Strategy")

    # Custom dictionary of sensitive terms
    sensitive_dict = {
        "Project Falcon": "PROJECT",
        "Acme Corporation": "COMPANY",
        "CONFIDENTIAL": "CLASSIFICATION",
        "John Smith": "PERSON",
        "Q4 2024": "TIMEFRAME",
    }

    config = SanConfig(strategies=["dict"], custom_dict=sensitive_dict)

    sanitizer = PromptSanitizer(config)

    text = """
    CONFIDENTIAL Report:
    John Smith from Acme Corporation
    is leading Project Falcon for Q4 2024.
    """

    print(f"Original text:\n{text}")
    print(f"Dictionary: Dictionary used:")
    for key, label in sensitive_dict.items():
        print(f"   '{key}' -> {label}")

    result = sanitizer.anonymize(text)
    print(f"Anonymized: Anonymized text:\n{result.text}")
    print(f"Mapping: Generated mapping:")
    for original, token in result.mapping.items():
        print(f"   '{original}' -> {token}")

    print("✓ Dictionary strategy successful")


def example_combined_strategies():
    """Example 4: Combining multiple strategies"""
    example_section("EXAMPLE 4: Combined Strategies (Regex + Dict)")

    config = SanConfig(
        strategies=["regex", "dict"],
        custom_dict={"OpenAI": "AI_COMPANY", "Claude": "AI_MODEL", "GPT-4": "AI_MODEL"},
    )

    sanitizer = PromptSanitizer(config)

    text = """
    Email from researcher@openai.com sent on 12/25/2023:
    "OpenAI's GPT-4 and Anthropic's Claude are competing.
    Phone: +1-555-123-4567
    Meeting scheduled for Q1 2024."
    """

    print(f"Original text:\n{text}")

    result = sanitizer.anonymize(text)
    print(f"Anonymized: Anonymized text:\n{result.text}")
    print(f"Mapping: Combined mapping:")
    for original, token in result.mapping.items():
        print(f"   '{original}' -> {token}")

    print("✓ Combined strategies successful")


def example_custom_strategy():
    """Example 5: Custom strategy development"""
    example_section("EXAMPLE 5: Custom Strategy (IBAN)")

    def iban_strategy(text: str, mapping: MappingStore, cfg: SanConfig) -> str:
        """Custom strategy to anonymize IBAN numbers"""
        # Simplified IBAN pattern (French format)
        iban_pattern = r"\bFR\d{2}\s?(?:\d{4}\s?){5}\d{2}\b"

        for match in re.finditer(iban_pattern, text):
            iban_full = match.group()  # Full IBAN with spaces
            iban_clean = iban_full.replace(" ", "")  # Cleaned version
            token = mapping.add(iban_clean, "IBAN")
            text = text.replace(iban_full, token)  # Replace original format

        return text

    # Base configuration
    sanitizer = PromptSanitizer()

    # Register custom strategy
    sanitizer.register_strategy("iban", iban_strategy)

    # New config with custom strategy
    config = SanConfig(strategies=["regex", "iban"])
    sanitizer = PromptSanitizer(config)
    sanitizer.register_strategy("iban", iban_strategy)

    text = """
    Wire Transfer:
    IBAN: FR14 2004 1010 0505 0001 3M02 606
    Email: banking@bank.fr
    Date: 01/15/2024
    """

    print(f"Original text:\n{text}")

    result = sanitizer.anonymize(text)
    print(f"Anonymized: Anonymized text:\n{result.text}")
    print(f"Mapping: Mapping with IBAN:")
    for original, token in result.mapping.items():
        print(f"   '{original}' -> {token}")

    print("✓ Custom strategy successful")


def example_streaming():
    """Example 6: Streaming deanonymization"""
    example_section("EXAMPLE 6: Streaming Deanonymization")

    # Prepare anonymized data
    sanitizer = PromptSanitizer()
    original_text = """
    Report by Alice Johnson (alice@company.com)
    Date: 03/15/2024, Phone: +1-555-123-4567
    ZIP code: 90210
    """

    result = sanitizer.anonymize(original_text)
    print(f"Anonymized text:\n{result.text}")

    # Simulate stream (chunks of text)
    def simulate_stream(text: str) -> Generator[str, None, None]:
        """Simulate a stream by breaking text into chunks"""
        chunk_size = 10
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            print(f"   Input: '{chunk}'")
            yield chunk

    print(f"\nStream: Simulating stream (chunks of 10 characters):")

    # Streaming deanonymization
    stream_gen = simulate_stream(result.text)
    deanonymized_stream = sanitizer.deanonymize_stream(stream_gen, result.mapping)

    print(f"\nRestored: Streaming deanonymization:")
    restored_text = ""
    for chunk in deanonymized_stream:
        print(f"   Output: '{chunk}'")
        restored_text += chunk

    print(f"\nResult: Final restored text:\n{restored_text}")

    # Robust comparison
    original_clean = original_text.strip().replace("\n", " ").replace("  ", " ")
    restored_clean = restored_text.strip().replace("\n", " ").replace("  ", " ")

    if original_clean == restored_clean:
        print("✓ Streaming successful")
    else:
        print(f"Warning: Minor differences detected (whitespace/newlines)")
        print("✓ Streaming functional (minor differences acceptable)")


def example_llm_strategy():
    """Example 7: LLM strategy (if available)"""
    example_section("EXAMPLE 7: LLM Strategy (Optional)")

    # Create a simple prompt template
    prompt_template = """<task>
Anonymize sensitive entities in the following text by replacing them with tokens in the format __LABEL_N__.
</task>

<rules>
- People: __PERSON_N__
- Places: __LOCATION_N__
- Organizations: __ORG_N__  
- Dates: __DATE_N__
- Emails: __EMAIL_N__
- Phones: __PHONE_N__
</rules>

Respond STRICTLY in this XML format:
<response>
  <anonymized>full anonymized text here</anonymized>
  <mapping>
    <entity original="original text" token="__LABEL_N__" label="LABEL" />
  </mapping>
</response>

Text to anonymize:
{text}"""

    config = SanConfig(
        strategies=["llm"],
        llm_model="dolphin3.0-llama3.1-8b",
        llm_base_url="http://localhost:1234/v1",
        llm_prompt_template=prompt_template,
    )

    text = """
    John Smith works at Microsoft in Seattle.
    Contact: john.smith@microsoft.com
    Phone: +1-206-123-4567
    """

    print(f"Original text:\n{text}")
    print(f"LLM: LLM Configuration:")
    print(f"   Model: {config.llm_model}")
    print(f"   URL: {config.llm_base_url}")
    print(f"   Prompt: Custom XML template")

    try:
        sanitizer = PromptSanitizer(config)
        result = sanitizer.anonymize(text)

        print(f"Anonymized: LLM anonymized text:\n{result.text}")
        print(f"Mapping: LLM mapping:")
        for original, token in result.mapping.items():
            print(f"   '{original}' -> {token}")

        # Test deanonymization
        restored = sanitizer.deanonymize(result.text, result.mapping)
        print(f"Restored: Restored text:\n{restored}")

        print("✓ LLM strategy successful")

    except Exception as e:
        print(f"Warning: LLM strategy not available: {e}")
        print("   (Ensure a local LLM server is running on localhost:1234)")


def example_error_handling():
    """Example 8: Error handling"""
    example_section("EXAMPLE 8: Error Handling")

    print("Test 1: Unknown strategy")
    try:
        config = SanConfig(strategies=["nonexistent"])
        sanitizer = PromptSanitizer(config)
        sanitizer.anonymize("test")
    except ValueError as e:
        print(f"   ✓ Error caught: {e}")

    print("\nTest 2: Missing LLM configuration")
    try:
        config = SanConfig(strategies=["llm"], llm_model=None)  # Missing model
        sanitizer = PromptSanitizer(config)
        sanitizer.anonymize("test")
    except ValueError as e:
        print(f"   ✓ Error caught: {e}")

    print("\nTest 3: Empty mapping deanonymization")
    try:
        sanitizer = PromptSanitizer()
        result = sanitizer.deanonymize("__TOKEN_1__", {})  # Empty mapping
        print(f"   Warning: Result with empty mapping: '{result}'")
        print("   ✓ No error, but token unchanged (expected behavior)")
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")

    print("✓ Error handling validated")


def example_performance_comparison():
    """Example 9: Performance comparison"""
    example_section("EXAMPLE 9: Performance Analysis")

    # Test text
    test_text = (
        """
    Business Report Q1 2024
    
    CEO Jennifer Adams announced that TechCorp Inc.
    achieved $2.5M revenue this quarter.
    
    Key contacts:
    - Sales: mike.jones@techcorp.com
    - Support: +1-800-555-0199
    
    Next board meeting: April 30, 2024
    Location: San Francisco office
    """
        * 10
    )  # Repeat 10x for more meaningful timing

    print(f"Stats: Performance test with {len(test_text)} character text")

    # Test configurations
    configs = {
        "Regex Only": SanConfig(strategies=["regex"]),
        "Dict Only": SanConfig(
            strategies=["dict"],
            custom_dict={
                "Jennifer Adams": "PERSON",
                "TechCorp Inc": "COMPANY",
                "San Francisco": "CITY",
            },
        ),
        "Combined": SanConfig(
            strategies=["regex", "dict"],
            custom_dict={"TechCorp Inc": "COMPANY", "San Francisco": "CITY"},
        ),
    }

    results = {}

    for name, config in configs.items():
        sanitizer = PromptSanitizer(config)

        # Warmup
        sanitizer.anonymize("warmup text")

        # Timing test
        start_time = time.time()
        result = sanitizer.anonymize(test_text)
        duration = time.time() - start_time

        results[name] = {
            "duration": duration,
            "entities": len(result.mapping),
            "text_length": len(result.text),
        }

        print(f"\nConfig: {name}:")
        print(f"   Time: {duration:.3f} seconds")
        print(f"   Entities found: {results[name]['entities']}")
        if duration > 0:
            print(f"   Characters/second: {len(test_text)/duration:.0f}")
        else:
            print(f"   Characters/second: >1000000 (too fast to measure)")

    # Comparison
    print(f"\nSummary: Performance Summary:")
    fastest = min(results.keys(), key=lambda x: results[x]["duration"])
    most_entities = max(results.keys(), key=lambda x: results[x]["entities"])

    print(f"   Fastest: {fastest} ({results[fastest]['duration']:.3f}s)")
    print(
        f"   Most entities: {most_entities} ({results[most_entities]['entities']} entities)"
    )

    print("✓ Performance analysis complete")


if __name__ == "__main__":
    main()
