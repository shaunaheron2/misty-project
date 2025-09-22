#!/usr/bin/env python3
"""
Misty Robot Integration for Who-Dunnit Speech-to-Speech Pipeline
Connects HuggingFace pipeline to Misty robot hardware.
"""

import json
import logging
import socket
import time
import threading
from typing import Optional

try:
    from mistyPy.Robot import Robot
    from mistyPy.Events import Events
    MISTY_AVAILABLE = True
except ImportError:
    MISTY_AVAILABLE = False
    print("⚠️  Misty SDK not available. Install with: pip install git+https://github.com/MistyCommunity/Python-SDK.git")

from latency_monitor import monitor

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
    Misty robot integration for who-dunnit mystery solving experiment.

    Connects to remote speech-to-speech pipeline server and handles:
    - Audio capture and playback
    - Robot expressions based on JSON responses
    - Latency monitoring for robot actions
    - Network communication with pipeline server
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

        # Pipeline connection
        self.pipeline_socket = None
        self.connected = False

        # State management
        self.current_conversation_id = None
        self.listening = False

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
            self.pipeline_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.pipeline_socket.connect((self.pipeline_server_ip, self.pipeline_port))
            self.connected = True
            logger.info(f"✅ Connected to pipeline server at {self.pipeline_server_ip}:{self.pipeline_port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to pipeline server: {e}")
            self.connected = False
            return False

    def disconnect_from_pipeline(self):
        """Disconnect from pipeline server."""
        if self.pipeline_socket:
            self.pipeline_socket.close()
            self.connected = False
            logger.info("🔌 Disconnected from pipeline server")

    def perform_expression(self, expression: str) -> float:
        """
        Perform robot expression and return execution time.

        Returns:
            float: Time taken to execute expression in milliseconds
        """
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

        # Log to latency monitor
        monitor.log_robot_action(expression, duration_ms)

        logger.info(f"🤖 Performed expression '{expression}' in {duration_ms:.1f}ms")
        return duration_ms

    def parse_pipeline_response(self, response_text: str) -> tuple[str, Optional[str]]:
        """
        Parse JSON response from pipeline to extract message and expression.

        Returns:
            tuple: (message_text, expression_name)
        """
        try:
            # Try to parse as JSON
            if response_text.strip().startswith('{') and response_text.strip().endswith('}'):
                data = json.loads(response_text)
                message = data.get('msg', response_text)
                expression = data.get('expression', None)

                logger.info(f"📝 Parsed response - Message: '{message[:50]}...', Expression: {expression}")
                return message, expression
            else:
                # Plain text response
                return response_text, None

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response_text[:100]}...")
            return response_text, None

    def start_conversation(self):
        """Start a new conversation turn with latency monitoring."""
        self.current_conversation_id = int(time.time())
        monitor.start_conversation()
        logger.info(f"🎯 Starting conversation {self.current_conversation_id}")

    def play_audio_response(self, audio_data: bytes) -> float:
        """
        Play audio response on Misty and return playback time.

        Returns:
            float: Audio playback duration in milliseconds
        """
        start_time = time.time()

        # Save audio to temporary file
        audio_file = f"/tmp/misty_response_{int(time.time())}.wav"
        with open(audio_file, 'wb') as f:
            f.write(audio_data)

        # Play on Misty
        # Note: This is a simplified version - you'd need to implement
        # proper audio file serving for Misty's HTTP-based audio system
        self.robot.play_audio(f"http://{self.get_local_ip()}:8000/audio/{audio_file}")

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

    def run_experiment_loop(self):
        """
        Main experiment loop for who-dunnit mystery solving.

        Handles conversation flow with latency monitoring.
        """
        if not self.connect_to_pipeline():
            return

        logger.info("🕵️ Starting Who-Dunnit Mystery Experiment")

        try:
            # Initial greeting
            self.start_conversation()
            self.perform_expression("hi")

            # Send initial prompt to pipeline
            initial_prompt = "Start conversation"
            # ... implement socket communication with pipeline

            conversation_count = 0
            max_conversations = 50  # Experiment limit

            while conversation_count < max_conversations and self.connected:
                try:
                    # Wait for user speech input
                    # Process through pipeline
                    # Handle response
                    # Monitor latency

                    conversation_count += 1
                    time.sleep(0.1)  # Small delay to prevent tight loop

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in conversation loop: {e}")

        finally:
            self.disconnect_from_pipeline()
            self.perform_expression("goodbye")

            # Generate experiment report
            report = monitor.get_performance_report()
            timestamp = int(time.time())

            with open(f"misty_experiment_report_{timestamp}.json", 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f" Experiment complete. Report saved to misty_experiment_report_{timestamp}.json")

def main():
    """Test Misty integration."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python misty_integration.py <misty_ip> <pipeline_server_ip>")2
        print("Example: python misty_integration.py 192.168.1.100 192.168.1.50")
        sys.exit(1)

    misty_ip = sys.argv[1]
    pipeline_server_ip = sys.argv[2]

    robot = MistyWhoDunnitRobot(misty_ip, pipeline_server_ip)
    robot.run_experiment_loop()

if __name__ == "__main__":
    main()