using System;
using System.Collections.Generic;
using UnityEngine;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework;
using Sirenix.OdinInspector;

namespace VibeVtuber.FaceTracking
{
    /// <summary>
    /// Maps MediaPipe face tracking data to Live2D Cubism model parameters
    /// Fully configurable in Inspector
    /// </summary>
    [RequireComponent(typeof(CubismModel))]
    public class Live2DFaceController : SerializedMonoBehaviour
    {
        [Title("Live2D Face Controller", "Maps MediaPipe face tracking data to Live2D Cubism model parameters", TitleAlignments.Centered, HorizontalLine = true)]

        [BoxGroup("Setup")]
        [LabelText("Face Data Receiver")]
        [Required("Face Data Receiver is required!")]
        [SerializeField] private FaceDataReceiver dataReceiver;

        [BoxGroup("Setup")]
        [LabelText("Global Smoothing")]
        [Range(0f, 1f)]
        [InfoBox("0 = Instant response, 1 = Very smooth (adds delay)", InfoMessageType.None)]
        [SerializeField] private float smoothingFactor = 0.3f;

        [Title("Parameter Mappings", "Configure how Python parameters map to Live2D parameters", TitleAlignments.Centered)]
        [InfoBox("💡 Special source names: 'headYaw', 'headPitch', 'headRoll' for head rotation\n" +
                 "💡 Add multiple source parameters to blend them together", InfoMessageType.Info)]
        [ListDrawerSettings(
            ShowIndexLabels = true,
            ListElementLabelName = "description",
            DraggableItems = true,
            ShowPaging = true,
            NumberOfItemsPerPage = 5,
            CustomAddFunction = "CreateNewMapping"
        )]
        [SerializeField] private List<ParameterMapping> parameterMappings = new List<ParameterMapping>();

        private ParameterMapping CreateNewMapping()
        {
            return new ParameterMapping();
        }

        [FoldoutGroup("Debug Options")]
        [LabelText("Log Parameter Updates")]
        [SerializeField] private bool logParameterUpdates = false;

        [FoldoutGroup("Debug Options")]
        [LabelText("Show Missing Parameters")]
        [SerializeField] private bool showMissingParameters = true;

        private CubismModel cubismModel;
        private CubismParameter[] parameters;
        private Dictionary<string, float> smoothedValues = new Dictionary<string, float>();

        private void Start()
        {
            // Get Live2D model component
            cubismModel = GetComponent<CubismModel>();
            if (cubismModel == null)
            {
                Debug.LogError("[Live2DFaceController] CubismModel component not found!");
                enabled = false;
                return;
            }

            parameters = cubismModel.Parameters;

            // Subscribe to face data events
            if (dataReceiver != null)
            {
                dataReceiver.OnDataReceived.AddListener(OnFaceDataReceived);
                Debug.Log("[Live2DFaceController] Subscribed to FaceDataReceiver");
            }
            else
            {
                Debug.LogWarning("[Live2DFaceController] FaceDataReceiver not assigned!");
            }

            // NOTE: Auto-initialization removed - configure Parameter Mappings manually in Inspector
            // You can right-click this component and select "Initialize Default Mappings" if needed

            // Log available parameters for debugging
            if (logParameterUpdates)
            {
                Debug.Log($"[Live2DFaceController] Available Live2D parameters ({parameters.Length}):");
                foreach (var param in parameters)
                {
                    Debug.Log($"  - {param.Id} (min: {param.MinimumValue}, max: {param.MaximumValue}, default: {param.DefaultValue})");
                }
            }
        }

        private void OnDestroy()
        {
            if (dataReceiver != null)
            {
                dataReceiver.OnDataReceived.RemoveListener(OnFaceDataReceived);
            }
        }

        /// <summary>
        /// Called when new face data is received
        /// </summary>
        private void OnFaceDataReceived(FaceData data)
        {
            if (!data.faceDetected)
            {
                return;
            }

            // Apply all configured parameter mappings
            foreach (var mapping in parameterMappings)
            {
                if (!mapping.enabled)
                    continue;

                ApplyParameterMapping(mapping, data);
            }
        }

        /// <summary>
        /// Get source value from FaceData
        /// All parameters (52 ARKit blendshapes + 3 head rotation) are stored in blendshapes dictionary
        /// Special source names: 'headYaw', 'headPitch', 'headRoll'
        /// </summary>
        private float GetSourceValue(string sourceName, FaceData data)
        {
            // All parameters unified in blendshapes dictionary
            return data.GetBlendshape(sourceName);
        }

