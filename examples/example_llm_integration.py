#!/usr/bin/env python3
"""
PromptSan LLM Integration Examples

Demonstrates LLM-based anonymization:
- Local LLM setup and configuration
- Custom prompt templates
- Error handling and retry mechanisms
- Performance comparison with regex strategies
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time

from promptsan import PromptSanitizer, SanConfig


def main():
    print("PromptSan - LLM Integration Examples")
    print("=" * 50)

    # Example 1: Basic LLM Setup
    print("\nExample 1: Basic LLM Configuration")
    print("-" * 50)

    # Create a simple prompt template
    basic_prompt = """<task>
Anonymize sensitive entities in the following text by replacing them with tokens in the format __LABEL_N__.
Do not modify strings already in the form __SOMETHING_N__.
</task>

<rules>
- People: __PERSON_N__
- Places: __LOCATION_N__  
- Organizations: __ORG_N__
- Dates: __DATE_N__
- Emails: __EMAIL_N__
- Phones: __PHONE_N__
- Addresses: __ADDRESS_N__
</rules>

Respond STRICTLY in this XML format:
<response>
  <anonymized>full anonymized text here</anonymized>
  <mapping>
    <entity original="original text" token="__LABEL_N__" label="LABEL" />
    <!-- more entities -->
  </mapping>
</response>

Text to anonymize:
{text}"""

    config = SanConfig(
        strategies=["llm"],
        llm_model="dolphin3.0-llama3.1-8b",
        llm_base_url="http://localhost:1234/v1",
        llm_prompt_template=basic_prompt,
    )

    text = """
    John Smith works at Microsoft in Seattle.
    Contact: john.smith@microsoft.com
    Phone: +1-206-123-4567
    Meeting on March 15, 2024.
    """

    print(f"Original text:\n{text}")
    print(f"LLM Configuration:")
    print(f"  Model: {config.llm_model}")
    print(f"  Base URL: {config.llm_base_url}")
    print(f"  Using basic prompt template")

    try:
        sanitizer = PromptSanitizer(config)
        start_time = time.time()
        result = sanitizer.anonymize(text)
        duration = time.time() - start_time

        print(f"LLM anonymized text:\n{result.text}")
        print(f"LLM mapping:")
        for original, token in result.mapping.items():
            print(f"  '{original}' -> {token}")

        print(f"Processing time: {duration:.2f} seconds")

        # Test deanonymization
        restored = sanitizer.deanonymize(result.text, result.mapping)
        print(f"Restored text:\n{restored}")

        print("✓ Basic LLM integration working!")

    except Exception as e:
        print(f"Warning: LLM not available: {e}")
        print("Make sure a local LLM server is running on localhost:1234")
        return

    # Example 2: Advanced Prompt Template
    print("\nExample 2: Advanced Prompt Template")
    print("-" * 50)

    advanced_prompt = """<task>
You are a privacy-focused text anonymization system. Your job is to identify and anonymize ALL sensitive information in the given text.

CRITICAL REQUIREMENTS:
1. Be COMPREHENSIVE - don't miss any sensitive data
2. Be PRECISE - only anonymize what needs anonymizing
3. Maintain text readability and structure
4. Use consistent token formatting: __LABEL_N__
</task>

<entity_categories>
- PERSON: Full names, first names, last names
- ORGANIZATION: Companies, institutions, agencies
- LOCATION: Cities, states, countries, addresses
- CONTACT: Emails, phone numbers, websites
- TEMPORAL: Dates, times, years, months
- IDENTIFIER: Account numbers, IDs, codes
- FINANCIAL: Credit cards, bank accounts, amounts
- MEDICAL: Conditions, treatments, medications
- TECHNICAL: IP addresses, domains, systems
</entity_categories>

<examples>
Input: "Dr. Sarah Chen at Stanford Hospital called about patient ID 12345"
Output: "__PERSON_1__ at __ORGANIZATION_2__ called about patient ID __IDENTIFIER_3__"
</examples>

<output_format>
<response>
  <anonymized>anonymized text with all sensitive entities replaced</anonymized>
  <mapping>
    <entity original="exact original text" token="__LABEL_N__" label="CATEGORY" />
  </mapping>
</response>
</output_format>

