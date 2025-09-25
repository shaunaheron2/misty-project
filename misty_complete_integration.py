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
    print("  Misty SDK not available. Install with: pip install git+https://github.com/MistyCommunity/Python-SDK.git")

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
            logger.info(f"Connected send socket to {self.pipeline_server_ip}:{self.pipeline_port}")

            # Connect to receive socket (audio output)
            self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.recv_socket.connect((self.pipeline_server_ip, self.pipeline_port + 1))
            logger.info(f" Connected recv socket to {self.pipeline_server_ip}:{self.pipeline_port + 1}")

            self.connected = True
            return True
        except Exception as e:
            logger.error(f" Failed to connect to pipeline server: {e}")
            self.connected = False
            return False

    def disconnect_from_pipeline(self):
        """Disconnect from pipeline server."""
        if self.send_socket:
            self.send_socket.close()
        if self.recv_socket:
            self.recv_socket.close()
        self.connected = False
        logger.info(" Disconnected from pipeline server")

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
        logger.info(f" Performed expression '{expression}' in {duration_ms:.1f}ms")
        return duration_ms

    def start_audio_server(self):
        """Start HTTP server for serving audio files to Misty."""
        def run_server():
            class AudioHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(self.audio_files_dir.parent), **kwargs)

            with socketserver.TCPServer(("", self.audio_server_port), AudioHandler) as httpd:
                logger.info(f" Audio server started on port {self.audio_server_port}")
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
        logger.info(f" Playing audio: {audio_url}")
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
        logger.info(" Starting audio capture process...")

        try:
            # Enable AV streaming service
            logger.info(" Enabling AV streaming service...")
            stat = self.robot.get_av_streaming_service_enabled()
            if not stat.json().get("result", False):
                self.robot.enable_av_streaming_service()

            time.sleep(0.1)
            self.robot.stop_av_streaming()
            time.sleep(0.1)

            # Start AV streaming
            logger.info(" Starting AV streaming...")
            self.robot.start_av_streaming(url="rtspd:1936", width=1920, height=1080, frameRate=30)
            time.sleep(0.5)

            self.av_streaming = True

            # Start FFmpeg audio capture
            rtsp_url = f"rtsp://{self.misty_ip}:1936/h264"
            logger.info(f" Connecting to RTSP stream: {rtsp_url}")

        except Exception as e:
            logger.error(f" Error in AV streaming setup: {e}")
            return

        try:
            # Create audio capture directory
            audio_capture_dir = Path("./audio_capture")
            audio_capture_dir.mkdir(exist_ok=True)

            # Generate unique filename for this recording session
            timestamp = int(time.time() * 1000)
            self.current_audio_file = audio_capture_dir / f"misty_audio_{timestamp}.wav"

            # Set up FFmpeg to capture audio to file (like the working script)
            self.ffmpeg_input = ffmpeg.input(rtsp_url, **{"use_wallclock_as_timestamps": "1", "rtsp_transport": "tcp"})

            # Start audio capture to file
            self.audio_process = (
                self.ffmpeg_input
                .output(str(self.current_audio_file), format="wav", acodec="pcm_s16le", ac=1, ar=16000, t=10)  # 10 second max
                .overwrite_output()
                .run_async(pipe_stderr=True)
            )

            # Wait a moment and check if process started successfully
            time.sleep(0.5)
            if self.audio_process.poll() is not None:
                # Process has already terminated
                stderr_output = self.audio_process.stderr.read()
                logger.error(f" FFmpeg failed to start: {stderr_output.decode()}")
                self.audio_process = None
                return

            logger.info(f" Started audio capture to file: {self.current_audio_file}")

        except Exception as e:
            logger.error(f" Failed to start FFmpeg process: {e}")
            self.audio_process = None

    def stop_audio_capture(self):
        """Stop audio capture from Misty."""
        if self.audio_process:
            self.audio_process.terminate()
            self.audio_process = None

        if self.av_streaming:
            self.robot.stop_av_streaming()
            self.av_streaming = False

        logger.info(" Stopped audio capture from Misty")

    def send_audio_to_pipeline(self):
        """Send captured audio file to pipeline server."""
        if not self.audio_process or not self.send_socket:
            logger.warning("Audio process or send socket not available")
            return

        try:
            logger.info(" Waiting for audio capture to complete...")

            # Wait for FFmpeg to finish capturing (up to recording duration)
            while self.recording and self.audio_process.poll() is None:
                time.sleep(0.1)

            # Check if we have a captured audio file
            if hasattr(self, 'current_audio_file') and self.current_audio_file.exists():
                file_size = self.current_audio_file.stat().st_size
                logger.info(f" Audio file captured: {self.current_audio_file} ({file_size} bytes)")

                if file_size > 0:
                    # Use wave library to read raw audio data (skip WAV headers)
                    try:
                        with wave.open(str(self.current_audio_file), 'rb') as wav_file:
                            # Get audio parameters
                            frames = wav_file.getnframes()
                            sample_rate = wav_file.getframerate()
                            channels = wav_file.getnchannels()

                            logger.info(f" Audio info: {frames} frames, {sample_rate}Hz, {channels} channels")

                            # Read raw audio data (without WAV headers)
                            raw_audio_data = wav_file.readframes(frames)

                        logger.info(f"Streaming {len(raw_audio_data)} bytes of raw audio to pipeline...")

                        # Stream raw audio data to pipeline with timing (simulate real-time)
                        chunk_size = 1024  # Match pipeline expectations
                        sample_rate = 16000
                        bytes_per_second = sample_rate * 2  # 16-bit = 2 bytes per sample
                        chunk_duration = chunk_size / bytes_per_second  # Time per chunk in seconds

                        bytes_sent = 0
                        start_time = time.time()

                        for i in range(0, len(raw_audio_data), chunk_size):
                            chunk = raw_audio_data[i:i + chunk_size]
                            self.send_socket.sendall(chunk)
                            bytes_sent += len(chunk)

                            # Simulate real-time streaming by adding appropriate delay
                            elapsed = time.time() - start_time
                            expected_time = (bytes_sent / bytes_per_second)
                            if expected_time > elapsed:
                                time.sleep(expected_time - elapsed)

                        logger.info(f"Successfully streamed {bytes_sent} bytes of raw audio to pipeline")

                    except wave.Error as e:
                        logger.error(f" Error reading WAV file: {e}")
                    except Exception as e:
                        logger.error(f" Error processing audio file: {e}")
                else:
                    logger.warning("  Audio file is empty - no audio captured")
            else:
                logger.warning("  No audio file found or capture failed")

        except Exception as e:
            logger.error(f" Error sending audio file to pipeline: {e}")
            # Log FFmpeg stderr for debugging
            if self.audio_process and self.audio_process.stderr:
                try:
                    stderr_output = self.audio_process.stderr.read()
                    if stderr_output:
                        logger.error(f"FFmpeg stderr: {stderr_output.decode()}")
                except:
                    pass

    def receive_audio_from_pipeline(self):
        """Receive processed audio from pipeline server."""
        if not self.recv_socket:
            logger.warning("No receive socket available")
            return

        logger.info(" Waiting for audio response from pipeline...")

        def receive_with_timeout(conn, chunk_size, timeout=5.0):
            """Receive data with timeout."""
            import select
            ready = select.select([conn], [], [], timeout)
            if ready[0]:
                return conn.recv(chunk_size)
            return None

        try:
            # Receive audio chunks from pipeline
            audio_chunks = []
            total_timeout = 15.0  # 15 second max wait
            start_time = time.time()

            while self.connected and (time.time() - start_time) < total_timeout:
                chunk_size = 1024
                audio_data = receive_with_timeout(self.recv_socket, chunk_size, timeout=2.0)

                if audio_data:
                    if not audio_chunks:  # First chunk received
                        logger.info(f" Receiving audio response from pipeline...")

                    audio_chunks.append(audio_data)

                    # Check if we have enough data (pipeline might send in bursts)
                    total_bytes = sum(len(chunk) for chunk in audio_chunks)
                    if total_bytes > 10000:  # If we have > 10KB, check if more is coming
                        # Wait briefly for more data
                        more_data = receive_with_timeout(self.recv_socket, chunk_size, timeout=0.5)
                        if more_data:
                            audio_chunks.append(more_data)
                        else:
                            break  # No more data coming
                else:
                    if audio_chunks:
                        break  # We have some data and no more is coming
                    # No data yet, keep waiting

            if audio_chunks:
                # Combine all chunks and play
                complete_audio = b''.join(audio_chunks)
                logger.info(f" Received {len(complete_audio)} bytes of response audio")
                self.play_audio_response(complete_audio)
            else:
                logger.warning("  No audio response received from pipeline")
                logger.info(" Falling back to generating local TTS response...")
                self.generate_fallback_tts_response()

        except Exception as e:
            logger.error(f" Error receiving audio from pipeline: {e}")

    def generate_fallback_tts_response(self):
        """Generate a simple TTS response when pipeline doesn't respond."""
        try:
            # Simple fallback responses for testing
            fallback_responses = [
                "I heard you speaking. Can you tell me more about what you're looking for?",
                "Interesting. What else can you tell me about this mystery?",
                "I'm listening. Please continue with your investigation.",
                "That's helpful information. What would you like to explore next?",
                "I understand. Can you give me more details?"
            ]

            import random
            response_text = random.choice(fallback_responses)

            logger.info(f"  Generating fallback response: '{response_text}'")

            # Create robot_speech_files directory
            speech_dir = Path("./robot_speech_files")
            speech_dir.mkdir(exist_ok=True)
            speech_file = speech_dir / "fallback_speech.wav"

            # Generate simple TTS (you could use pyttsx3, gTTS, or a simple beep)
            # For now, let's create a simple audio file or use system TTS
            try:
                # Try using system say command (macOS/Linux)
                import subprocess
                subprocess.run([
                    'say', response_text, '-o', str(speech_file), '--data-format=LEI16@16000'
                ], check=True, capture_output=True)

                # Play on Misty
                audio_url = f"http://{self.get_local_ip()}:8000/robot_speech_files/fallback_speech.wav"
                logger.info(f" Playing fallback audio: {audio_url}")
                self.robot.play_audio(audio_url, volume=self.volume)

            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to robot expression only
                logger.info(" TTS not available, using robot expression instead")
                self.perform_expression("question")
                time.sleep(2)  # Give user time to see expression

        except Exception as e:
            logger.error(f" Error generating fallback response: {e}")

    def start_conversation(self):
        """Start a new conversation turn with latency monitoring."""
        self.current_conversation_id = int(time.time())
        monitor.start_conversation()
        logger.info(f" Starting conversation {self.current_conversation_id}")

    def run_experiment_loop(self):
        """Main experiment loop for who-dunnit mystery solving."""
        if not self.connect_to_pipeline():
            return

        logger.info(" Starting Who-Dunnit Mystery Experiment")

        # Start audio server
        self.start_audio_server()

        try:
            # Initial greeting
            self.start_conversation()
            self.perform_expression("hi")

            conversation_count = 0
            max_conversations = 5  # Experiment limit

            while conversation_count < max_conversations and self.connected:
                try:
                    logger.info(f" Starting conversation turn {conversation_count + 1}")

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
                    logger.info(" Experiment interrupted by user")
                    break
                except Exception as e:
                    logger.error(f" Error in conversation loop: {e}")
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

            logger.info(f" Experiment complete. Report saved to misty_experiment_report_{timestamp}.json")

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