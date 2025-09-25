#!/usr/bin/env python3
"""
Test cuDNN installation by running a simple neural network operation.
"""

import torch
import torch.nn as nn

def test_cudnn():
    print("=== cuDNN Installation Test ===")

    # Basic checks
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        print(f"GPU name: {torch.cuda.get_device_name(0)}")

        # Check cuDNN
        print(f"cuDNN available: {torch.backends.cudnn.is_available()}")
        if torch.backends.cudnn.is_available():
            print(f"cuDNN version: {torch.backends.cudnn.version()}")
            print(f"cuDNN enabled: {torch.backends.cudnn.enabled}")
        else:
            print("❌ cuDNN NOT available")
            return False
    else:
        print("❌ CUDA not available")
        return False

    # Test actual cuDNN operation
    try:
        print("\n=== Testing cuDNN Operations ===")
        device = torch.device('cuda')

        # Create a simple conv layer (requires cuDNN)
        conv = nn.Conv1d(1, 1, kernel_size=3).to(device)
        x = torch.randn(1, 1, 10).to(device)

        # This operation requires cuDNN
        with torch.backends.cudnn.flags(enabled=True):
            y = conv(x)

        print("✅ Convolution operation successful!")
        print(f"Input shape: {x.shape}")
        print(f"Output shape: {y.shape}")

        return True

    except Exception as e:
        print(f"❌ cuDNN operation failed: {e}")
        return False

if __name__ == "__main__":
    success = test_cudnn()
    if success:
        print("\n🎉 cuDNN is properly installed and working!")
    else:
        print("\n💀 cuDNN installation has issues")