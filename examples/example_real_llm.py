#!/usr/bin/env python3
"""
PromptSan Real LLM Example

Demonstrates a complete workflow:
1. Anonymize sensitive data
2. Send to real LLM (OpenRouter)
3. Stream the response back
4. Deanonymize the streamed response in real-time

Usage:
    export OPENAI_API_KEY="sk-or-v1-your-openrouter-key"
    python examples/example_real_llm.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from promptsan import PromptSanitizer, SanConfig
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import time
from typing import Generator

# Configuration constants
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
MODEL = os.getenv('OPENROUTER_MODEL', "mistralai/devstral-small")

def main():
    print("PromptSan - Real LLM Integration Example (OpenRouter)")
    print("=" * 50)
    
    # Check for API key
    if not API_KEY:
        print("Please set your OpenRouter API key in the OPENAI_API_KEY environment variable.")
        return

    print("✓ OpenRouter API key found")
    
    # Step 1: Prepare sensitive data
    print("\n" + "="*50)
    print("STEP 1: Anonymize Sensitive Data")
    print("="*50)
    
    sensitive_text = """
    Patient Case Summary:
    
    Name: Sarah Johnson
    Email: sarah.johnson@hospital.com
    Phone: +1-555-123-4567
    DOB: 03/15/1985
    SSN: 123-45-6789
    
    Medical History:
    Patient presented with acute symptoms on 12/20/2023.
    Previous treatment at General Hospital was effective.
    Current prescription: Metformin 500mg daily.
    
    Next appointment: 01/15/2024
    """
    
    print("Original sensitive text:")
    print(sensitive_text)
    
    # Configure anonymization with custom dictionary + enhanced regex
    config = SanConfig(
        strategies=["dict", "regex"],
        custom_dict={
            "Sarah Johnson": "PERSON",
            "General Hospital": "HOSPITAL"
        },
        regex_patterns={
            r"\+?1?[-\s]?\(?[0-9]{3}\)?[-\s]?[0-9]{3}[-\s]?[0-9]{4}": "PHONE",
            r"\b\d{2}/\d{2}/\d{4}\b": "DATE",
            r"\b\d{4}-\d{2}-\d{2}\b": "DATE", 
            r"\b\d{2}-\d{2}-\d{4}\b": "DATE",
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b": "EMAIL",
            r"\b\d{3}-\d{2}-\d{4}\b": "SSN"
        }
    )
    
    sanitizer = PromptSanitizer(config)
    result = sanitizer.anonymize(sensitive_text)
    
    print("\nAnonymized text:")
    print(result.text)
    print(f"\nFound {len(result.mapping)} sensitive entities:")
    for original, token in result.mapping.items():
        print(f"  '{original}' → {token}")
    
    # Step 2: Send to real LLM
    print("\n" + "="*50)
    print("STEP 2: Send to OpenRouter LLM")
    print("="*50)
    
    print(f"Using OpenRouter with model: {MODEL}")
    
    # Create LLM client
    llm = ChatOpenAI(
        model_name=MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=API_KEY,
        streaming=True,
        temperature=0.7
    )
    
    # Create prompt
    prompt_template = ChatPromptTemplate.from_template(
        """You are a medical AI assistant. Please analyze this patient case and provide:
        1. A brief summary 
        2. Recommendations for next steps
        3. Any red flags or concerns
        
        IMPORTANT: The patient data below has been anonymized for privacy protection. 
        Sensitive information appears as tokens like __PERSON_1__, __DATE_1__, __EMAIL_1__, etc.
        When you encounter these tokens in your analysis, please keep them EXACTLY as they are 
        (preserve the __LABEL__ format). Do not try to guess or replace the actual values.
        
        Patient Case:
        {case_text}
        
        Please provide a clear, professional medical analysis while preserving all anonymized tokens."""
    )
    
    print("Sending anonymized text to LLM...")
    
    try:
        # Step 3: Stream response and deanonymize
        print("\n" + "="*50)
        print("STEP 3: Stream Response + Real-time Deanonymization")
        print("="*50)
        
        # Get streaming response
        chain = prompt_template | llm
        
        print("LLM is responding with real-time deanonymization...")
        print("\n" + "-"*40)
        print("LIVE DEANONYMIZED STREAM (as LLM generates):")
        print("-"*40)
        
        # Create a REAL stream generator directly from LLM
        def real_llm_stream() -> Generator[str, None, None]:
            """Generator that yields chunks directly from LLM streaming"""
            for chunk in chain.stream({"case_text": result.text}):
                chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if chunk_content:  # Only yield non-empty chunks
                    yield chunk_content
        
        # Deanonymize the REAL stream AS IT COMES
        real_stream = real_llm_stream()
        deanonymized_stream = sanitizer.deanonymize_stream(real_stream, result.mapping)
        
        deanonymized_response = ""
        
        # Process the real streaming response
        for chunk in deanonymized_stream:
            print(chunk, end='', flush=True)
            deanonymized_response += chunk
        
        print(f"\n\nTotal deanonymized response length: {len(deanonymized_response)} characters")
        
        # Step 5: Summary
        print("\n\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        
        print(f"✓ Anonymized {len(result.mapping)} sensitive entities")
        print(f"✓ Processed {len(deanonymized_response)} characters through OpenRouter LLM")
        print(f"✓ REAL-TIME streaming deanonymization (not simulated!)")
        print(f"✓ Original entities restored LIVE as LLM generates response")
        
        # Show a few examples of what was restored
        print("\nRestored entities:")
        restored_count = 0
        for original, token in result.mapping.items():
            if original in deanonymized_response:
                print(f"  {token} → '{original}' (restored in real-time)")
                restored_count += 1
        
        if restored_count == 0:
            print("  (No tokens were present in LLM response to restore)")
            print("  LLM may have used different phrasing or avoided the anonymized tokens")
        
        print("\nComplete workflow successful!")
        print("   Sensitive data was protected during LLM processing")
        print("   and restored in the final response.")
        
    except Exception as e:
        print(f"\n Error calling OpenRouter LLM: {e}")
        print("\nTroubleshooting:")
        print("1. Check your OpenRouter API key is valid")
        print("2. Check your internet connection")
        print("3. Ensure you have credits in your OpenRouter account")
        print("4. Visit https://openrouter.ai/ to check your account status")

if __name__ == "__main__":
    main()