"""
Test script to verify headYaw/Pitch/Roll are sent to Unity correctly
Run this to test if Unity receives head rotation parameters
"""

import socket
import json
import time

def send_test_data():
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Test message with headYaw/Pitch/Roll in blendshapes
    message = {
        "timestamp": time.time(),
        "faceDetected": True,
        "blendshapes": {
            # Head rotation (should show in Unity Inspector)
            "headYaw": 25.0,
            "headPitch": -15.0,
            "headRoll": 5.0,

            # Some example blendshapes
            "jawOpen": 0.5,
            "eyeBlinkLeft": 0.2,
            "eyeBlinkRight": 0.3,
            "mouthSmileLeft": 0.6,
            "mouthSmileRight": 0.7
        }
    }

    # Convert to JSON
    json_data = json.dumps(message, indent=2)

    print("=" * 60)
    print("Test: Sending Head Rotation Data to Unity")
    print("=" * 60)
    print(f"\nJSON being sent:\n{json_data}\n")
    print("=" * 60)
    print("Expected Unity Inspector values:")
    print("  Head Yaw:   25.0°")
    print("  Head Pitch: -15.0°")
    print("  Head Roll:  5.0°")
    print("  Jaw Open:   0.5")
    print("=" * 60)

    # Send to Unity (localhost:11111)
    sock.sendto(json_data.encode('utf-8'), ('127.0.0.1', 11111))

    print("\n✅ Data sent to Unity (127.0.0.1:11111)")
    print("\nCheck Unity Inspector:")
    print("  1. Open FaceDataReceiver GameObject")
    print("  2. Look at 'Head Rotation Parameters' section")
    print("  3. Values should update to match expected values above")
    print("\nIf values are still 0:")
    print("  - Enable 'Log Blendshape Parsing' in Unity Inspector")
    print("  - Check Unity Console for parsing errors")
    print("  - See DEBUG_HEAD_ROTATION.md for troubleshooting")
    print("=" * 60)

    sock.close()

if __name__ == "__main__":
    try:
        send_test_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure Unity is running and FaceDataReceiver is active")
