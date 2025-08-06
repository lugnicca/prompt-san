#!/usr/bin/env python3
"""
PromptSan Configuration Examples

Demonstrates various configuration approaches:
- JSON configuration files
- Environment-based configuration
- Dynamic configuration changes
- Configuration validation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from promptsan import PromptSanitizer, SanConfig
import json
import os
import tempfile


def main():
    print("PromptSan - Configuration Examples")
    print("=" * 50)
    
    # Example 1: JSON Configuration
    print("\nExample 1: JSON Configuration Files")
    print("-" * 50)
    
    # Create sample configurations
    configs = {
        "basic_regex": {
            "strategies": ["regex"],
            "regex_patterns": {
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "EMAIL",
                r"\b\d{3}-\d{2}-\d{4}\b": "SSN",
                r"\b\d{3}-\d{3}-\d{4}\b": "PHONE"
            }
        },
        
        "enterprise_dict": {
            "strategies": ["dict", "regex"],
            "custom_dict": {
                "CONFIDENTIAL": "CLASSIFICATION",
                "INTERNAL": "CLASSIFICATION", 
                "Project Zeus": "PROJECT",
                "Alpha Corp": "COMPANY",
                "Beta Division": "DIVISION"
            },
            "regex_patterns": {
                r"\b[A-Z]{2,}\d{6,8}\b": "REFERENCE",
                r"\bEMP-\d{6}\b": "EMPLOYEE_ID"
            }
        },
        
        "medical_config": {
            "strategies": ["regex"],
            "regex_patterns": {
                r"\bMRN:\s*\d{6,10}\b": "MRN",
                r"\bDOB:\s*\d{2}/\d{2}/\d{4}\b": "DOB",
                r"\b(?:Dr\.|Doctor)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b": "DOCTOR",
                r"\b\d{3}-\d{2}-\d{4}\b": "SSN",
                r"\b[A-Z][a-z]+\s+Hospital\b": "HOSPITAL"
            }
        }
    }
    
    # Test each configuration
    for config_name, config_data in configs.items():
        print(f"\nConfig: Testing {config_name} configuration:")
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            config_file = f.name
        
        try:
            # Load configuration from file
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
            
            config = SanConfig(**loaded_config)
            sanitizer = PromptSanitizer(config)
            
            # Test with appropriate sample text
            test_texts = {
                "basic_regex": "Contact jane.doe@company.com or call 555-123-4567. SSN: 123-45-6789",
                "enterprise_dict": "CONFIDENTIAL: Project Zeus led by Alpha Corp's Beta Division. REF: ABC123456, EMP-789012",
                "medical_config": "Patient MRN: 1234567890, DOB: 03/15/1985. Treating physician: Dr. Sarah Johnson at City Hospital"
            }
            
            test_text = test_texts[config_name]
            print(f"  Input: {test_text}")
            
            result = sanitizer.anonymize(test_text)
            print(f"  Output: {result.text}")
            print(f"  Entities: {len(result.mapping)} found")
            
        finally:
            os.unlink(config_file)
    
    print("✓ JSON configuration examples complete!")
    
    
    # Example 2: Environment-based Configuration
    print("\nExample 2: Environment-based Configuration")
    print("-" * 50)
    
    def load_config_from_env():
        """Load configuration from environment variables"""
        config_data = {
            "strategies": os.getenv("PROMPTSAN_STRATEGIES", "regex").split(","),
            "llm_model": os.getenv("PROMPTSAN_LLM_MODEL"),
            "llm_base_url": os.getenv("PROMPTSAN_LLM_URL", "http://localhost:1234/v1"),
        }
        
        # Load custom dictionary from env
        custom_dict_str = os.getenv("PROMPTSAN_CUSTOM_DICT", "{}")
        try:
            config_data["custom_dict"] = json.loads(custom_dict_str)
        except json.JSONDecodeError:
            config_data["custom_dict"] = {}
        
        # Filter out None values
        return {k: v for k, v in config_data.items() if v is not None}
    
    # Set some example environment variables
    os.environ["PROMPTSAN_STRATEGIES"] = "regex,dict"
    os.environ["PROMPTSAN_CUSTOM_DICT"] = '{"Secret Project": "PROJECT", "Company A": "COMPANY"}'
    
    print("Environment variables set:")
    print(f"  PROMPTSAN_STRATEGIES={os.environ['PROMPTSAN_STRATEGIES']}")
    print(f"  PROMPTSAN_CUSTOM_DICT={os.environ['PROMPTSAN_CUSTOM_DICT']}")
    
    env_config_data = load_config_from_env()
    print(f"Loaded config: {env_config_data}")
    
    env_config = SanConfig(**env_config_data)
    env_sanitizer = PromptSanitizer(env_config)
    
    env_text = "Working on Secret Project for Company A. Email: test@example.com"
    env_result = env_sanitizer.anonymize(env_text)
    
    print(f"Input: {env_text}")
    print(f"Output: {env_result.text}")
    print("✓ Environment-based configuration working!")
    
    # Clean up environment
    del os.environ["PROMPTSAN_STRATEGIES"]
    del os.environ["PROMPTSAN_CUSTOM_DICT"]
    
    
    # Example 3: Dynamic Configuration Changes
    print("\nExample 3: Dynamic Configuration Changes")
    print("-" * 50)
    
    # Start with basic configuration
    base_config = SanConfig(strategies=["regex"])
    sanitizer = PromptSanitizer(base_config)
    
    sample_text = "Dr. John Smith at Johns Hopkins (j.smith@jh.edu) treats patient #12345"
    
    print(f"Sample text: {sample_text}")
    print("\nTesting different configurations:")
    
    configurations = [
        {
            "name": "Basic Regex",
            "config": SanConfig(strategies=["regex"])
        },
        {
            "name": "Extended Regex", 
            "config": SanConfig(
                strategies=["regex"],
                regex_patterns={
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "EMAIL",
                    r"\b(?:Dr\.|Doctor)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b": "DOCTOR",
                    r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b": "INSTITUTION",
                    r"\#\d+\b": "PATIENT_ID"
                }
            )
        },
        {
            "name": "Medical Dictionary",
            "config": SanConfig(
                strategies=["dict"],
                custom_dict={
                    "Dr. John Smith": "DOCTOR",
                    "Johns Hopkins": "HOSPITAL", 
                    "patient #12345": "PATIENT_REF"
                }
            )
        },
        {
            "name": "Combined Strategies",
            "config": SanConfig(
                strategies=["dict", "regex"],
                custom_dict={
                    "Johns Hopkins": "HOSPITAL"
                },
                regex_patterns={
                    r"\b(?:Dr\.|Doctor)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b": "DOCTOR",
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "EMAIL",
                    r"\#\d+\b": "PATIENT_ID"
                }
            )
        }
    ]
    
    for config_test in configurations:
        print(f"\nConfig: {config_test['name']}:")
        sanitizer = PromptSanitizer(config_test['config'])
        result = sanitizer.anonymize(sample_text)
        print(f"  Result: {result.text}")
        print(f"  Entities: {list(result.mapping.keys())}")
    
    print("✓ Dynamic configuration testing complete!")
    
    
    # Example 4: Configuration Validation
    print("\nExample 4: Configuration Validation")
    print("-" * 50)
    
    print("Testing configuration validation:")
    
    # Valid configurations
    valid_configs = [
        {"strategies": ["regex"]},
        {"strategies": ["dict"], "custom_dict": {"test": "LABEL"}},
        {"strategies": ["regex", "dict"], "regex_patterns": {r"\d+": "NUMBER"}},
    ]
    
    for i, config_data in enumerate(valid_configs, 1):
        try:
            config = SanConfig(**config_data)
            config.validate()
            print(f"  ✓ Valid config {i}: {config.strategies}")
        except Exception as e:
            print(f"  ✗ Config {i} failed: {e}")
    
    # Invalid configurations
    invalid_configs = [
        {"strategies": "not_a_list"},  # Wrong type
        {"custom_dict": "not_a_dict"},  # Wrong type
        {"regex_patterns": ["not_a_dict"]},  # Wrong type
    ]
    
    print("\nTesting invalid configurations:")
    for i, config_data in enumerate(invalid_configs, 1):
        try:
            config = SanConfig(**config_data)
            config.validate()
            print(f"  ✗ Invalid config {i} passed (shouldn't happen)")
        except Exception as e:
            print(f"  ✓ Invalid config {i} caught: {type(e).__name__}")
    
    print("✓ Configuration validation working correctly!")
    
    
    # Example 5: Configuration Templates
    print("\nExample 5: Configuration Templates")
    print("-" * 50)
    
    def create_config_template(domain: str) -> dict:
        """Create configuration templates for different domains"""
        templates = {
            "healthcare": {
                "strategies": ["regex"],
                "regex_patterns": {
                    r"\bMRN:\s*\d{6,10}\b": "MRN",
                    r"\bDOB:\s*\d{2}/\d{2}/\d{4}\b": "DOB",
                    r"\b(?:Dr\.|Doctor)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b": "DOCTOR",
                    r"\b\d{3}-\d{2}-\d{4}\b": "SSN",
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "EMAIL"
                }
            },
            
            "financial": {
                "strategies": ["regex"],
                "regex_patterns": {
                    r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2})\s?(?:\d{4}\s?){2}\d{4}\b": "CREDIT_CARD",
                    r"\b\d{9}\b": "ROUTING_NUMBER",
                    r"\b\d{10,12}\b": "ACCOUNT_NUMBER",
                    r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b": "AMOUNT",
                    r"\b\d{3}-\d{2}-\d{4}\b": "SSN"
                }
            },
            
            "corporate": {
                "strategies": ["dict", "regex"],
                "custom_dict": {
                    "CONFIDENTIAL": "CLASSIFICATION",
                    "PROPRIETARY": "CLASSIFICATION",
                    "INTERNAL": "CLASSIFICATION"
                },
                "regex_patterns": {
                    r"\b[A-Z]{2,}\d{6,8}\b": "REFERENCE",
                    r"\bEMP-\d{6}\b": "EMPLOYEE_ID",
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "EMAIL"
                }
            }
        }
        
        return templates.get(domain, {})
    
    # Test templates
    test_data = {
        "healthcare": "Patient MRN: 1234567, DOB: 03/15/1985. Dr. Smith (dr.smith@hospital.com) SSN: 123-45-6789",
        "financial": "Credit card 4532123456789012, routing 123456789, account 9876543210. Amount: $1,234.56",
        "corporate": "CONFIDENTIAL document EMP-123456, contact admin@company.com, reference ABC789012"
    }
    
    for domain in ["healthcare", "financial", "corporate"]:
        print(f"\n🏥 {domain.title()} Template:")
        template = create_config_template(domain)
        
        if template:
            config = SanConfig(**template)
            sanitizer = PromptSanitizer(config)
            
            sample = test_data[domain]
            result = sanitizer.anonymize(sample)
            
            print(f"  Input: {sample}")
            print(f"  Output: {result.text}")
            print(f"  Entities: {len(result.mapping)} found")
        else:
            print(f"  No template available for {domain}")
    
    print("✓ Configuration templates working!")


def example_real_config_files():
    """Example 6: Using the actual provided config files"""
    print("\nExample 6: Using Provided Configuration Files")
    print("-" * 50)
    
    # Get examples directory
    examples_dir = os.path.dirname(__file__)
    
    config_files = {
        "Basic": "config_basic.json",
        "Enterprise": "config_enterprise.json",
        "Medical": "config_medical.json"
    }
    
    test_texts = {
        "Basic": "Contact admin@company.com, ZIP: 90210, Date: 03/15/2024",
        "Enterprise": "CONFIDENTIAL project by Acme Corporation, EMP-123456",
        "Medical": "Patient MRN: 123456, Dr. Johnson at General Hospital"
    }
    
    for config_name, filename in config_files.items():
        config_path = os.path.join(examples_dir, filename)
        
        if os.path.exists(config_path):
            print(f"\n{config_name} Configuration ({filename}):")
            
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            config = SanConfig(**config_data)
            sanitizer = PromptSanitizer(config)
            
            test_text = test_texts[config_name]
            result = sanitizer.anonymize(test_text)
            
            print(f"  Input: {test_text}")
            print(f"  Output: {result.text}")
            print(f"  Entities: {len(result.mapping)} found")
        else:
            print(f"  {filename} not found")
    
    print("\n✓ Real configuration files tested!")


if __name__ == "__main__":
    main()
    example_real_config_files()