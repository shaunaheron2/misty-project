#!/usr/bin/env python3
"""
Test script to validate JSON parsing functionality for robot responses.
This tests our modifications without requiring the full pipeline dependencies.
"""

import json
import sys
from pathlib import Path

def parse_json_response(text):
    """
    Parse JSON response from the model and extract message and expression.
    Returns (message_text, expression) or (original_text, None) if not JSON.
    """
    try:
        # Try to find JSON in the response
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            parsed = json.loads(text)
            if 'msg' in parsed:
                expression = parsed.get('expression', None)
                print(f"Parsed JSON response - Expression: {expression}")
                return parsed['msg'], expression
        return text, None
    except json.JSONDecodeError:
        print("Response is not valid JSON, using as plain text")
        return text, None

def load_who_dunnit_prompt():
    """Load the who-dunnit instruction prompt from the markdown file."""
    try:
        current_dir = Path(__file__).resolve().parent
        prompt_file = current_dir / "who-dunnit-instruction.md"
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ Successfully loaded who-dunnit prompt ({len(content)} characters)")
        return content
    except FileNotFoundError:
        print("❌ who-dunnit-instruction.md not found")
        return None

def test_json_parsing():
    """Test JSON parsing with sample robot responses."""
    print("Testing JSON parsing functionality...")

    # Test cases
    test_cases = [
        '{"msg": "Hello! I\'m Misty, ready to help you solve this mystery. What\'s your name?", "expression": "hi"}',
        '{"msg": "I detected some hesitation in your voice. Would you like a hint?", "expression": "hint"}',
        'This is plain text, not JSON',
        '{"msg": "Great job! You found the right suspect.", "expression": "excited"}',
        '{"invalid": "json without msg field"}',
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case[:50]}...")
        message, expression = parse_json_response(test_case)
        print(f"  Message: {message}")
        print(f"  Expression: {expression}")

def main():
    print("🤖 Testing Who-Dunnit Robot Integration")
    print("=" * 50)

    # Test prompt loading
    print("\n1. Testing prompt loading:")
    prompt = load_who_dunnit_prompt()
    if prompt:
        # Show first few lines of the prompt
        lines = prompt.split('\n')[:10]
        print("First 10 lines of prompt:")
        for line in lines:
            print(f"  {line}")

    # Test JSON parsing
    print("\n2. Testing JSON parsing:")
    test_json_parsing()

    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()