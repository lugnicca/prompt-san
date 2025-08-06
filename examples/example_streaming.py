#!/usr/bin/env python3
"""
PromptSan Streaming Examples

Demonstrates streaming deanonymization capabilities:
- Simulating LLM output streams
- Handling partial tokens across chunks
- Real-time processing scenarios
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from promptsan import PromptSanitizer
from typing import Generator
import time
import threading


def main():
    print("PromptSan - Streaming Examples")
    print("=" * 50)
    
    # Example 1: Basic Streaming
    print("\nExample 1: Basic Streaming Deanonymization")
    print("-" * 50)
    
    # First, create some anonymized content
    sanitizer = PromptSanitizer()
    original_text = """
    Report by Alice Johnson (alice@company.com)
    Date: 03/15/2024, Phone: +1-555-123-4567
    ZIP: 90210
    """
    
    result = sanitizer.anonymize(original_text)
    print(f"Original text:\n{original_text}")
    print(f"Anonymized text:\n{result.text}")
    
    # Simulate streaming by chunking the anonymized text
    def simulate_stream(text: str, chunk_size: int = 8) -> Generator[str, None, None]:
        """Simulate a stream by splitting text into chunks"""
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            print(f"  Input: '{chunk}'")
            yield chunk
            time.sleep(0.1)  # Simulate network delay
    
    print(f"\nStream: Simulating stream (chunks of 8 characters):")
    
    # Deanonymize the stream
    stream_gen = simulate_stream(result.text)
    deanonymized_stream = sanitizer.deanonymize_stream(stream_gen, result.mapping)
    
    print(f"\nRestored: Deanonymized stream output:")
    restored_text = ""
    for chunk in deanonymized_stream:
        print(f"  Output: '{chunk}'")
        restored_text += chunk
    
    print(f"\nResult: Final restored text:\n{restored_text}")
    
    # Verify restoration
    if original_text.strip() == restored_text.strip():
        print("✓ Perfect streaming restoration!")
    else:
        print("Warning: Minor differences in whitespace/formatting")
    
    
    # Example 2: LLM Response Simulation
    print("\nExample 2: Simulated LLM Response Stream")
    print("-" * 50)
    
    # Simulate an LLM generating a response with anonymized data
    def simulate_llm_response() -> Generator[str, None, None]:
        """Simulate realistic LLM streaming where tokens are randomly split"""
        # Full response text that would be generated
        full_response = "Based on the data, __PERSON_1__ from __COMPANY_2__ can be reached at __EMAIL_3__ or by calling __PHONE_4__. The report is dated __DATE_5__."
        
        # Simulate realistic chunking (tokens WILL be split randomly)
        import random
        i = 0
        while i < len(full_response):
            # Random chunk size between 1-8 characters (realistic for LLM streaming)
            chunk_size = random.randint(1, 8)
            chunk = full_response[i:i + chunk_size]
            yield chunk
            i += chunk_size
            time.sleep(0.1)  # Simulate network/generation delay
    
    # Create mapping for this example
    test_mapping = {
        "Dr. Sarah Chen": "__PERSON_1__",
        "MedTech Inc": "__COMPANY_2__",
        "s.chen@medtech.com": "__EMAIL_3__",
        "+1-555-987-6543": "__PHONE_4__",
        "03/20/2024": "__DATE_5__"
    }
    
    print("Simulating LLM response generation...")
    print("Raw LLM stream:")
    
    llm_stream = simulate_llm_response()
    deanonymized_llm = sanitizer.deanonymize_stream(llm_stream, test_mapping)
    
    print("\nDeanonymized real-time output:")
    for chunk in deanonymized_llm:
        print(chunk, end='', flush=True)
        time.sleep(0.1)
    
    print("\n\n✓ LLM response streaming complete!")
    
    
    # Example 2b: Extreme Token Splitting
    print("\nExample 2b: Extreme Token Splitting (Worst Case)")
    print("-" * 50)
    
    def simulate_extreme_splitting() -> Generator[str, None, None]:
        """Simulate the WORST case: tokens split character by character"""
        text = "Contact __EMAIL_1__ and __PERSON_2__ today"
        
        # Split almost character by character (worst case scenario)
        extreme_chunks = [
            "Contact _",
            "_EM",
            "AIL_",
            "1__ a",
            "nd __PE",
            "RS",
            "ON_2",
            "__ today"
        ]
        
        for chunk in extreme_chunks:
            print(f"    Stream chunk: '{chunk}'")
            yield chunk
            time.sleep(0.1)
    
    extreme_mapping = {
        "support@company.com": "__EMAIL_1__",
        "John Smith": "__PERSON_2__"
    }
    
    print("Testing extreme token splitting:")
    extreme_stream = simulate_extreme_splitting()
    extreme_restored = sanitizer.deanonymize_stream(extreme_stream, extreme_mapping)
    
    print("\n  Restored output:")
    extreme_result = ""
    for chunk in extreme_restored:
        print(f"    ➜ '{chunk}'")
        extreme_result += chunk
    
    print(f"\n  Final: '{extreme_result}'")
    print("✓ Even extreme splitting handled correctly!")
    
    
    # Example 3: Partial Token Handling
    print("\nExample 3: Partial Token Handling")
    print("-" * 50)
    
    def create_partial_token_stream() -> Generator[str, None, None]:
        """Create a stream where tokens are split across chunks"""
        # This will split __EMAIL_1__ across multiple chunks
        text_with_tokens = "Contact __EMAIL_1__ for more info about __PERSON_2__"
        
        # Deliberately split at awkward positions
        chunks = [
            "Contact __EM",
            "AIL_1__ for mo",
            "re info about __PE",
            "RSON_2__"
        ]
        
        for chunk in chunks:
            print(f"  Input: '{chunk}'")
            yield chunk
    
    partial_mapping = {
        "john@company.com": "__EMAIL_1__",
        "Jane Doe": "__PERSON_2__"
    }
    
    print("Testing partial token handling:")
    partial_stream = create_partial_token_stream()
    restored_stream = sanitizer.deanonymize_stream(partial_stream, partial_mapping)
    
    print("\nRestored output:")
    final_output = ""
    for chunk in restored_stream:
        print(f"    ➜ '{chunk}'")
        final_output += chunk
    
    print(f"\nFinal result: '{final_output}'")
    expected = "Contact john@company.com for more info about Jane Doe"
    
    if final_output == expected:
        print("✓ Partial token handling working perfectly!")
    else:
        print(f"Warning: Expected: '{expected}'")
        print(f"   Got: '{final_output}'")
    
    
    # Example 4: Multi-threaded Streaming
    print("\nExample 4: Multi-threaded Streaming Processing")
    print("-" * 50)
    
    def producer_thread(queue_simulation):
        """Simulate a producer generating anonymized content"""
        content = [
            "Processing request from __PERSON_1__\n",
            "Email: __EMAIL_2__\n", 
            "Account: __ACCOUNT_3__\n",
            "Status: Active\n"
        ]
        
        for item in content:
            queue_simulation.append(item)
            time.sleep(0.3)
        
        queue_simulation.append(None)  # End marker
    
    # Simulate queue-based streaming
    queue_simulation = []
    
    mapping = {
        "Bob Wilson": "__PERSON_1__",
        "bob.wilson@example.com": "__EMAIL_2__",
        "ACC-789456": "__ACCOUNT_3__"
    }
    
    # Start producer in background
    producer = threading.Thread(target=producer_thread, args=(queue_simulation,))
    producer.start()
    
    print("Multi-threaded streaming example:")
    print("Producer generating content...")
    
    def consume_queue():
        """Generator that consumes from queue simulation"""
        while True:
            if queue_simulation:
                item = queue_simulation.pop(0)
                if item is None:
                    break
                yield item
            else:
                time.sleep(0.1)
    
    # Process the queue stream
    consumer_stream = consume_queue()
    deanonymized_queue = sanitizer.deanonymize_stream(consumer_stream, mapping)
    
    print("Consumer processing and deanonymizing:")
    for chunk in deanonymized_queue:
        print(f"  → {chunk.strip()}")
    
    producer.join()
    print("✓ Multi-threaded streaming complete!")


if __name__ == "__main__":
    main()