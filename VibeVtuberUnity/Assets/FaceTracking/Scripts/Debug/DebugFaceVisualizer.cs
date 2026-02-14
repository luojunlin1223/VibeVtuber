using UnityEngine;
using UnityEngine.UI;
using System.Text;
using System.Linq;

namespace VibeVtuber.FaceTracking
{
    /// <summary>
    /// Debug UI for visualizing face tracking data in real-time
    /// Displays connection status, FPS, latency, and blendshape values
    /// </summary>
    public class DebugFaceVisualizer : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private FaceDataReceiver dataReceiver;
        [SerializeField] private Canvas debugCanvas;

        [Header("UI Elements")]
        [SerializeField] private Text statusText;
        [SerializeField] private Text fpsText;
        [SerializeField] private Text latencyText;
        [SerializeField] private Text blendshapesText;
        [SerializeField] private Slider[] parameterSliders; // Optional: visual sliders for key parameters

        [Header("Settings")]
        [SerializeField] private KeyCode toggleKey = KeyCode.F1;
        [SerializeField] private bool startVisible = true;
        [SerializeField] private int maxBlendshapesToShow = 20;
        [SerializeField] private bool showAllBlendshapes = false;

        private FaceData lastData;
        private float lastDataTimestamp = 0f;
        private bool isVisible;

        // Priority blendshapes to always show (even if showAllBlendshapes is false)
        private readonly string[] priorityBlendshapes = new string[]
        {
            BlendshapeNames.EyeBlinkLeft,
            BlendshapeNames.EyeBlinkRight,
            BlendshapeNames.JawOpen,
            BlendshapeNames.MouthSmileLeft,
            BlendshapeNames.MouthSmileRight,
            BlendshapeNames.BrowInnerUp,
            BlendshapeNames.EyeLookUpLeft,
            BlendshapeNames.EyeLookDownLeft,
            BlendshapeNames.MouthFrownLeft,
            BlendshapeNames.MouthFrownRight
        };

        private void Start()
        {
            isVisible = startVisible;

            if (debugCanvas != null)
            {
                debugCanvas.gameObject.SetActive(isVisible);
            }

            if (dataReceiver != null)
            {
                dataReceiver.OnDataReceived.AddListener(OnFaceDataReceived);
            }
            else
            {
                Debug.LogWarning("[DebugFaceVisualizer] FaceDataReceiver not assigned!");
            }

            // Create UI if not assigned
            if (statusText == null || fpsText == null)
            {
                CreateDebugUI();
            }
        }

        private void OnDestroy()
        {
            if (dataReceiver != null)
            {
                dataReceiver.OnDataReceived.RemoveListener(OnFaceDataReceived);
            }
        }

        private void Update()
        {
            // Toggle visibility
            if (Input.GetKeyDown(toggleKey))
            {
                isVisible = !isVisible;
                if (debugCanvas != null)
                {
                    debugCanvas.gameObject.SetActive(isVisible);
                }
            }

            if (!isVisible) return;

            // Update UI
            UpdateStatusDisplay();
            UpdateBlendshapeDisplay();
        }

        private void OnFaceDataReceived(FaceData data)
        {
            lastData = data;
            lastDataTimestamp = Time.time;
        }

        private void UpdateStatusDisplay()
        {
            if (dataReceiver == null) return;

            // Connection status
            if (statusText != null)
            {
                string status = dataReceiver.IsReceiving ? "CONNECTED" : "WAITING FOR DATA";
                Color statusColor = dataReceiver.IsReceiving ? Color.green : Color.yellow;
                statusText.text = status;
                statusText.color = statusColor;
            }

            // FPS
            if (fpsText != null)
            {
                fpsText.text = $"FPS: {dataReceiver.CurrentFPS:F1}";
            }

            // Latency
            if (latencyText != null && lastData != null)
            {
                float latency = (Time.time - lastData.timestamp) * 1000f; // Convert to ms
                latencyText.text = $"Latency: {latency:F0}ms";

                // Color code latency
                if (latency < 50f)
                    latencyText.color = Color.green;
                else if (latency < 100f)
                    latencyText.color = Color.yellow;
                else
                    latencyText.color = Color.red;
            }
        }

