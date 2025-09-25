#!/usr/bin/env python3
"""
Complete Misty Robot Integration for Who-Dunnit Speech-to-Speech Pipeline
Connects HuggingFace pipeline to Misty robot hardware with full audio processing.
"""

import json
import logging
import socket
import time
import threading
import os
import http.server
import socketserver
import ffmpeg
from pathlib import Path
from typing import Optional
import base64
import subprocess
import wave

try:
    from mistyPy.Robot import Robot
    from mistyPy.Events import Events
    MISTY_AVAILABLE = True
except ImportError:
    MISTY_AVAILABLE = False
    print("⚠️  Misty SDK not available. Install with: pip install git+https://github.com/MistyCommunity/Python-SDK.git")

from latency_monitor import monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Robot expressions matching who-dunnit prompt
ROBOT_EXPRESSIONS = {
    "hi": {"led_color": (0, 199, 252), "image": "e_Admiration.jpg", "head": (-5, 0, 0)},
    "listen": {"led_color": (0, 199, 252), "image": "e_Surprise.jpg", "head": (-6, 30, 0)},
    "question": {"led_color": (255, 255, 0), "image": "e_DefaultContent.jpg", "head": (0, 0, 0)},
    "correct": {"led_color": (0, 255, 0), "image": "e_Joy.jpg", "head": (5, 0, 0)},
    "wrong": {"led_color": (255, 100, 0), "image": "e_Sadness.jpg", "head": (-10, 0, 0)},
    "hint": {"led_color": (255, 165, 0), "image": "e_Ecstacy.jpg", "head": (-5, 10, 0)},
    "thinking": {"led_color": (128, 0, 128), "image": "e_Contemplate.jpg", "head": (0, -15, 0)},
    "excited": {"led_color": (255, 20, 147), "image": "e_Amazement.jpg", "head": (10, 0, 0)},
    "frustrated": {"led_color": (255, 69, 0), "image": "e_Rage.jpg", "head": (-15, 0, 0)},
    "worry": {"led_color": (169, 169, 169), "image": "e_Disgust.jpg", "head": (0, 0, -10)},
    "confused": {"led_color": (255, 255, 0), "image": "e_Disoriented.jpg", "head": (0, 20, 0)},
    "funny": {"led_color": (255, 192, 203), "image": "e_Glee.jpg", "head": (15, 0, 0)},
    "goodbye": {"led_color": (100, 70, 160), "image": "e_DefaultContent.jpg", "head": (-5, 0, 0)},
    "love": {"led_color": (255, 105, 180), "image": "e_Love.jpg", "head": (0, 0, 0)},
    "head-up-down-nod": {"led_color": (0, 199, 252), "head_sequence": [(-15, 0, 0), (5, 0, 0), (-15, 0, 0), (5, 0, 0), (-5, 0, 0)]},
}