        /// <summary>
        /// Apply a single parameter mapping: Source(s) (Python) → Target (Live2D)
        /// Supports special source names: 'headYaw', 'headPitch', 'headRoll'
        /// Supports single or multiple source parameters with blending
        /// </summary>
        private void ApplyParameterMapping(ParameterMapping mapping, FaceData data)
        {
            // Validate
            if (mapping.sourceParameters == null || mapping.sourceParameters.Count == 0 ||
                string.IsNullOrEmpty(mapping.live2DParameter))
                return;

            float value;

            // Single source parameter (simple one-to-one mapping)
            if (mapping.sourceParameters.Count == 1)
            {
                value = GetSourceValue(mapping.sourceParameters[0], data);
            }
            // Multiple source parameters (blend them together)
            else
            {
                List<float> sourceValues = new List<float>();
                foreach (string sourceName in mapping.sourceParameters)
                {
                    sourceValues.Add(GetSourceValue(sourceName, data));
                }
                value = CombineValues(sourceValues, mapping.combineMode);
            }

            // Apply invert if enabled
            if (mapping.invert)
            {
                value = 1.0f - value;
            }

            // Apply range remapping if enabled
            if (mapping.useRemapping)
            {
                // Normalize input to 0-1 range
                float t = Mathf.InverseLerp(mapping.inputMin, mapping.inputMax, value);

                // Apply smoothstep if enabled (creates smooth easing)
                if (mapping.useSmoothstep)
                {
                    t = Mathf.SmoothStep(0f, 1f, t);
                }

                // Map to output range
                value = Mathf.Lerp(mapping.outputMin, mapping.outputMax, t);
            }

            // Apply multiplier and offset
            float finalValue = value * mapping.multiplier + mapping.offset;

            // Clamp to range if enabled
            if (mapping.useClamp)
            {
                finalValue = Mathf.Clamp(finalValue, mapping.clampMin, mapping.clampMax);
            }

            // Apply smoothing if enabled
            if (mapping.useSmoothing)
            {
                string key = mapping.live2DParameter;
                if (!smoothedValues.ContainsKey(key))
                    smoothedValues[key] = finalValue;

                smoothedValues[key] = Mathf.Lerp(smoothedValues[key], finalValue, 1f - smoothingFactor);
                finalValue = smoothedValues[key];
            }

            // Set Live2D parameter
            SetParameter(mapping.live2DParameter, finalValue);
        }

        /// <summary>
        /// Combine multiple values according to the specified mode
        /// </summary>
        private float CombineValues(List<float> values, CombineMode mode)
        {
            if (values.Count == 0)
                return 0f;

            if (values.Count == 1)
                return values[0];

            switch (mode)
            {
                case CombineMode.None:
                    // Use only the first parameter, ignore others
                    return values[0];

                case CombineMode.Average:
                    float sum = 0f;
                    foreach (float v in values) sum += v;
                    return sum / values.Count;

                case CombineMode.Sum:
                    float total = 0f;
                    foreach (float v in values) total += v;
                    return total;

                case CombineMode.Max:
                    float max = values[0];
                    foreach (float v in values)
                        if (v > max) max = v;
                    return max;

                case CombineMode.Min:
                    float min = values[0];
                    foreach (float v in values)
                        if (v < min) min = v;
                    return min;

                case CombineMode.Difference:
                    if (values.Count >= 2)
                        return values[0] - values[1];
                    return values[0];

                default:
                    return values[0];
            }
        }

        /// <summary>
        /// Set a Live2D parameter value by name
        /// </summary>
        public void SetParameter(string paramId, float value)
        {
            if (string.IsNullOrEmpty(paramId))
                return;

            CubismParameter param = Array.Find(parameters, p => p.Id == paramId);
            if (param != null)
            {
                // Clamp to parameter's min/max range
                value = Mathf.Clamp(value, param.MinimumValue, param.MaximumValue);
                param.Value = value;

                if (logParameterUpdates)
                {
                    Debug.Log($"[Live2D] {paramId} = {value:F3}");
                }
            }
            else if (showMissingParameters)
            {
                Debug.LogWarning($"[Live2D] Parameter not found: {paramId}");
            }
        }

        /// <summary>
        /// Get a Live2D parameter value by name
        /// </summary>
        /// <param name="paramId">Parameter ID (e.g., "ParamEyeLOpen")</param>
        /// <returns>Current parameter value, or -1 if not found</returns>
        public float GetParameter(string paramId)
        {
            if (string.IsNullOrEmpty(paramId))
                return -1f;

            CubismParameter param = Array.Find(parameters, p => p.Id == paramId);
            if (param != null)
            {
                return param.Value;
            }

            return -1f; // Parameter not found
        }