Text to process:
{text}"""

    config = SanConfig(
        strategies=["llm"],
        llm_model="dolphin3.0-llama3.1-8b",
        llm_base_url="http://localhost:1234/v1",
        llm_prompt_template=advanced_prompt,
    )

    complex_text = """
    Case Report #CR-2024-0157
    Patient: Maria Rodriguez (DOB: 07/22/1978)
    Provider: Dr. James Wilson, MD
    Hospital: Cedar Sinai Medical Center
    Date: March 20, 2024
    
    Contact Information:
    Email: m.rodriguez@email.com
    Phone: (555) 234-5678
    Insurance: Aetna Policy #POL789456123
    
    Clinical Notes:
    Patient presented with acute symptoms.
    Prescribed Metformin 500mg daily.
    Follow-up scheduled for April 15, 2024.
    """

    print(f"Complex medical text:\n{complex_text}")

    try:
        sanitizer = PromptSanitizer(config)
        start_time = time.time()
        result = sanitizer.anonymize(complex_text)
        duration = time.time() - start_time

        print(f"Advanced LLM anonymized text:\n{result.text}")
        print(f"Advanced LLM mapping ({len(result.mapping)} entities):")
        for original, token in result.mapping.items():
            print(f"  '{original}' -> {token}")

        print(f"Processing time: {duration:.2f} seconds")
        print("✓ Advanced LLM prompt working!")

    except Exception as e:
        print(f"Warning: Advanced LLM processing failed: {e}")

    # Example 3: Strategy Comparison
    print("\nExample 3: Strategy Comparison (Regex vs LLM)")
    print("-" * 50)

    comparison_text = """
    Business Report Q1 2024
    
    CEO Jennifer Adams announced that TechCorp Inc.
    achieved $2.5M revenue this quarter.
    
    Key contacts:
    - Sales: mike.jones@techcorp.com
    - Support: +1-800-555-0199
    
    Next board meeting: April 30, 2024
    Location: San Francisco office
    """

    print(f"Text for comparison:\n{comparison_text}")

    # Test Regex strategy
    print("\n🔍 Regex Strategy Results:")
    regex_config = SanConfig(strategies=["regex"])
    regex_sanitizer = PromptSanitizer(regex_config)

    start_time = time.time()
    regex_result = regex_sanitizer.anonymize(comparison_text)
    regex_duration = time.time() - start_time

    print(f"Regex anonymized: {regex_result.text[:100]}...")
    print(f"Regex entities found: {len(regex_result.mapping)}")
    print(f"Regex time: {regex_duration:.3f} seconds")

    # Test LLM strategy
    print("\nLLM: LLM Strategy Results:")
    try:
        llm_config = SanConfig(
            strategies=["llm"],
            llm_model="dolphin3.0-llama3.1-8b",
            llm_base_url="http://localhost:1234/v1",
            llm_prompt_template=basic_prompt,
        )
        llm_sanitizer = PromptSanitizer(llm_config)

        start_time = time.time()
        llm_result = llm_sanitizer.anonymize(comparison_text)
        llm_duration = time.time() - start_time

        print(f"LLM anonymized: {llm_result.text[:100]}...")
        print(f"LLM entities found: {len(llm_result.mapping)}")
        print(f"LLM time: {llm_duration:.3f} seconds")

        # Comparison
        print(f"\nStats: Comparison:")
        print(f"  Regex: {len(regex_result.mapping)} entities in {regex_duration:.3f}s")
        print(f"  LLM: {len(llm_result.mapping)} entities in {llm_duration:.3f}s")
        print(f"  Speed ratio: {llm_duration/regex_duration:.1f}x slower")

        # Show entity differences
        regex_entities = set(regex_result.mapping.keys())
        llm_entities = set(llm_result.mapping.keys())

        only_regex = regex_entities - llm_entities
        only_llm = llm_entities - regex_entities

        if only_regex:
            print(f"  Only found by regex: {list(only_regex)}")
        if only_llm:
            print(f"  Only found by LLM: {list(only_llm)}")

        print("✓ Strategy comparison complete!")

    except Exception as e:
        print(f"Warning: LLM comparison failed: {e}")

    # Example 4: Error Handling
    print("\nExample 4: LLM Error Handling")
    print("-" * 50)

    # Test with invalid configuration
    print("Testing error handling scenarios:")

    # Missing model
    try:
        bad_config = SanConfig(strategies=["llm"], llm_model=None)
        bad_sanitizer = PromptSanitizer(bad_config)
        bad_sanitizer.anonymize("test")
    except ValueError as e:
        print(f"✓ Caught missing model error: {e}")

    # Missing prompt template
    try:
        bad_config = SanConfig(
            strategies=["llm"], llm_model="test-model", llm_prompt_template=None
        )
        bad_sanitizer = PromptSanitizer(bad_config)
        bad_sanitizer.anonymize("test")
    except ValueError as e:
        print(f"✓ Caught missing prompt error: {e}")

    print("✓ Error handling working correctly!")


if __name__ == "__main__":
    main()
