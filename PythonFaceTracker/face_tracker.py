"""
MediaPipe Face Landmarker with Blendshapes
Processes webcam frames and extracts facial tracking data
"""

import mediapipe as mp
import numpy as np
import cv2
from typing import Optional, Dict, Tuple


class FaceTracker:
    def __init__(self, model_path: str, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5, num_faces: int = 1):
        """
        Initialize MediaPipe Face Landmarker

        Args:
            model_path: Path to face_landmarker_v2_with_blendshapes.task
            min_detection_confidence: Minimum confidence for face detection
            min_tracking_confidence: Minimum confidence for face tracking
            num_faces: Maximum number of faces to track
        """
        self.model_path = model_path

        # MediaPipe Face Landmarker options
        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True
        )

        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self.frame_timestamp_ms = 0

        # Smoothing state (Exponential Moving Average)
        self.prev_blendshapes: Optional[Dict[str, float]] = None
        self.prev_head_rotation: Optional[Tuple[float, float, float]] = None

    def process_frame(self, frame: np.ndarray, alpha: float = 0.3) -> Optional[Dict]:
        """
        Process a single frame and extract face tracking data

        Args:
            frame: BGR image from webcam (OpenCV format)
            alpha: EMA smoothing factor (0.0 = no smoothing, 1.0 = no history)

        Returns:
            Dictionary with face tracking data or None if no face detected
        """
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Process with timestamp (required for VIDEO mode)
        self.frame_timestamp_ms += 33  # ~30fps
        results = self.landmarker.detect_for_video(mp_image, self.frame_timestamp_ms)

        # Check if face was detected
        if not results.face_blendshapes or len(results.face_blendshapes) == 0:
            return None

        # Extract blendshapes (first face only)
        blendshapes_raw = results.face_blendshapes[0]
        blendshapes = {bs.category_name: bs.score for bs in blendshapes_raw}

        # Extract head rotation from transformation matrix
        if results.facial_transformation_matrixes:
            matrix = results.facial_transformation_matrixes[0]
            head_rotation = self._matrix_to_euler(matrix)
        else:
            head_rotation = (0.0, 0.0, 0.0)

        # Apply EMA smoothing
        if self.prev_blendshapes is not None:
            blendshapes = self._smooth_dict(blendshapes, self.prev_blendshapes, alpha)
        if self.prev_head_rotation is not None:
            head_rotation = self._smooth_tuple(head_rotation, self.prev_head_rotation, alpha)

        self.prev_blendshapes = blendshapes
        self.prev_head_rotation = head_rotation

        return {
            'blendshapes': blendshapes,
            'head_rotation': {
                'yaw': head_rotation[0],
                'pitch': head_rotation[1],
                'roll': head_rotation[2]
            }
        }

    def _matrix_to_euler(self, matrix: np.ndarray) -> Tuple[float, float, float]:
        """
        Convert 4x4 transformation matrix to Euler angles (yaw, pitch, roll)

        Args:
            matrix: 4x4 transformation matrix from MediaPipe

        Returns:
            (yaw, pitch, roll) in degrees
        """
        # Extract rotation matrix (top-left 3x3)
        r = matrix[:3, :3]

        # Convert to Euler angles (YXZ convention)
        # https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
        sy = np.sqrt(r[0, 0]**2 + r[1, 0]**2)

        singular = sy < 1e-6

        if not singular:
            pitch = np.arctan2(-r[2, 0], sy)
            yaw = np.arctan2(r[1, 0], r[0, 0])
            roll = np.arctan2(r[2, 1], r[2, 2])
        else:
            pitch = np.arctan2(-r[2, 0], sy)
            yaw = np.arctan2(-r[0, 1], r[1, 1])
            roll = 0

        # Convert radians to degrees
        return (
            float(np.degrees(yaw)),
            float(np.degrees(pitch)),
            float(np.degrees(roll))
        )

    def _smooth_dict(self, current: Dict[str, float], previous: Dict[str, float],
                     alpha: float) -> Dict[str, float]:
        """Apply EMA smoothing to dictionary values"""
        return {
            key: alpha * current[key] + (1 - alpha) * previous.get(key, current[key])
            for key in current
        }

    def _smooth_tuple(self, current: Tuple[float, float, float],
                      previous: Tuple[float, float, float], alpha: float) -> Tuple[float, float, float]:
        """Apply EMA smoothing to tuple values"""
        return tuple(
            alpha * curr + (1 - alpha) * prev
            for curr, prev in zip(current, previous)
        )

    def reset_smoothing(self):
        """Reset smoothing state (useful when tracking is lost)"""
        self.prev_blendshapes = None
        self.prev_head_rotation = None

    def close(self):
        """Clean up resources"""
        self.landmarker.close()