        /// <summary>
        /// Initialize default parameter mappings (standard Live2D parameters)
        /// Right-click this component and select this option if you want default mappings
        /// </summary>
        [ContextMenu("Initialize Default Mappings")]
        public void InitializeDefaultMappings()
        {
            parameterMappings = new List<ParameterMapping>
            {
                // === Head Rotation === (special source names: headYaw, headPitch, headRoll)
                new ParameterMapping("headYaw", "ParamAngleX", 1f, -30f, 30f),
                new ParameterMapping("headPitch", "ParamAngleY", 1f, -30f, 30f),
                new ParameterMapping("headRoll", "ParamAngleZ", 1f, -30f, 30f),

                // === Eye Blinks === (invert: MediaPipe 1=closed, Live2D 1=open)
                new ParameterMapping("eyeBlinkLeft", "ParamEyeLOpen", true),
                new ParameterMapping("eyeBlinkRight", "ParamEyeROpen", true),

                // === Jaw ===
                new ParameterMapping("jawOpen", "ParamMouthOpenY"),

                // === Mouth Smile === (average left + right)
                new ParameterMapping(
                    new List<string> { "mouthSmileLeft", "mouthSmileRight" },
                    "ParamMouthForm",
                    CombineMode.Average
                ),

                // === Eyebrows ===
                new ParameterMapping("browInnerUp", "ParamBrowLY"),
                new ParameterMapping("browInnerUp", "ParamBrowRY"),
            };

            Debug.Log("[Live2DFaceController] Initialized default parameter mappings (with multi-parameter blending support)");
        }

        // Editor helper
        private void OnValidate()
        {
            if (dataReceiver == null)
            {
                dataReceiver = FindObjectOfType<FaceDataReceiver>();
            }
        }

        // Context menu helper to log all available Live2D parameters
        [ContextMenu("Log All Live2D Parameters")]
        private void LogAllParameters()
        {
            if (cubismModel == null)
                cubismModel = GetComponent<CubismModel>();

            if (cubismModel != null)
            {
                parameters = cubismModel.Parameters;
                Debug.Log($"=== Live2D Parameters ({parameters.Length}) ===");
                foreach (var param in parameters)
                {
                    Debug.Log($"{param.Id} | min: {param.MinimumValue} | max: {param.MaximumValue} | default: {param.DefaultValue}");
                }
            }
        }

        // Context menu helper to log all available MediaPipe blendshapes
        [ContextMenu("Log All MediaPipe Blendshapes")]
        private void LogAllBlendshapes()
        {
            Debug.Log("=== MediaPipe ARKit Blendshapes (52 total) ===");
            var blendshapeNames = typeof(BlendshapeNames).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            foreach (var field in blendshapeNames)
            {
                Debug.Log($"- {field.GetValue(null)}");
            }
        }
    }

    /// <summary>
    /// Parameter mapping: Source Parameter(s) (Python) → Target Parameter (Live2D)
    /// Supports single parameter or multiple parameters with blending
    /// </summary>
    [Serializable]
    [HideLabel]
    public class ParameterMapping
    {
        // Basic Info
        [HorizontalGroup("Header", Width = 0.7f)]
        [LabelText("Description")]
        [Tooltip("Description (optional)")]
        public string description;

        [HorizontalGroup("Header", Width = 0.3f)]
        [LabelText("Enabled")]
        [Tooltip("Enable/disable this mapping")]
        public bool enabled = true;

        // Source and Target
        [BoxGroup("Mapping", ShowLabel = false)]
        [LabelText("Source Parameters (Python)")]
        [Tooltip("Add multiple parameters to blend them together")]
        [InfoBox("Special names: 'headYaw', 'headPitch', 'headRoll'", InfoMessageType.None)]
        public List<string> sourceParameters = new List<string>();

        [BoxGroup("Mapping")]
        [LabelText("Target Live2D Parameter")]
        [Tooltip("Target Live2D parameter name (e.g., 'ParamEyeLOpen', 'ParamMouthOpenY')")]
        public string live2DParameter;

        [BoxGroup("Mapping")]
        [LabelText("Combine Mode")]
        [Tooltip("How to combine multiple source parameters (only used if sourceParameters has 2+ items)")]
        [ShowIf("@sourceParameters.Count > 1")]
        public CombineMode combineMode = CombineMode.Average;

        // Adjustments (Foldout)
        [FoldoutGroup("Adjustments")]
        [LabelText("Invert (1.0 - value)")]
        [Tooltip("Invert value (1.0 - value), useful for eye blinks")]
        public bool invert = false;

        [FoldoutGroup("Adjustments")]
        [LabelText("Multiplier")]
        [Tooltip("Multiply the value (negative values also invert)")]
        public float multiplier = 1f;

