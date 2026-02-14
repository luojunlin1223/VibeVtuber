using System;
using System.Collections.Generic;
using UnityEngine;

namespace VibeVtuber.FaceTracking
{
    /// <summary>
    /// Data structure for face tracking information received from MediaPipe
    /// Matches JSON format sent from Python face tracker
    /// </summary>
    [Serializable]
    public class FaceData
    {
        public float timestamp;
        public bool faceDetected;

        // All parameters stored in blendshapes dictionary (52 ARKit + 3 head rotation = 55 total)
        // Head rotation: "headYaw", "headPitch", "headRoll"
        public Dictionary<string, float> blendshapes;

        /// <summary>
        /// Get a blendshape value by name, returns 0 if not found
        /// </summary>
        public float GetBlendshape(string name)
        {
            if (blendshapes != null && blendshapes.TryGetValue(name, out float value))
            {
                return value;
            }
            return 0f;
        }

        /// <summary>
        /// Check if a specific blendshape exists in the data
        /// </summary>
        public bool HasBlendshape(string name)
        {
            return blendshapes != null && blendshapes.ContainsKey(name);
        }
    }

    /// <summary>
    /// Common ARKit blendshape names for easy reference
    /// </summary>
    public static class BlendshapeNames
    {
        // Eye blinks
        public const string EyeBlinkLeft = "eyeBlinkLeft";
        public const string EyeBlinkRight = "eyeBlinkRight";

        // Eye look
        public const string EyeLookUpLeft = "eyeLookUpLeft";
        public const string EyeLookUpRight = "eyeLookUpRight";
        public const string EyeLookDownLeft = "eyeLookDownLeft";
        public const string EyeLookDownRight = "eyeLookDownRight";
        public const string EyeLookInLeft = "eyeLookInLeft";
        public const string EyeLookInRight = "eyeLookInRight";
        public const string EyeLookOutLeft = "eyeLookOutLeft";
        public const string EyeLookOutRight = "eyeLookOutRight";

        // Eye squint/wide
        public const string EyeSquintLeft = "eyeSquintLeft";
        public const string EyeSquintRight = "eyeSquintRight";
        public const string EyeWideLeft = "eyeWideLeft";
        public const string EyeWideRight = "eyeWideRight";

        // Eyebrows
        public const string BrowDownLeft = "browDownLeft";
        public const string BrowDownRight = "browDownRight";
        public const string BrowInnerUp = "browInnerUp";
        public const string BrowOuterUpLeft = "browOuterUpLeft";
        public const string BrowOuterUpRight = "browOuterUpRight";

        // Jaw
        public const string JawOpen = "jawOpen";
        public const string JawForward = "jawForward";
        public const string JawLeft = "jawLeft";
        public const string JawRight = "jawRight";

        // Mouth
        public const string MouthClose = "mouthClose";
        public const string MouthFunnel = "mouthFunnel";
        public const string MouthPucker = "mouthPucker";
        public const string MouthLeft = "mouthLeft";
        public const string MouthRight = "mouthRight";
        public const string MouthSmileLeft = "mouthSmileLeft";
        public const string MouthSmileRight = "mouthSmileRight";
        public const string MouthFrownLeft = "mouthFrownLeft";
        public const string MouthFrownRight = "mouthFrownRight";
        public const string MouthDimpleLeft = "mouthDimpleLeft";
        public const string MouthDimpleRight = "mouthDimpleRight";
        public const string MouthStretchLeft = "mouthStretchLeft";
        public const string MouthStretchRight = "mouthStretchRight";
        public const string MouthRollLower = "mouthRollLower";
        public const string MouthRollUpper = "mouthRollUpper";
        public const string MouthShrugLower = "mouthShrugLower";
        public const string MouthShrugUpper = "mouthShrugUpper";
        public const string MouthPressLeft = "mouthPressLeft";
        public const string MouthPressRight = "mouthPressRight";
        public const string MouthLowerDownLeft = "mouthLowerDownLeft";
        public const string MouthLowerDownRight = "mouthLowerDownRight";
        public const string MouthUpperUpLeft = "mouthUpperUpLeft";
        public const string MouthUpperUpRight = "mouthUpperUpRight";

        // Nose
        public const string NoseSneerLeft = "noseSneerLeft";
        public const string NoseSneerRight = "noseSneerRight";

        // Cheek
        public const string CheekPuff = "cheekPuff";
        public const string CheekSquintLeft = "cheekSquintLeft";
        public const string CheekSquintRight = "cheekSquintRight";

        // Tongue
        public const string TongueOut = "tongueOut";
    }
}
