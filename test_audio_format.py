#!/usr/bin/env python3
"""
Test audio format from captured Misty files to ensure compatibility with pipeline.
"""

import wave
import sys
from pathlib import Path

def test_audio_format(audio_file_path):
    """Test audio file format and properties."""
    try:
        with wave.open(str(audio_file_path), 'rb') as wav_file:
            # Get audio parameters
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            duration = frames / sample_rate

            print(f"Audio File: {audio_file_path}")
            print(f"Sample Rate: {sample_rate} Hz")
            print(f"Channels: {channels}")
            print(f"Sample Width: {sample_width} bytes ({sample_width * 8} bits)")
            print(f"Frames: {frames}")
            print(f"Duration: {duration:.2f} seconds")
            print(f"File Size: {audio_file_path.stat().st_size} bytes")

            # Check if format matches pipeline expectations
            expected_sample_rate = 16000
            expected_channels = 1
            expected_sample_width = 2  # 16-bit = 2 bytes

            print(f"\nFormat Check:")
            print(f"Sample Rate: {'✓' if sample_rate == expected_sample_rate else '✗'} (expected {expected_sample_rate})")
            print(f"Channels: {'✓' if channels == expected_channels else '✗'} (expected {expected_channels})")
            print(f"Sample Width: {'✓' if sample_width == expected_sample_width else '✗'} (expected {expected_sample_width})")

            # Read a small sample to check data
            raw_data = wav_file.readframes(min(1000, frames))
            print(f"Sample Data: {len(raw_data)} bytes read")

            if len(raw_data) > 0:
                print(f"First few bytes: {raw_data[:20].hex()}")
                return True
            else:
                print("No audio data found in file!")
                return False

    except Exception as e:
        print(f"Error reading audio file: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
        if audio_file.exists():
            test_audio_format(audio_file)
        else:
            print(f"File not found: {audio_file}")
    else:
        # Test all captured audio files
        audio_dir = Path("./audio_capture")
        if audio_dir.exists():
            audio_files = list(audio_dir.glob("*.wav"))
            if audio_files:
                print(f"Testing {len(audio_files)} audio files:")
                for audio_file in sorted(audio_files)[-3:]:  # Test last 3 files
                    print("=" * 50)
                    test_audio_format(audio_file)
                    print()
            else:
                print("No audio files found in ./audio_capture/")
        else:
            print("No audio_capture directory found")
            print("Usage: python test_audio_format.py [audio_file.wav]")

if __name__ == "__main__":
    main()