        private void UpdateBlendshapeDisplay()
        {
            if (blendshapesText == null || lastData == null || lastData.blendshapes == null)
                return;

            StringBuilder sb = new StringBuilder();

            // Blendshapes
            sb.AppendLine("=== BLENDSHAPES ===");

            if (showAllBlendshapes)
            {
                // Show all blendshapes sorted by value (highest first)
                var sortedBlendshapes = lastData.blendshapes
                    .OrderByDescending(kv => kv.Value)
                    .Take(maxBlendshapesToShow);

                foreach (var kvp in sortedBlendshapes)
                {
                    sb.AppendLine($"{kvp.Key}: {kvp.Value:F3} {GetBar(kvp.Value)}");
                }
            }
            else
            {
                // Show only priority blendshapes
                foreach (string key in priorityBlendshapes)
                {
                    float value = lastData.GetBlendshape(key);
                    sb.AppendLine($"{key}: {value:F3} {GetBar(value)}");
                }
            }

            blendshapesText.text = sb.ToString();
        }

        /// <summary>
        /// Generate a visual bar for a value (0-1 range)
        /// </summary>
        private string GetBar(float value, int length = 10)
        {
            int filled = Mathf.RoundToInt(value * length);
            return new string('█', filled) + new string('░', length - filled);
        }

        /// <summary>
        /// Create debug UI programmatically if not assigned in inspector
        /// </summary>
        private void CreateDebugUI()
        {
            // Create canvas if needed
            if (debugCanvas == null)
            {
                GameObject canvasObj = new GameObject("DebugFaceVisualizerCanvas");
                debugCanvas = canvasObj.AddComponent<Canvas>();
                debugCanvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvasObj.AddComponent<CanvasScaler>();
                canvasObj.AddComponent<GraphicRaycaster>();
            }

            // Create panel
            GameObject panel = new GameObject("Panel");
            panel.transform.SetParent(debugCanvas.transform, false);
            Image panelImage = panel.AddComponent<Image>();
            panelImage.color = new Color(0, 0, 0, 0.7f);

            RectTransform panelRect = panel.GetComponent<RectTransform>();
            panelRect.anchorMin = new Vector2(0, 0);
            panelRect.anchorMax = new Vector2(0, 1);
            panelRect.pivot = new Vector2(0, 0.5f);
            panelRect.sizeDelta = new Vector2(400, 0);
            panelRect.anchoredPosition = new Vector2(10, 0);

            // Create text elements
            statusText = CreateText("StatusText", panel.transform, new Vector2(10, -30), 20);
            fpsText = CreateText("FPSText", panel.transform, new Vector2(10, -60), 16);
            latencyText = CreateText("LatencyText", panel.transform, new Vector2(10, -85), 16);
            blendshapesText = CreateText("BlendshapesText", panel.transform, new Vector2(10, -120), 12);

            blendshapesText.alignment = TextAnchor.UpperLeft;
            blendshapesText.GetComponent<RectTransform>().sizeDelta = new Vector2(380, 600);
        }

        private Text CreateText(string name, Transform parent, Vector2 position, int fontSize)
        {
            GameObject textObj = new GameObject(name);
            textObj.transform.SetParent(parent, false);

            Text text = textObj.AddComponent<Text>();
            text.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            text.fontSize = fontSize;
            text.color = Color.white;
            text.text = "";

            RectTransform rect = textObj.GetComponent<RectTransform>();
            rect.anchorMin = new Vector2(0, 1);
            rect.anchorMax = new Vector2(0, 1);
            rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = position;
            rect.sizeDelta = new Vector2(380, 30);

            return text;
        }

        private void OnValidate()
        {
            if (dataReceiver == null)
            {
                dataReceiver = FindObjectOfType<FaceDataReceiver>();
            }
        }
    }
}
