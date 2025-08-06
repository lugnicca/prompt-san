#!/usr/bin/env python3
"""
Advanced PromptSan Strategy Examples

Demonstrates advanced features:
- Dictionary strategy for domain-specific entities
- Combined strategies (regex + dict)
- Custom strategy development
- Strategy registration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from promptsan import PromptSanitizer, SanConfig
from promptsan.mapping import MappingStore
import re


def main():
    print("PromptSan - Advanced Strategy Examples")
    print("=" * 50)
    
    # Example 1: Dictionary Strategy
    print("\nExample 1: Dictionary Strategy")
    print("-" * 50)
    
    # Define sensitive business terms
    business_dict = {
        "Project Falcon": "PROJECT",
        "Acme Corporation": "COMPANY",
        "CONFIDENTIAL": "CLASSIFICATION", 
        "John Smith": "PERSON",
        "Q4 2024": "TIMEFRAME"
    }
    
    config = SanConfig(
        strategies=["dict"],
        custom_dict=business_dict
    )
    
    sanitizer = PromptSanitizer(config)
    
    text = """
    CONFIDENTIAL Report:
    John Smith from Acme Corporation
    is leading Project Falcon for Q4 2024.
    """
    
    print(f"Original text:\n{text}")
    print(f"Business dictionary:")
    for term, label in business_dict.items():
        print(f"  '{term}' -> {label}")
    
    result = sanitizer.anonymize(text)
    print(f"Anonymized text:\n{result.text}")
    
    print("Generated mapping:")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")
    
    print("✓ Dictionary strategy working!")
    
    
    # Example 2: Combined Strategies
    print("\nExample 2: Combined Strategies (Regex + Dict)")
    print("-" * 50)
    
    config = SanConfig(
        strategies=["regex", "dict"],  # Apply in sequence
        custom_dict={
            "OpenAI": "AI_COMPANY",
            "GPT-4": "AI_MODEL",
            "Claude": "AI_MODEL"
        }
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
    print(f"Anonymized text:\n{result.text}")
    
    print("Combined mapping (regex + dict):")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")
    
    print("✓ Combined strategies working!")
    
    
    # Example 3: Custom Strategy
    print("\nExample 3: Custom Strategy (Credit Cards)")
    print("-" * 50)
    
    def credit_card_strategy(text: str, mapping: MappingStore, cfg: SanConfig) -> str:
        """Custom strategy to anonymize credit card numbers"""
        # Simplified credit card pattern (Visa/MasterCard)
        cc_pattern = r'\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2})\s?(?:\d{4}\s?){2}\d{4}\b'
        
        for match in re.finditer(cc_pattern, text):
            cc_number = match.group().replace(' ', '')  # Remove spaces
            token = mapping.add(cc_number, "CREDIT_CARD")
            text = text.replace(match.group(), token)
        
        return text
    
    # Create sanitizer and register custom strategy
    sanitizer = PromptSanitizer()
    sanitizer.register_strategy("credit_card", credit_card_strategy)
    
    # Update config to use custom strategy
    config = SanConfig(strategies=["regex", "credit_card"])
    sanitizer = PromptSanitizer(config)
    sanitizer.register_strategy("credit_card", credit_card_strategy)
    
    text = """
    Payment Information:
    Credit Card: 4532 1234 5678 9012
    Email: billing@company.com
    Expiry: 12/25
    """
    
    print(f"Original text:\n{text}")
    
    result = sanitizer.anonymize(text)
    print(f"Anonymized text:\n{result.text}")
    
    print("Mapping with custom strategy:")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")
    
    print("✓ Custom strategy working!")
    
    
    # Example 4: Medical Data Strategy
    print("\nExample 4: Medical Data Strategy")
    print("-" * 50)
    
    def medical_strategy(text: str, mapping: MappingStore, cfg: SanConfig) -> str:
        """Custom strategy for medical data"""
        patterns = {
            r'\bMRN:\s*\d{6,8}\b': 'MRN',  # Medical Record Number
            r'\bDOB:\s*\d{2}/\d{2}/\d{4}\b': 'DOB',  # Date of Birth
            r'\b(?:Dr\.|Doctor)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b': 'DOCTOR',
            r'\b\d{3}-\d{2}-\d{4}\b': 'SSN',  # Social Security
        }
        
        for pattern, label in patterns.items():
            for match in re.finditer(pattern, text):
                entity = match.group()
                token = mapping.add(entity, label)
                text = text.replace(entity, token)
        
        return text
    
    # Setup medical anonymization
    sanitizer = PromptSanitizer()
    sanitizer.register_strategy("medical", medical_strategy)
    
    config = SanConfig(strategies=["medical"])
    sanitizer = PromptSanitizer(config)
    sanitizer.register_strategy("medical", medical_strategy)
    
    text = """
    Patient Chart:
    MRN: 1234567
    DOB: 03/15/1985
    Attending: Dr. Johnson
    SSN: 123-45-6789
    """
    
    print(f"Original text:\n{text}")
    
    result = sanitizer.anonymize(text)
    print(f"Anonymized text:\n{result.text}")
    
    print("Medical data mapping:")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")
    
    print("✓ Medical strategy working!")


if __name__ == "__main__":
    main()