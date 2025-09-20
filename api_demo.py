#!/usr/bin/env python3
"""
API-based fallback for Misty demo.
Uses cloud services for reliable performance.
"""

import os
from llm_based_human_robot_dialogue import MistyRobot

def setup_api_demo():
    """Setup demo using API services."""

    # Check environment variables
    required_keys = ['DEEPGRAM_API_KEY', 'GPT_API_KEY', 'OPENAI_API_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]

    if missing_keys:
        print(f"❌ Missing API keys: {missing_keys}")
        print("Set them in your environment or .env file")
        return False

    print("✅ API keys configured")
    print("🚀 Using cloud-based pipeline for reliable demo performance")
    return True

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python api_demo.py <MISTY_IP>")
        sys.exit(1)

    misty_ip = sys.argv[1]

    if setup_api_demo():
        print(f"🤖 Starting API-based demo with Misty at {misty_ip}")
        robot = MistyRobot(misty_ip, 'who-dunnit-instruction.md')
    else:
        print("❌ Demo setup failed")