        [FoldoutGroup("Adjustments")]
        [LabelText("Offset")]
        [Tooltip("Add to the value")]
        public float offset = 0f;

        // Range Remapping
        [FoldoutGroup("Range Remapping")]
        [LabelText("Enable Range Remapping")]
        [Tooltip("Map input range to output range (useful for normalizing values)")]
        public bool useRemapping = false;

        [FoldoutGroup("Range Remapping")]
        [HorizontalGroup("Range Remapping/Input")]
        [LabelText("Input Min")]
        [Tooltip("Minimum expected input value from MediaPipe")]
        [ShowIf("useRemapping")]
        public float inputMin = 0f;

        [FoldoutGroup("Range Remapping")]
        [HorizontalGroup("Range Remapping/Input")]
        [LabelText("Input Max")]
        [Tooltip("Maximum expected input value from MediaPipe")]
        [ShowIf("useRemapping")]
        public float inputMax = 1f;

        [FoldoutGroup("Range Remapping")]
        [HorizontalGroup("Range Remapping/Output")]
        [LabelText("Output Min")]
        [Tooltip("Minimum output value to Live2D")]
        [ShowIf("useRemapping")]
        public float outputMin = 0f;

        [FoldoutGroup("Range Remapping")]
        [HorizontalGroup("Range Remapping/Output")]
        [LabelText("Output Max")]
        [Tooltip("Maximum output value to Live2D")]
        [ShowIf("useRemapping")]
        public float outputMax = 1f;

        [FoldoutGroup("Range Remapping")]
        [LabelText("Use Smoothstep")]
        [Tooltip("Apply smoothstep interpolation (creates smooth acceleration/deceleration)")]
        [ShowIf("useRemapping")]
        public bool useSmoothstep = false;

        // Clamping
        [FoldoutGroup("Clamping")]
        [LabelText("Enable Clamping")]
        [Tooltip("Clamp final value to min/max range")]
        public bool useClamp = true;

        [FoldoutGroup("Clamping")]
        [HorizontalGroup("Clamping/Range")]
        [LabelText("Min")]
        [Tooltip("Minimum clamped value")]
        [ShowIf("useClamp")]
        public float clampMin = 0f;

        [FoldoutGroup("Clamping")]
        [HorizontalGroup("Clamping/Range")]
        [LabelText("Max")]
        [Tooltip("Maximum clamped value")]
        [ShowIf("useClamp")]
        public float clampMax = 1f;

        // Temporal Smoothing (Frame-to-Frame)
        [FoldoutGroup("Temporal Smoothing")]
        [LabelText("Use Temporal Smoothing")]
        [Tooltip("Apply frame-to-frame smoothing to reduce jitter (Lerp between frames)")]
        public bool useSmoothing = true;

        // Default constructor
        public ParameterMapping() { }

        // Simple single-parameter constructor
        public ParameterMapping(string source, string target, bool invertValue = false)
        {
            description = $"{source} → {target}";
            sourceParameters = new List<string> { source };
            live2DParameter = target;
            invert = invertValue;
        }

        // Multi-parameter constructor
        public ParameterMapping(List<string> sources, string target, CombineMode mode = CombineMode.Average)
        {
            description = $"{string.Join("+", sources)} → {target}";
            sourceParameters = new List<string>(sources);
            live2DParameter = target;
            combineMode = mode;
        }

        // Constructor with multiplier (for head rotation)
        public ParameterMapping(string source, string target, float mult, float clampMinValue = -30f, float clampMaxValue = 30f)
        {
            description = $"{source} → {target}";
            sourceParameters = new List<string> { source };
            live2DParameter = target;
            multiplier = mult;
            clampMin = clampMinValue;
            clampMax = clampMaxValue;
        }

        // Constructor with range remapping
        public ParameterMapping(string source, string target, float inMin, float inMax, float outMin, float outMax, bool smoothstep = false)
        {
            description = $"{source} → {target} (remapped)";
            sourceParameters = new List<string> { source };
            live2DParameter = target;
            useRemapping = true;
            inputMin = inMin;
            inputMax = inMax;
            outputMin = outMin;
            outputMax = outMax;
            useSmoothstep = smoothstep;
        }
    }

    /// <summary>
    /// How to combine multiple source parameters into one value
    /// </summary>
    public enum CombineMode
    {
        [Tooltip("Use only the first parameter (no blending)")]
        None,

        [Tooltip("Average all parameter values (sum / count)")]
        Average,

        [Tooltip("Sum all parameter values (add together)")]
        Sum,

        [Tooltip("Use maximum value")]
        Max,

        [Tooltip("Use minimum value")]
        Min,

        [Tooltip("Difference (first - second)")]
        Difference
    }

}
