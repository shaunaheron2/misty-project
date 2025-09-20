# Friday Demo Deployment Guide
**Who-Dunnit Mystery Robot with Speech-to-Speech Pipeline**

## 🎯 Demo Overview
- **Misty-II robot** guided mystery solving using real-time speech interaction
- **Distributed AI**: Desktop PC (RTX 5070 Ti) serves AI pipeline, laptop controls robot
- **Performance**: <2000ms response times for natural conversation

## 🚀 Quick Start (30 seconds)

### Step 1: Start Pipeline Server on Desktop PC
```bash
cd /home/sheron/Documents/robots/speech-to-speech
source .venv-312/bin/activate
python s2s_pipeline.py --mode socket --recv_host 0.0.0.0 --send_host 0.0.0.0 --device cuda --stt faster-whisper --llm transformers --tts parler --lm_model_name microsoft/Phi-3-mini-4k-instruct --log_level info
```

### Step 2: Test Connection from Laptop
```bash
python test_remote_connection.py <DESKTOP_PC_IP>
# Should show: "🎉 All connections successful! 📡 Average network latency: ~5-15ms"
```

### Step 3: Connect Misty Robot
```bash
python misty_integration.py <MISTY_IP> <DESKTOP_PC_IP>
```

## 📋 Pre-Demo Checklist

### Desktop PC Setup
- [ ] Python 3.12 environment activated (`.venv-312`)
- [ ] CUDA drivers working (`nvidia-smi` shows RTX 5070 Ti)
- [ ] All models cached and loaded (first run may take 2-3 minutes)
- [ ] Firewall allows ports 12345, 12346 (`sudo ufw allow 12345 && sudo ufw allow 12346`)
- [ ] Pipeline server shows "Server listening on 0.0.0.0:12345"

### Network Configuration
- [ ] Desktop PC and laptop on same WiFi network
- [ ] Desktop PC IP address known (`ip addr show | grep inet`)
- [ ] Misty robot connected to same WiFi
- [ ] Misty robot IP address known (check Misty web interface)

### Robot Preparation
- [ ] Misty robot powered on and responsive
- [ ] Misty SDK installed in Python environment
- [ ] Robot expressions tested (16 different expressions available)
- [ ] Audio volume set appropriately (~50%)

## 🎭 Demo Flow

### 1. Introduction (30 seconds)
"This is a social robotics experiment where our Misty robot guides participants through collaborative mystery-solving tasks. The robot has a complete personality and can express emotions through colors, movements, and facial expressions."

### 2. Technical Demonstration (1 minute)
- Show the distributed architecture: "The AI runs on this powerful desktop PC with an RTX 5070 Ti, while the robot handles interaction"
- Display real-time latency monitoring: "We're tracking every component - voice detection, speech-to-text, AI reasoning, text-to-speech, and robot actions"
- Point out performance: "We're achieving response times under 2 seconds, which is faster than most voice assistants"

### 3. Interactive Demo (2-3 minutes)
Let Misty guide through one of the mystery tasks:
- **Suspect Identification**: "I have information about 6 suspects. Ask me yes/no questions to find the perpetrator."
- Watch robot expressions change based on responses
- Show JSON parsing: robot receives `{"msg": "Great question!", "expression": "excited"}`

### 4. Q&A (Remaining time)
- Explain the 3-tier hint system
- Discuss affect detection and adaptive behavior
- Show performance metrics and grading system

## 🔧 Technical Highlights for Professor

### Architecture Innovation
- **Distributed Processing**: Separates AI computation from robot interaction
- **Real-time Performance**: Component-level latency monitoring with automatic grading
- **Structured Conversation**: Task-specific prompts with pre-defined knowledge base

### Performance Metrics
```
Component Breakdown:
├─ VAD: ~45ms (voice detection)
├─ STT: ~294ms (speech transcription)
├─ LLM: ~760ms (response generation)
├─ TTS: ~452ms (voice synthesis)
└─ Robot: ~150ms (physical expressions)
Total: ~1701ms (Grade A+ performance)
```

### Research Contributions
1. **Multimodal Communication**: Simultaneous speech and physical expressions
2. **Affect-Responsive Interaction**: Robot adapts to user hesitation/confusion
3. **Production Monitoring**: Real-world robotics performance tracking
4. **Scalable Architecture**: Desktop AI power for resource-constrained robots

## 🛠️ Troubleshooting

### Common Issues
1. **"Connection refused"**: Check firewall settings on desktop PC
2. **Models downloading**: First run in new environment rebuilds cache
3. **Robot not responding**: Verify Misty IP and SDK installation
4. **High latency**: Check WiFi network, use ethernet if possible

### Fallback Options
1. **Local Mode**: Run everything on laptop if network issues
2. **API Mode**: Use cloud services (requires API keys)
3. **Demo Mode**: Pre-recorded responses if hardware fails

### Emergency Commands
```bash
# Check if pipeline is running
ps aux | grep s2s_pipeline

# Kill stuck processes
pkill -f s2s_pipeline

# Quick restart
./laptop_demo.sh
```

## 📊 Performance Dashboard

Real-time metrics available during demo:
- Component latency breakdown
- End-to-end conversation timing
- Performance grade (A+ to D)
- Network latency monitoring
- Robot expression execution times

**Data Export**: All metrics saved to JSON for post-demo analysis

## 🎯 Demo Success Criteria

**Technical Success:**
- [ ] Total response time < 2000ms consistently
- [ ] All robot expressions working correctly
- [ ] JSON parsing functioning (speech + actions)
- [ ] Network latency < 50ms

**Educational Success:**
- [ ] Clear explanation of distributed AI architecture
- [ ] Demonstration of human-robot interaction principles
- [ ] Evidence of real-time performance monitoring
- [ ] Q&A handling about social robotics research

---

**🤖 Ready for Demo!** This system demonstrates state-of-the-art human-robot interaction with production-ready performance monitoring.