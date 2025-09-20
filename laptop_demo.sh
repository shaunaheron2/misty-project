#!/bin/bash
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
echo "   Model: HuggingFaceTB/SmolLM-360M-Instruct"
echo "   Mode: local"
echo "   Target Latency: 3000ms"

# Run optimized pipeline
echo "🚀 Starting optimized pipeline..."
python s2s_pipeline.py \
    --mode local \
    --device $DEVICE \
    --stt faster-whisper \
    --llm transformers \
    --tts parler \
    --lm_model_name HuggingFaceTB/SmolLM-360M-Instruct \
    --lm_gen_max_new_tokens 512 \
    --log_level info \
    --recv_host 0.0.0.0 \
    --send_host 0.0.0.0

echo "✅ Demo pipeline ready!"
echo "🔗 Connect Misty with: python misty_integration.py <MISTY_IP> <LAPTOP_IP>"