class MistyWhoDunnitRobot:
    """
    Complete Misty robot integration for who-dunnit mystery solving experiment.
    """

    def __init__(self, misty_ip: str, pipeline_server_ip: str, pipeline_port: int = 12345):
        if not MISTY_AVAILABLE:
            raise ImportError("Misty SDK not available. Please install it first.")

        self.misty_ip = misty_ip
        self.pipeline_server_ip = pipeline_server_ip
        self.pipeline_port = pipeline_port

        # Initialize Misty robot
        self.robot = Robot(misty_ip)
        self.volume = 50

        # Pipeline connections
        self.send_socket = None  # Send audio to pipeline
        self.recv_socket = None  # Receive audio from pipeline
        self.connected = False

        # State management
        self.current_conversation_id = None
        self.listening = False
        self.recording = False
        self.av_streaming = False

        # Audio server for Misty
        self.audio_server = None
        self.audio_server_port = 8000
        self.audio_files_dir = Path("./robot_audio_files")
        self.audio_files_dir.mkdir(exist_ok=True)

        # FFmpeg processes for AV streaming
        self.audio_process = None

        # Initialize robot to default state
        self.reset_robot()

    def reset_robot(self):
        """Reset robot to neutral state."""
        self.robot.change_led(100, 70, 160)  # Purple - neutral
        self.robot.display_image("e_DefaultContent.jpg")
        self.robot.move_head(0, 0, 0, 100)  # Neutral head position

    def connect_to_pipeline(self) -> bool:
        """Connect to the speech-to-speech pipeline server."""
        try:
            # Connect to send socket (audio input)
            self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.send_socket.connect((self.pipeline_server_ip, self.pipeline_port))
            logger.info(f"✅ Connected send socket to {self.pipeline_server_ip}:{self.pipeline_port}")

            # Connect to receive socket (audio output)
            self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.recv_socket.connect((self.pipeline_server_ip, self.pipeline_port + 1))
            logger.info(f"✅ Connected recv socket to {self.pipeline_server_ip}:{self.pipeline_port + 1}")

            self.connected = True
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to pipeline server: {e}")
            self.connected = False
            return False

    def disconnect_from_pipeline(self):
        """Disconnect from pipeline server."""
        if self.send_socket:
            self.send_socket.close()
        if self.recv_socket:
            self.recv_socket.close()
        self.connected = False
        logger.info("🔌 Disconnected from pipeline server")

    def perform_expression(self, expression: str) -> float:
        """Perform robot expression and return execution time."""
        start_time = time.time()

        if expression not in ROBOT_EXPRESSIONS:
            logger.warning(f"Unknown expression: {expression}")
            expression = "question"  # Default fallback

        expr_config = ROBOT_EXPRESSIONS[expression]

        # Change LED color
        if "led_color" in expr_config:
            r, g, b = expr_config["led_color"]
            self.robot.change_led(r, g, b)

        # Display image
        if "image" in expr_config:
            self.robot.display_image(expr_config["image"])

        # Move head
        if "head" in expr_config:
            pitch, roll, yaw = expr_config["head"]
            self.robot.move_head(pitch, roll, yaw, 500)  # 500ms duration

        # Handle head sequences (like nodding)
        if "head_sequence" in expr_config:
            for i, (pitch, roll, yaw) in enumerate(expr_config["head_sequence"]):
                self.robot.move_head(pitch, roll, yaw, 300)
                time.sleep(0.4)  # Wait for movement to complete

        duration_ms = (time.time() - start_time) * 1000
        monitor.log_robot_action(expression, duration_ms)
        logger.info(f"🤖 Performed expression '{expression}' in {duration_ms:.1f}ms")
        return duration_ms

    def start_audio_server(self):
        """Start HTTP server for serving audio files to Misty."""
        def run_server():
            class AudioHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(self.audio_files_dir.parent), **kwargs)

            with socketserver.TCPServer(("", self.audio_server_port), AudioHandler) as httpd:
                logger.info(f"🎵 Audio server started on port {self.audio_server_port}")
                self.audio_server = httpd
                httpd.serve_forever()

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(1)  # Give server time to start

    def play_audio_response(self, audio_data: bytes) -> float:
        """Play audio response on Misty and return playback time."""
        start_time = time.time()

        # Save audio to server directory
        timestamp = int(time.time() * 1000)
        audio_filename = f"misty_response_{timestamp}.wav"
        audio_file_path = self.audio_files_dir / audio_filename

        with open(audio_file_path, 'wb') as f:
            f.write(audio_data)

        # Play on Misty via HTTP
        audio_url = f"http://{self.get_local_ip()}:{self.audio_server_port}/{self.audio_files_dir.name}/{audio_filename}"
        logger.info(f"🔊 Playing audio: {audio_url}")
        self.robot.play_audio(audio_url, volume=self.volume)

        duration_ms = (time.time() - start_time) * 1000
        return duration_ms

    def get_local_ip(self) -> str:
        """Get local IP address for serving audio files to Misty."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    def start_audio_capture(self):
        """Start audio capture from Misty using AV streaming."""
        # Enable AV streaming service
        stat = self.robot.get_av_streaming_service_status()
        if not stat.json().get("result", False):
            self.robot.enable_av_streaming_service()

        time.sleep(0.1)
        self.robot.stop_av_streaming()
        time.sleep(0.1)

        # Start AV streaming
        self.robot.start_av_streaming(url="rtspd:1936", width=1920, height=1080, frameRate=30)
        time.sleep(0.5)

        self.av_streaming = True

        # Start FFmpeg audio capture
        rtsp_url = f"rtsp://{self.misty_ip}:1936/h264"

        self.audio_process = (
            ffmpeg
            .input(rtsp_url, **{"rtsp_transport": "tcp"})
            .output("pipe:", format="s16le", acodec="pcm_s16le", ac=1, ar=16000)
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        logger.info("🎤 Started audio capture from Misty")

    def stop_audio_capture(self):
        """Stop audio capture from Misty."""
        if self.audio_process:
            self.audio_process.terminate()
            self.audio_process = None

        if self.av_streaming:
            self.robot.stop_av_streaming()
            self.av_streaming = False

        logger.info("🛑 Stopped audio capture from Misty")

    def send_audio_to_pipeline(self):
        """Send captured audio to pipeline server."""
        if not self.audio_process or not self.send_socket:
            return

        packet_size = 4096
        try:
            while self.recording and self.audio_process:
                # Read audio data from FFmpeg
                audio_data = self.audio_process.stdout.read(packet_size)
                if audio_data:
                    # Send to pipeline
                    self.send_socket.sendall(audio_data)
                else:
                    break
        except Exception as e:
            logger.error(f"Error sending audio to pipeline: {e}")

    def receive_audio_from_pipeline(self):
        """Receive processed audio from pipeline server."""
        if not self.recv_socket:
            return

        def receive_full_chunk(conn, chunk_size):
            data = b""
            while len(data) < chunk_size:
                packet = conn.recv(chunk_size - len(data))
                if not packet:
                    return None
                data += packet
            return data

        try:
            # Receive audio chunks from pipeline
            audio_chunks = []
            while self.connected:
                chunk_size = 2048  # Match pipeline chunk size
                audio_data = receive_full_chunk(self.recv_socket, chunk_size)
                if audio_data:
                    audio_chunks.append(audio_data)
                    # Check for end marker or timeout
                    if len(audio_chunks) > 100:  # Prevent infinite accumulation
                        break
                else:
                    break

            if audio_chunks:
                # Combine all chunks and play
                complete_audio = b''.join(audio_chunks)
                self.play_audio_response(complete_audio)

        except Exception as e:
            logger.error(f"Error receiving audio from pipeline: {e}")

    def start_conversation(self):
        """Start a new conversation turn with latency monitoring."""
        self.current_conversation_id = int(time.time())
        monitor.start_conversation()
        logger.info(f"🎯 Starting conversation {self.current_conversation_id}")

    def run_experiment_loop(self):
        """Main experiment loop for who-dunnit mystery solving."""
        if not self.connect_to_pipeline():
            return

        logger.info("🕵️ Starting Who-Dunnit Mystery Experiment")

        # Start audio server
        self.start_audio_server()

        try:
            # Initial greeting
            self.start_conversation()
            self.perform_expression("hi")

            conversation_count = 0
            max_conversations = 50  # Experiment limit

            while conversation_count < max_conversations and self.connected:
                try:
                    logger.info(f"🔄 Starting conversation turn {conversation_count + 1}")

                    # Start listening - change LED to blue
                    self.robot.change_led(0, 199, 252)  # Blue for listening
                    self.perform_expression("listen")

                    # Start audio capture from Misty
                    self.start_audio_capture()
                    self.recording = True

                    # Start threads for audio processing
                    send_thread = threading.Thread(target=self.send_audio_to_pipeline, daemon=True)
                    recv_thread = threading.Thread(target=self.receive_audio_from_pipeline, daemon=True)

                    send_thread.start()
                    recv_thread.start()

                    # Listen for speech for up to 10 seconds
                    listen_duration = 10.0
                    start_time = time.time()

                    while (time.time() - start_time) < listen_duration and self.recording:
                        time.sleep(0.1)

                    # Stop recording
                    self.recording = False
                    self.stop_audio_capture()

                    # Wait for pipeline response
                    recv_thread.join(timeout=10.0)

                    # Reset to neutral state
                    self.robot.change_led(100, 70, 160)  # Purple - neutral

                    conversation_count += 1
                    time.sleep(2.0)  # Pause between turns

                except KeyboardInterrupt:
                    logger.info("🛑 Experiment interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"❌ Error in conversation loop: {e}")
                    time.sleep(2.0)  # Recovery pause

        finally:
            # Cleanup
            self.recording = False
            self.stop_audio_capture()
            self.disconnect_from_pipeline()
            self.perform_expression("goodbye")

            # Generate experiment report
            report = monitor.get_performance_report()
            timestamp = int(time.time())

            with open(f"misty_experiment_report_{timestamp}.json", 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"📊 Experiment complete. Report saved to misty_experiment_report_{timestamp}.json")

def main():
    """Run Misty integration."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python misty_complete_integration.py <misty_ip> <pipeline_server_ip>")
        print("Example: python misty_complete_integration.py 192.168.1.100 192.168.1.50")
        sys.exit(1)

    misty_ip = sys.argv[1]
    pipeline_server_ip = sys.argv[2]

    robot = MistyWhoDunnitRobot(misty_ip, pipeline_server_ip)
    robot.run_experiment_loop()

if __name__ == "__main__":
    main()