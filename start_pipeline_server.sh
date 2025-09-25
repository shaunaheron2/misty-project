#!/bin/bash
# Pipeline Server Launcher for Misty Who-Dunnit Demo
# Simple script to start the speech-to-speech pipeline server

echo "🤖 Starting Misty Who-Dunnit Pipeline Server"
echo "============================================="

# Check if we're in the right directory
if [ ! -f "s2s_pipeline.py" ]; then
    echo "❌ Error: s2s_pipeline.py not found"
    echo "   Please run this script from the speech-to-speech directory"
    exit 1
fi

# Check Python 3.12 environment
if [ ! -d ".venv-312" ]; then
    echo "❌ Error: Python 3.12 environment (.venv-312) not found"
    echo "   Please set up the Python 3.12 environment first"
    exit 1
fi

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️  No GPU detected - pipeline will run on CPU (slower)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Activate environment and start server
echo " Activating Python 3.12 environment..."
source .venv-312/bin/activate

echo " Starting pipeline server..."
echo "   This will take 2-3 minutes to load all models"
echo "   Look for: 'Receiver waiting to be connected...'"
echo ""

# Start the pipeline server
python s2s_pipeline.py \
    --mode socket \
    --recv_host 0.0.0.0 \
    --send_host 0.0.0.0 \
    --device cuda \
    --stt faster-whisper \
    --llm transformers \
    --tts parler \
    --lm_model_name microsoft/Phi-3-mini-4k-instruct \
    --log_level info

echo ""
echo "Pipeline server stopped"
