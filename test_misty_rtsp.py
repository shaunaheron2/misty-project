#!/usr/bin/env python3
"""
Test Misty RTSP stream with proper AV streaming setup.
"""

import sys
import time
import subprocess

try:
    from mistyPy.Robot import Robot
    MISTY_AVAILABLE = True
except ImportError:
    MISTY_AVAILABLE = False
    print("❌ Misty SDK not available")

def test_misty_rtsp(misty_ip):
    """Test RTSP stream from Misty after enabling AV streaming."""
    if not MISTY_AVAILABLE:
        print("❌ Cannot test - Misty SDK not installed")
        return False

    print(f"🤖 Connecting to Misty at {misty_ip}...")
    robot = Robot(misty_ip)

    try:
        # Enable AV streaming service
        print("📡 Enabling AV streaming service...")
        stat = robot.get_av_streaming_service_enabled()
        if not stat.json().get("result", False):
            robot.enable_av_streaming_service()
            print("   ✅ AV streaming service enabled")
        else:
            print("   ✅ AV streaming service already enabled")

        # Stop any existing streaming
        robot.stop_av_streaming()
        time.sleep(0.5)

        # Start AV streaming
        print("▶️  Starting AV streaming...")
        robot.start_av_streaming(url="rtspd:1936", width=1920, height=1080, frameRate=30)
        time.sleep(2.0)  # Give it more time to start

        # Test RTSP URL
        rtsp_url = f"rtsp://{misty_ip}:1936/h264"
        print(f"🔍 Testing RTSP stream: {rtsp_url}")

        # Use ffprobe to check the stream
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-rtsp_transport', 'tcp',
            rtsp_url
        ]

        print("📊 Probing stream (this may take a few seconds)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode != 0:
            print(f"❌ ffprobe failed:")
            print(f"   stderr: {result.stderr}")
            return False

        # Parse JSON output
        import json
        try:
            data = json.loads(result.stdout)
            streams = data.get('streams', [])

            print(f"\n🎬 Found {len(streams)} stream(s):")

            has_audio = False
            has_video = False

            for i, stream in enumerate(streams):
                codec_type = stream.get('codec_type', 'unknown')
                codec_name = stream.get('codec_name', 'unknown')
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
                print("\n⚠️  CRITICAL: No audio stream found in Misty's RTSP!")
                print("   This explains the 'Broken pipe' error in your integration.")
                print("   The pipeline expects audio data, but Misty's RTSP only provides video.")

            return has_audio

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse ffprobe output: {e}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    finally:
        # Clean up
        try:
            robot.stop_av_streaming()
            print("🛑 Stopped AV streaming")
        except:
            pass

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_misty_rtsp.py <misty_ip>")
        print("Example: python test_misty_rtsp.py 192.168.0.137")
        return

    misty_ip = sys.argv[1]
    has_audio = test_misty_rtsp(misty_ip)

    if not has_audio:
        print(f"\n🔧 Next steps:")
        print(f"  1. Misty's RTSP stream likely only provides video")
        print(f"  2. You may need to use Misty's direct microphone API instead")
        print(f"  3. Consider using the working llm_based_human_robot_dialogue.py approach")
        print(f"  4. Check Misty documentation for audio capture methods")

if __name__ == "__main__":
    main()