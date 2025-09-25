#!/usr/bin/env python3
"""
Test RTSP stream from Misty to verify audio is available.
"""

import ffmpeg
import sys
import time

def test_rtsp_stream(misty_ip):
    """Test if RTSP stream from Misty has audio."""
    rtsp_url = f"rtsp://{misty_ip}:1936/h264"
    print(f"🔍 Testing RTSP stream: {rtsp_url}")

    try:
        # Probe the stream to see what's available
        print("📊 Probing stream info...")
        probe = ffmpeg.probe(rtsp_url, rtsp_transport="tcp")

        print("\n📺 Stream Information:")
        print(f"Format: {probe['format']['format_name']}")
        print(f"Duration: {probe['format'].get('duration', 'N/A')}")

        print(f"\n🎬 Found {len(probe['streams'])} stream(s):")

        has_audio = False
        has_video = False

        for i, stream in enumerate(probe['streams']):
            codec_type = stream['codec_type']
            codec_name = stream['codec_name']
            print(f"  Stream {i}: {codec_type} ({codec_name})")

            if codec_type == 'audio':
                has_audio = True
                sample_rate = stream.get('sample_rate', 'N/A')
                channels = stream.get('channels', 'N/A')
                print(f"    📢 Sample rate: {sample_rate}Hz, Channels: {channels}")

            elif codec_type == 'video':
                has_video = True
                width = stream.get('width', 'N/A')
                height = stream.get('height', 'N/A')
                print(f"    📹 Resolution: {width}x{height}")

        print(f"\n✅ Stream Summary:")
        print(f"  📹 Video: {'Yes' if has_video else 'No'}")
        print(f"  📢 Audio: {'Yes' if has_audio else 'No'}")

        if not has_audio:
            print("\n⚠️  WARNING: No audio stream found!")
            print("   This explains why the pipeline integration fails.")
            print("   Misty's RTSP stream may only provide video.")
            return False

        # Try to capture a small sample of audio
        print(f"\n🎤 Testing audio capture (5 seconds)...")

        process = (
            ffmpeg
            .input(rtsp_url, rtsp_transport="tcp")
            .output("pipe:", format="s16le", acodec="pcm_s16le", ac=1, ar=16000, t=5)
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        # Read some data
        audio_data = process.stdout.read(1024)
        process.terminate()

        if audio_data:
            print(f"✅ Successfully captured {len(audio_data)} bytes of audio!")
            return True
        else:
            print("❌ No audio data received")
            return False

    except Exception as e:
        print(f"❌ Error testing RTSP stream: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_rtsp_stream.py <misty_ip>")
        print("Example: python test_rtsp_stream.py 192.168.0.137")
        return

    misty_ip = sys.argv[1]
    success = test_rtsp_stream(misty_ip)

    if not success:
        print("\n🔧 Suggestions:")
        print("  1. Make sure Misty's AV streaming is enabled")
        print("  2. Check if Misty has a microphone")
        print("  3. Try using a different audio source for testing")

if __name__ == "__main__":
    main()