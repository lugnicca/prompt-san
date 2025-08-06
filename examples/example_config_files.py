#!/usr/bin/env python3
"""
PromptSan Configuration Files Examples

Demonstrates how to use the provided JSON configuration files:
- config_basic.json
- config_enterprise.json
- config_medical.json
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from promptsan import PromptSanitizer, SanConfig
import json
import os


def main():
    print("PromptSan - Configuration Files Examples")
    print("=" * 50)
    
    # Get the examples directory path
    examples_dir = os.path.dirname(__file__)
    
    # Example 1: Basic Configuration
    print("\nExample 1: Basic Configuration (config_basic.json)")
    print("-" * 50)
    
    config_path = os.path.join(examples_dir, "config_basic.json")
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    print(f"Loaded config: {json.dumps(config_data, indent=2)}")
    
    config = SanConfig(**config_data)
    sanitizer = PromptSanitizer(config)
    
    text = "Contact John at john.doe@company.com or call +1-555-123-4567. ZIP: 90210, DOB: 03/15/1985"
    result = sanitizer.anonymize(text)
    
    print(f"Original: {text}")
    print(f"Anonymized: {result.text}")
    print(f"Found {len(result.mapping)} entities")
    print("✓ Basic configuration working!")
    
    
    # Example 2: Enterprise Configuration  
    print("\nExample 2: Enterprise Configuration (config_enterprise.json)")
    print("-" * 50)
    
    config_path = os.path.join(examples_dir, "config_enterprise.json")
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    print(f"Enterprise strategies: {config_data['strategies']}")
    print(f"Custom dictionary: {list(config_data['custom_dict'].keys())}")
    
    config = SanConfig(**config_data)
    sanitizer = PromptSanitizer(config)
    
    text = """
    CONFIDENTIAL Report - EMP-123456
    Project: TOP SECRET initiative by Acme Corporation
    Contact: admin@company.com, Phone: +1-555-987-6543
    Employee SSN: 123-45-6789, Reference: ABC789012
    """
    
    result = sanitizer.anonymize(text)
    
    print(f"Original: {text.strip()}")
    print(f"Anonymized: {result.text.strip()}")
    print(f"Enterprise entities found: {len(result.mapping)}")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")
    print("✓ Enterprise configuration working!")
    
    
    # Example 3: Medical Configuration
    print("\nExample 3: Medical Configuration (config_medical.json)")
    print("-" * 50)
    
    config_path = os.path.join(examples_dir, "config_medical.json")
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    print(f"Medical patterns: {len(config_data['regex_patterns'])} specialized patterns")
    
    config = SanConfig(**config_data)
    sanitizer = PromptSanitizer(config)
    
    text = """
    Patient Chart - City Hospital
    MRN: 1234567890, DOB: 03/15/1985
    Attending: Dr. Sarah Johnson
    Contact: patient.services@hospital.com
    SSN: 123-45-6789, Phone: +1-555-MEDIC
    Location: General Hospital Medical Center
    """
    
    result = sanitizer.anonymize(text)
    
    print(f"Original: {text.strip()}")
    print(f"Anonymized: {result.text.strip()}")
    print(f"Medical entities found: {len(result.mapping)}")
    for original, token in result.mapping.items():
        print(f"  '{original}' -> {token}")
    print("✓ Medical configuration working!")
    
    
    # Example 4: Comparing Configurations
    print("\nExample 4: Configuration Comparison")
    print("-" * 50)
    
    test_text = "Dr. Smith at smith@hospital.com, MRN: 123456, CONFIDENTIAL data"
    
    configs = {
        "Basic": "config_basic.json",
        "Enterprise": "config_enterprise.json", 
        "Medical": "config_medical.json"
    }
    
    results = {}
    
    for name, filename in configs.items():
        config_path = os.path.join(examples_dir, filename)
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        config = SanConfig(**config_data)
        sanitizer = PromptSanitizer(config)
        result = sanitizer.anonymize(test_text)
        
        results[name] = result
        print(f"{name:12}: {result.text}")
        print(f"{'':12}  Entities: {len(result.mapping)}")
    
    print("\nConfiguration comparison complete!")
    
    
    # Example 5: Custom Configuration Creation
    print("\nExample 5: Creating Custom Configuration Files")
    print("-" * 50)
    
    # Create a financial services configuration
    financial_config = {
        "strategies": ["regex", "dict"],
        "custom_dict": {
            "CONFIDENTIAL": "CLASSIFICATION",
            "PROPRIETARY": "CLASSIFICATION",
            "Goldman Sachs": "FINANCIAL_INSTITUTION",
            "JP Morgan": "FINANCIAL_INSTITUTION"
        },
        "regex_patterns": {
            r"\\b(?:4\\d{3}|5[1-5]\\d{2})\\s?(?:\\d{4}\\s?){2}\\d{4}\\b": "CREDIT_CARD",
            r"\\b\\d{9}\\b": "ROUTING_NUMBER", 
            r"\\$\\d{1,3}(?:,\\d{3})*(?:\\.\\d{2})?\\b": "AMOUNT",
            r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b": "EMAIL",
            r"\\bACC-\\d{6,10}\\b": "ACCOUNT_ID"
        }
    }
    
    # Save it
    config_path = os.path.join(examples_dir, "config_financial_example.json")
    with open(config_path, 'w') as f:
        json.dump(financial_config, f, indent=2)
    
    print(f"Created custom configuration: config_financial_example.json")
    
    # Test it
    config = SanConfig(**financial_config)
    sanitizer = PromptSanitizer(config)
    
    text = """
    CONFIDENTIAL Financial Report
    Goldman Sachs client ACC-789123456
    Credit Card: 4532 1234 5678 9012
    Amount: $1,234,567.89
    Contact: wealth@goldmansachs.com
    """
    
    result = sanitizer.anonymize(text)
    print(f"Financial text anonymized: {len(result.mapping)} entities found")
    print(f"Result: {result.text.strip()}")
    
    # Clean up
    os.remove(config_path)
    print("Cleaned up example file")
    print("✓ Custom configuration creation working!")


if __name__ == "__main__":
    main()