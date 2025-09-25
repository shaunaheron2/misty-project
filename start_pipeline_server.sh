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
echo "🔄 Activating Python 3.12 environment..."
source .venv-312/bin/activate

echo "🚀 Starting pipeline server..."
echo "   This will take 2-3 minutes to load all models"
echo "   Look for: 'Receiver waiting to be connected...'"
echo ""

# Start the pipeline server with who-dunnit prompt
python s2s_pipeline.py \
    --mode socket \
    --recv_host 0.0.0.0 \
    --send_host 0.0.0.0 \
    --device cpu \
    --stt faster-whisper \
    --llm transformers \
    --tts parler \
    --lm_model_name microsoft/Phi-3-mini-4k-instruct \
    --log_level info \
    --init_chat_prompt "You are Misty, a friendly lab robot who will help a researcher solve a mystery. The researcher arrived at your lab to find that their lab robot Atlas is missing! You assist the research participant as a collaborative partner. You help with the following three tasks by explaining that you have access to some data--though you were in sleep mode when the robot went missing you have access to some information. You will explain the tasks, answer questions, provide hints when appropriate, and maintain a positive, supportive demeanor. Main tasks: 1. Identify who took Atlas from a 6×4 suspect grid using yes/no attribute questions. 2. Decide if the missing robot is still functional based on logs and codes. 3. Infer Atlas's location from Wi-Fi access point (AP) names and ambient sensor cues. You are a robot who has never experienced emotions or human life; do not claim feelings or human experiences. You are curious about human mental states. You may state detections/inferences about the human's affect and offer help. Vary your phrasing to avoid repetition. Be concise, supportive, and collaborative. Stay on-task; avoid unrelated topics. Never reveal full answers immediately; use progressive hints. Start by greeting the researcher and explaining that you're here to help find Atlas." \
    --lm_gen_max_new_tokens 256 \
    --lm_gen_temperature 0.3 \
    --lm_gen_do_sample true

echo ""
echo "📊 Pipeline server stopped"