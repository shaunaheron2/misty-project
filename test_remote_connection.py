#!/usr/bin/env python3
"""
Test script to verify remote connection to PC pipeline server.
Use this from your laptop to test the connection before Friday's demo.
"""

import socket
import time
import sys
import argparse

def test_pipeline_connection(server_ip, audio_in_port=12345, audio_out_port=12346, timeout=5):
    """
    Test connection to pipeline server on both audio ports.

    Args:
        server_ip: IP address of your PC running the pipeline
        audio_in_port: Port for audio input (default 12345)
        audio_out_port: Port for audio output (default 12346)
        timeout: Connection timeout in seconds
    """
    print(f"🔍 Testing connection to pipeline server at {server_ip}")
    print("=" * 50)

    results = {}

    # Test audio input port
    print(f"📥 Testing audio input port {audio_in_port}...")
    try:
        sock_in = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_in.settimeout(timeout)
        start_time = time.time()
        sock_in.connect((server_ip, audio_in_port))
        latency = (time.time() - start_time) * 1000
        sock_in.close()
        print(f"   ✅ Connected successfully! Latency: {latency:.1f}ms")
        results['audio_in'] = {'status': 'success', 'latency_ms': latency}
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        results['audio_in'] = {'status': 'failed', 'error': str(e)}

    # Test audio output port
    print(f"📤 Testing audio output port {audio_out_port}...")
    try:
        sock_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_out.settimeout(timeout)
        start_time = time.time()
        sock_out.connect((server_ip, audio_out_port))
        latency = (time.time() - start_time) * 1000
        sock_out.close()
        print(f"   ✅ Connected successfully! Latency: {latency:.1f}ms")
        results['audio_out'] = {'status': 'success', 'latency_ms': latency}
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        results['audio_out'] = {'status': 'failed', 'error': str(e)}

    # Summary
    print("\n📊 Connection Test Summary:")
    print("=" * 30)

    success_count = sum(1 for r in results.values() if r['status'] == 'success')

    if success_count == 2:
        avg_latency = (results['audio_in'].get('latency_ms', 0) +
                      results['audio_out'].get('latency_ms', 0)) / 2
        print(f"🎉 All connections successful!")
        print(f"📡 Average network latency: {avg_latency:.1f}ms")

        if avg_latency < 20:
            print("🚀 Excellent latency for robotics!")
        elif avg_latency < 50:
            print("✅ Good latency for demo")
        else:
            print("⚠️  Higher latency - check network connection")

    elif success_count == 1:
        print("⚠️  Partial connection - check firewall settings")
    else:
        print("❌ No connections successful")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Is the pipeline server running on your PC?")
        print("   2. Check firewall settings (allow ports 12345, 12346)")
        print("   3. Verify the IP address is correct")
        print("   4. Try: sudo ufw allow 12345 && sudo ufw allow 12346")

    return results

def get_server_ip_suggestions():
    """Provide suggestions for finding the server IP."""
    print("💡 How to find your PC's IP address:")
    print("   Linux/Mac: ip addr show | grep inet")
    print("   Windows: ipconfig")
    print("   Common ranges:")
    print("     - Home WiFi: 192.168.1.x or 192.168.0.x")
    print("     - Office: 10.x.x.x or 172.16-31.x.x")

def main():
    parser = argparse.ArgumentParser(description="Test connection to speech-to-speech pipeline server")
    parser.add_argument("server_ip", help="IP address of PC running the pipeline")
    parser.add_argument("--audio-in-port", type=int, default=12345, help="Audio input port (default: 12345)")
    parser.add_argument("--audio-out-port", type=int, default=12346, help="Audio output port (default: 12346)")
    parser.add_argument("--timeout", type=int, default=5, help="Connection timeout in seconds (default: 5)")

    if len(sys.argv) == 1:
        print("🤖 Remote Pipeline Connection Tester")
        print("=" * 40)
        print("Usage: python test_remote_connection.py <SERVER_IP>")
        print("Example: python test_remote_connection.py 192.168.1.100")
        print()
        get_server_ip_suggestions()
        return

    args = parser.parse_args()

    # Validate IP address format
    try:
        socket.inet_aton(args.server_ip)
    except socket.error:
        print(f"❌ Invalid IP address: {args.server_ip}")
        return

    # Run the test
    results = test_pipeline_connection(
        args.server_ip,
        args.audio_in_port,
        args.audio_out_port,
        args.timeout
    )

    # Exit code for scripting
    success_count = sum(1 for r in results.values() if r['status'] == 'success')
    sys.exit(0 if success_count == 2 else 1)

if __name__ == "__main__":
    main()