# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is a **social robotics research project** developing an inference pipeline for real-time human-robot interaction. The goal is to enable a small social robot (Misty-II) to guide humans through collaborative tasks using speech-to-speech communication while responding to user mental states.

**Primary Application**: "Who-dunnit" mystery-solving tasks where the robot assists humans with:
1. Identifying suspects using yes/no attribute questions
2. Analyzing system logs to determine robot functionality
3. Inferring location from Wi-Fi and sensor data

## Core Pipeline Architecture

**VAD → STT → LM → TTS**

1. **Voice Activity Detection** - Silero VAD v5
2. **Speech to Text** - Whisper variants, Lightning Whisper MLX, Paraformer
3. **Language Model** - Transformers models, MLX-LM, OpenAI API
4. **Text to Speech** - Parler-TTS, MeloTTS, ChatTTS

## Development Commands

### Installation
```bash
# Install dependencies (use uv for faster installs)
uv pip install -r requirements.txt

# For Mac users
uv pip install -r requirements_mac.txt

# For MeloTTS support
python -m unidic download
```

### Running the Pipeline

#### Testing Without Robot (Recommended for Development)
```bash
# Local testing with optimal settings
python s2s_pipeline.py --local_mac_optimal_settings

# Server/client mode for testing
python s2s_pipeline.py --recv_host 0.0.0.0 --send_host 0.0.0.0
python listen_and_play.py --host <SERVER_IP>
```

#### Robot Integration (Misty-II)
```bash
# Run the robot dialogue system (requires Misty-II robot)
python llm_based_human_robot_dialogue.py <MISTY_IP_ADDRESS>

# Start HTTP server for robot audio files
python -m http.server 8000
```

#### CUDA Optimized Pipeline
```bash
python s2s_pipeline.py \
    --lm_model_name microsoft/Phi-3-mini-4k-instruct \
    --stt_compile_mode reduce-overhead \
    --tts_compile_mode default \
    --recv_host 0.0.0.0 \
    --send_host 0.0.0.0
```

### Docker
```bash
docker compose up
```

## Development Focus

### Immediate Goals
1. **Setup speech pipeline with who-dunnit prompt using Hugging Face models** (avoid paid APIs)
2. **Test without Misty-II robot** for rapid development
3. **Integrate with robot websockets** for real-time interaction

### Key Files for Robot Integration

#### Core Implementation
- `llm_based_human_robot_dialogue.py` - Misty-II robot integration with Deepgram STT + OpenAI TTS + Gemini LLM
- `who-dunnit-instruction.md` - Complete task instructions and robot personality
- `claude-instruction.md` - Project context and goals

#### Pipeline Components
- `s2s_pipeline.py` - Main HuggingFace-based pipeline (preferred for development)
- `listen_and_play.py` - Audio client for testing without robot

### Misty-II Robot Integration

#### Hardware Platform
- **Documentation**: https://docs.mistyrobotics.com/
- **Python SDK**: https://github.com/MistyCommunity/Python-SDK

#### Robot Features
- **Custom Actions**: Defined in `custom_actions` dict (head movements, expressions)
- **Expression System**: JSON responses with `msg` and `expression` fields
- **Audio Streaming**: RTSP stream processing with FFmpeg
- **LED Indicators**: Purple (idle), Blue (listening)
- **AV Streaming**: 1920x1080 @ 30fps via RTSP

#### Behavioral Modes
- **CONTROL**: Rule-based, reactive, neutral tone
- **RESPONSIVE**: Proactive, affect-aware with personality

#### Task-Specific Knowledge
The robot guides users through 3-stage mystery solving:
1. **Suspect Identification** (Ground truth: ID 17 - black hair, glasses, beanie, green jacket, scarf)
2. **System Analysis** (STATUS 42 = low battery, ALERT 556 = security breach)
3. **Location Inference** (Wi-Fi AP naming: BUILDING-FLOORWING-AP#, target: ENG-2W Loading Bay)

### Architecture for Development

#### HuggingFace Pipeline (Preferred)
Use `s2s_pipeline.py` with local models to avoid API costs:
```bash
python s2s_pipeline.py --local_mac_optimal_settings --language en
```

#### API-Based Pipeline (Current Robot Implementation)
Uses paid services (Deepgram STT, OpenAI TTS, Gemini LLM) - good for final integration.

### Environment Setup
Required environment variables for robot integration:
- `DEEPGRAM_API_KEY` - Speech-to-text
- `GPT_API_KEY` - Text-to-speech
- `GEMINI_API_KEY` - Language model
- `MISTY_MODE` - "CONTROL" or "RESPONSIVE"

## Development Strategy

1. **Start with HuggingFace pipeline** (`s2s_pipeline.py`) for cost-effective development
2. **Test prompts and responses** using local models
3. **Integrate robot-specific behaviors** (expressions, timing, personality)
4. **Switch to API services** only when ready for full Misty-II robot testing

The HuggingFace pipeline provides the same VAD→STT→LM→TTS flow but with local models, making it ideal for iterative prompt development and testing without robot hardware.