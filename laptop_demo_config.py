#!/usr/bin/env python3
"""
Laptop-optimized configuration for Misty robot demo.
Balances performance with resource constraints.
"""

import json
import logging
from pathlib import Path

# Demo configuration optimized for laptop + Misty
LAPTOP_DEMO_CONFIG = {
    "performance_mode": "laptop_optimized",  # vs "desktop_power"

    # Model selection for laptop demo
    "models": {
        # Lightweight but capable LLM
        "lm_model": "HuggingFaceTB/SmolLM-360M-Instruct",  # Fast on 1050 Ti
        "lm_alternative": "microsoft/DialoGPT-medium",      # Conversation-optimized

        # STT options
        "stt_model": "openai/whisper-tiny.en",  # Fastest Whisper
        "stt_alternative": "faster-whisper",     # Hardware optimized

        # TTS options
        "tts_model": "parler-mini",              # Lightweight Parler
        "tts_alternative": "openai-api",         # Cloud fallback
    },

    # Pipeline settings for laptop
    "pipeline": {
        "device": "cuda",  # Use 1050 Ti
        "compile_modes": {
            "stt": None,      # Disable compilation to avoid issues
            "tts": None,      # Disable compilation to avoid issues
        },
        "batch_size": 1,      # Conservative memory usage
        "max_length": 512,    # Shorter responses for speed
    },

    # Network settings for demo
    "network": {
        "mode": "local",      # Run everything on laptop
        "fallback_mode": "socket",  # If needed for debugging
        "ports": {
            "audio_in": 12345,
            "audio_out": 12346,
            "misty_control": 8080
        }
    },

    # Demo-specific settings
    "demo": {
        "conversation_timeout": 30,    # 30 seconds max per turn
        "max_conversations": 20,       # Limit for demo
        "auto_hint_delay": 10,         # Proactive hints after 10s
        "expression_delay": 0.5,       # Faster expressions for demo
    },

    # Performance targets for laptop
    "performance_targets": {
        "total_latency_ms": 3000,      # More lenient for laptop
        "acceptable_latency_ms": 4000,  # Demo still usable
        "stt_target_ms": 500,          # STT target
        "llm_target_ms": 1500,         # LLM target for small model
        "tts_target_ms": 800,          # TTS target
        "robot_target_ms": 500,        # Robot action target
    }
}

# API fallback configuration
API_FALLBACK_CONFIG = {
    "openai": {
        "stt_model": "whisper-1",
        "llm_model": "gpt-4o-mini",    # Cost-effective
        "tts_model": "tts-1",
        "tts_voice": "nova",           # Clear, friendly voice
    },
    "deepgram": {
        "model": "nova-2",
        "language": "en-US",
        "smart_format": True,
    }
}

def create_laptop_demo_script():
    """Generate optimized demo script for laptop + Misty."""

    script_content = f'''#!/bin/bash
# Laptop Demo Script for Misty Robot
# Optimized for resource-constrained environments

echo "🤖 Setting up Misty Who-Dunnit Demo"
echo "======================================"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    DEVICE="cuda"
else
    echo "⚠️  No GPU detected, using CPU"
    DEVICE="cpu"
fi

# Check Python environment
if [[ "$VIRTUAL_ENV" == *".venv-312"* ]]; then
    echo "✅ Python 3.12 environment active"
else
    echo "🔄 Activating Python 3.12 environment"
    source .venv-312/bin/activate
fi

# Demo configuration
echo "📋 Demo Configuration:"
echo "   Device: $DEVICE"
echo "   Model: {LAPTOP_DEMO_CONFIG['models']['lm_model']}"
echo "   Mode: {LAPTOP_DEMO_CONFIG['network']['mode']}"
echo "   Target Latency: {LAPTOP_DEMO_CONFIG['performance_targets']['total_latency_ms']}ms"

# Run optimized pipeline
echo "🚀 Starting optimized pipeline..."
python s2s_pipeline.py \\
    --mode {LAPTOP_DEMO_CONFIG['network']['mode']} \\
    --device $DEVICE \\
    --stt faster-whisper \\
    --llm transformers \\
    --tts parler \\
    --lm_model_name {LAPTOP_DEMO_CONFIG['models']['lm_model']} \\
    --lm_gen_max_new_tokens {LAPTOP_DEMO_CONFIG['pipeline']['max_length']} \\
    --log_level info \\
    --recv_host 0.0.0.0 \\
    --send_host 0.0.0.0

echo "✅ Demo pipeline ready!"
echo "🔗 Connect Misty with: python misty_integration.py <MISTY_IP> <LAPTOP_IP>"
'''

    with open("laptop_demo.sh", "w") as f:
        f.write(script_content)

    # Make executable
    import os
    os.chmod("laptop_demo.sh", 0o755)

    print("📝 Created laptop_demo.sh script")

def create_api_fallback_script():
    """Generate API-based fallback for unreliable local performance."""

    script_content = '''#!/usr/bin/env python3
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
'''

    with open("api_demo.py", "w") as f:
        f.write(script_content)

    print("📝 Created api_demo.py fallback script")

def save_laptop_config():
    """Save laptop configuration to file."""
    config_file = Path("laptop_demo_config.json")

    with open(config_file, "w") as f:
        json.dump({
            "laptop_config": LAPTOP_DEMO_CONFIG,
            "api_fallback": API_FALLBACK_CONFIG
        }, f, indent=2)

    print(f"📋 Saved configuration to {config_file}")

if __name__ == "__main__":
    print("🔧 Creating laptop demo setup...")

    create_laptop_demo_script()
    create_api_fallback_script()
    save_laptop_config()

    print("\\n✅ Laptop demo setup complete!")
    print("\\nUsage options:")
    print("1. Local pipeline: ./laptop_demo.sh")
    print("2. API fallback: python api_demo.py <MISTY_IP>")
    print("3. Hybrid: Use local STT/TTS + cloud LLM")