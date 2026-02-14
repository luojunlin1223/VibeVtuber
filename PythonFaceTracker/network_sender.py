"""
UDP Network Sender
Serializes face tracking data to JSON and sends via UDP socket
"""

import socket
import json
import time
from typing import Dict, Optional


class NetworkSender:
    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        """
        Initialize UDP socket for sending face tracking data

        Args:
            host: Target IP address (default: localhost)
            port: Target port number
        """
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)  # Non-blocking mode

        print(f"[NetworkSender] Initialized UDP sender to {host}:{port}")

    def send_face_data(self, face_data: Optional[Dict]) -> bool:
        """
        Send face tracking data as JSON via UDP

        Args:
            face_data: Dictionary containing 'blendshapes' (52 ARKit parameters)
                      and 'head_rotation' dict (yaw/pitch/roll),
                      or None if no face detected.
                      Head rotation will be merged into blendshapes as
                      'headYaw', 'headPitch', 'headRoll' (total 55 parameters).

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Build message payload
            if face_data is None:
                message = {
                    "timestamp": time.time(),
                    "faceDetected": False,
                    "blendshapes": {}
                }
            else:
                # Merge head rotation into blendshapes dictionary (unified 55 parameters)
                blendshapes = face_data['blendshapes'].copy()
                head_rot = face_data['head_rotation']
                blendshapes['headYaw'] = head_rot['yaw']
                blendshapes['headPitch'] = head_rot['pitch']
                blendshapes['headRoll'] = head_rot['roll']

                message = {
                    "timestamp": time.time(),
                    "faceDetected": True,
                    "blendshapes": blendshapes
                }

            # Serialize to JSON
            json_data = json.dumps(message)

            # Send via UDP (fire-and-forget)
            self.socket.sendto(json_data.encode('utf-8'), (self.host, self.port))
            return True

        except Exception as e:
            print(f"[NetworkSender] Error sending data: {e}")
            return False

    def close(self):
        """Close the UDP socket"""
        self.socket.close()
        print("[NetworkSender] Socket closed")
