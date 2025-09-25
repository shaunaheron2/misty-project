#!/usr/bin/env python3
"""
Direct test of pipeline server by sending a captured audio file.
"""

import socket
import wave
import time
import sys
from pathlib import Path

def test_pipeline_with_audio_file(server_ip, audio_file_path, recv_port=12345, send_port=12346):
    """Test pipeline by sending an audio file directly."""

    print(f"Testing pipeline at {server_ip} with audio file: {audio_file_path}")

    # Read the audio file
    try:
        with wave.open(str(audio_file_path), 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            raw_audio_data = wav_file.readframes(frames)

        print(f"Audio loaded: {len(raw_audio_data)} bytes, {frames} frames, {sample_rate}Hz")

    except Exception as e:
        print(f"Error loading audio file: {e}")
        return False

    # Connect to pipeline
    try:
        # Connect to send socket (audio input)
        print("Connecting to pipeline send socket...")
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_socket.connect((server_ip, recv_port))
        print(f"Connected to send socket {server_ip}:{recv_port}")

        # Connect to receive socket (audio output)
        print("Connecting to pipeline receive socket...")
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recv_socket.connect((server_ip, send_port))
        print(f"Connected to receive socket {server_ip}:{send_port}")

    except Exception as e:
        print(f"Error connecting to pipeline: {e}")
        return False

    try:
        # Send audio data
        print("Sending audio data...")
        chunk_size = 1024
        bytes_sent = 0

        for i in range(0, len(raw_audio_data), chunk_size):
            chunk = raw_audio_data[i:i + chunk_size]
            send_socket.sendall(chunk)
            bytes_sent += len(chunk)

        print(f"Sent {bytes_sent} bytes of audio data")

        # Wait for response
        print("Waiting for pipeline response...")
        recv_socket.settimeout(30.0)  # 30 second timeout

        audio_chunks = []
        start_time = time.time()

        while True:
            try:
                chunk = recv_socket.recv(1024)
                if chunk:
                    if not audio_chunks:
                        print(f"First response received after {time.time() - start_time:.1f}s")
                    audio_chunks.append(chunk)

                    # Check if we have enough data
                    total_bytes = sum(len(c) for c in audio_chunks)
                    if total_bytes > 5000:  # Got some substantial response
                        # Try to get a bit more, then break
                        recv_socket.settimeout(1.0)  # Short timeout for final chunks
                        try:
                            while True:
                                chunk = recv_socket.recv(1024)
                                if chunk:
                                    audio_chunks.append(chunk)
                                else:
                                    break
                        except socket.timeout:
                            break
                        break
                else:
                    break

            except socket.timeout:
                if audio_chunks:
                    print("Timeout reached, but got some data")
                    break
                else:
                    print("Timeout - no response from pipeline")
                    return False

        if audio_chunks:
            total_response = b''.join(audio_chunks)
            print(f"SUCCESS! Received {len(total_response)} bytes of response audio")

            # Save response for testing
            response_file = Path("pipeline_response_test.wav")
            with open(response_file, 'wb') as f:
                f.write(total_response)
            print(f"Response saved to: {response_file}")
            return True
        else:
            print("No response received from pipeline")
            return False

    except Exception as e:
        print(f"Error during pipeline test: {e}")
        return False

    finally:
        send_socket.close()
        recv_socket.close()

def main():
    if len(sys.argv) < 2:
        # Use the most recent audio file
        audio_dir = Path("./audio_capture")
        if audio_dir.exists():
            audio_files = list(audio_dir.glob("*.wav"))
            if audio_files:
                audio_file = sorted(audio_files)[-1]  # Most recent
                print(f"Using most recent audio file: {audio_file}")
            else:
                print("No audio files found. Run the misty integration first.")
                return
        else:
            print("No audio_capture directory found")
            return
    else:
        audio_file = Path(sys.argv[1])
        if not audio_file.exists():
            print(f"Audio file not found: {audio_file}")
            return

    server_ip = sys.argv[2] if len(sys.argv) > 2 else "100.95.246.30"

    success = test_pipeline_with_audio_file(server_ip, audio_file)

    if success:
        print("\nPipeline test PASSED - pipeline is working!")
    else:
        print("\nPipeline test FAILED - check pipeline server logs")

if __name__ == "__main__":
    main()