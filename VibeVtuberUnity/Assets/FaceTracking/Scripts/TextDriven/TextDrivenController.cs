using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using Sirenix.OdinInspector;

namespace VibeVtuber.FaceTracking
{
    /// <summary>
    /// Listens on UDP port 11112 for text-driven lip-sync and emotion data
    /// from SpeechPlayer.py. In LateUpdate() it overrides the mouth-related
    /// Live2D parameters of Live2DFaceController, leaving head rotation and
    /// eye parameters untouched (still driven by FaceDataReceiver on 11111).
    ///
    /// After resetDelay seconds without incoming data the component stops
    /// overriding parameters, allowing face-capture to resume naturally.
    ///
    /// Setup:
    ///   1. Attach this component to the same GameObject as Live2DFaceController.
    ///   2. Configure mouthMappings to match your Live2D model's parameter IDs
    ///      (e.g. jawOpen → ParamMouthOpenY, mouthSmileLeft → ParamMouthForm).
    ///   3. Press Play — the component starts listening automatically.
    /// </summary>
    [RequireComponent(typeof(Live2DFaceController))]
    public class TextDrivenController : MonoBehaviour
    {
        [Title("Text-Driven Controller",
               "Receives lip-sync & emotion via UDP 11112 and overrides mouth params in LateUpdate()",
               TitleAlignments.Centered, HorizontalLine = true)]

        // ── Network ──────────────────────────────────────────────────────────

        [BoxGroup("Network")]
        [LabelText("UDP Port")]
        [Tooltip("Must match SpeechPlayer.UDP_PORT (default 11112)")]
        [SerializeField] private int port = 11112;

        [BoxGroup("Network")]
        [LabelText("Auto Start")]
        [SerializeField] private bool autoStart = true;

        // ── Timing ────────────────────────────────────────────────────────────

        [BoxGroup("Timing")]
        [LabelText("Reset Delay (s)")]
        [Tooltip("Seconds of silence before face-capture resumes control")]
        [SerializeField] private float resetDelay = 0.3f;

        // ── Parameter Mappings ────────────────────────────────────────────────

        [Title("Mouth Parameter Mappings",
               "Map incoming ARKit blendshape keys → Live2D parameter IDs for your model")]
        [InfoBox("Default values match the standard Live2D Cubism sample model.\n" +
                 "Adjust live2DParamId to match your specific model's parameters.",
                 InfoMessageType.Info)]
        [ListDrawerSettings(ShowIndexLabels = true, DraggableItems = true)]
        [SerializeField]
        private List<MouthParamMap> mouthMappings = new List<MouthParamMap>
        {
            // Lip-sync channels (driven by phoneme keyframes)
            new MouthParamMap { blendshapeKey = "jawOpen",         live2DParamId = "ParamMouthOpenY",  multiplier = 1f  },
            new MouthParamMap { blendshapeKey = "mouthFunnel",     live2DParamId = "ParamMouthForm",   multiplier = 0.5f },
            new MouthParamMap { blendshapeKey = "mouthPucker",     live2DParamId = "ParamMouthForm",   multiplier = -0.5f },

            // Emotion channels (driven by TextAnalyzer blendshapes)
            new MouthParamMap { blendshapeKey = "mouthSmileLeft",  live2DParamId = "ParamMouthForm",   multiplier = 0.5f },
            new MouthParamMap { blendshapeKey = "mouthSmileRight", live2DParamId = "ParamMouthForm",   multiplier = 0.5f },
            new MouthParamMap { blendshapeKey = "mouthFrownLeft",  live2DParamId = "ParamMouthForm",   multiplier = -0.5f },
            new MouthParamMap { blendshapeKey = "mouthFrownRight", live2DParamId = "ParamMouthForm",   multiplier = -0.5f },
        };

        // ── Status ────────────────────────────────────────────────────────────

        [FoldoutGroup("Status")]
        [LabelText("Overriding Mouth")]
        [ReadOnly]
        [SerializeField] private bool isOverriding = false;

        [FoldoutGroup("Status")]
        [LabelText("Last Message Type")]
        [ReadOnly]
        [SerializeField] private string lastMsgType = "-";

        [FoldoutGroup("Status")]
        [LabelText("Messages Received")]
        [ReadOnly]
        [SerializeField] private int totalMessages = 0;

        // ── Internals ─────────────────────────────────────────────────────────

        private Live2DFaceController faceController;
        private ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();
        private UdpClient udpClient;
        private Thread receiveThread;
        private bool isRunning = false;

        // Latest blendshapes to apply this frame (ARKit key → value)
        private Dictionary<string, float> pendingBlendshapes = new Dictionary<string, float>();
        // Accumulated per-Live2D-param contributions this frame
        private Dictionary<string, float> liveParamValues    = new Dictionary<string, float>();

        private float lastDataTime = -999f;

        // ARKit keys that this component cares about (determines which incoming
        // blendshapes to accept and which to pass through)
        private HashSet<string> watchedKeys;

        // ── Unity lifecycle ───────────────────────────────────────────────────

        private void OnEnable()
        {
            faceController = GetComponent<Live2DFaceController>();

            // Build the set of watched blendshape keys from mappings
            watchedKeys = new HashSet<string>();
            foreach (var m in mouthMappings)
            {
                if (!string.IsNullOrEmpty(m.blendshapeKey))
                    watchedKeys.Add(m.blendshapeKey);
            }

            if (autoStart)
                StartReceiving();
        }

        private void OnDisable() => StopReceiving();
        private void OnDestroy() => StopReceiving();

        // ── UDP Receive ───────────────────────────────────────────────────────

        [ButtonGroup]
        [Button("Start Receiving", ButtonSizes.Large)]
        [GUIColor(0.4f, 0.8f, 0.4f)]
        public void StartReceiving()
        {
            if (isRunning) return;
            try
            {
                udpClient = new UdpClient();
                udpClient.Client.SetSocketOption(
                    SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                udpClient.Client.Bind(new IPEndPoint(IPAddress.Any, port));
                udpClient.Client.ReceiveTimeout = 1000;

                isRunning = true;
                receiveThread = new Thread(ReceiveLoop) { IsBackground = true };
                receiveThread.Start();
                Debug.Log($"[TextDrivenController] Listening on UDP port {port}");
            }
            catch (Exception e)
            {
                Debug.LogError($"[TextDrivenController] Failed to start: {e.Message}");
                isRunning = false;
            }
        }

        [ButtonGroup]
        [Button("Stop Receiving", ButtonSizes.Large)]
        [GUIColor(0.8f, 0.4f, 0.4f)]
        public void StopReceiving()
        {
            if (!isRunning) return;
            isRunning = false;
            if (receiveThread != null && receiveThread.IsAlive)
                receiveThread.Join(1000);
            if (udpClient != null)
            {
                try { udpClient.Close(); udpClient.Dispose(); } catch { }
                udpClient = null;
            }
            while (messageQueue.TryDequeue(out _)) { }
        }

        private void ReceiveLoop()
        {
            IPEndPoint remote = new IPEndPoint(IPAddress.Any, 0);
            while (isRunning)
            {
                try
                {
                    byte[] data = udpClient.Receive(ref remote);
                    messageQueue.Enqueue(Encoding.UTF8.GetString(data));
                }
                catch (SocketException e)
                {
                    if (e.SocketErrorCode != SocketError.TimedOut && isRunning)
                        Debug.LogWarning($"[TextDrivenController] Socket error: {e.Message}");
                }
                catch (Exception e)
                {
                    if (isRunning)
                        Debug.LogError($"[TextDrivenController] Receive error: {e.Message}");
                }
            }
        }

        // ── LateUpdate: apply mouth overrides ─────────────────────────────────

        private void LateUpdate()
        {
            if (faceController == null) return;

            // Process all queued messages
            while (messageQueue.TryDequeue(out string json))
            {
                ProcessMessage(json);
                totalMessages++;
            }

            // Apply overrides only while data is fresh
            float timeSinceData = Time.time - lastDataTime;
            if (timeSinceData < resetDelay && pendingBlendshapes.Count > 0)
            {
                isOverriding = true;
                ApplyToLive2D();
            }
            else if (isOverriding)
            {
                // Transition: was overriding → now stopping. Push zeros so the
                // mouth doesn't freeze at the last non-zero keyframe value.
                isOverriding = false;
                ApplyZeros();
            }
        }

        private void ApplyToLive2D()
        {
            // Accumulate contributions per Live2D parameter
            liveParamValues.Clear();
            foreach (var mapping in mouthMappings)
            {
                if (string.IsNullOrEmpty(mapping.blendshapeKey) ||
                    string.IsNullOrEmpty(mapping.live2DParamId))
                    continue;

                if (!pendingBlendshapes.TryGetValue(mapping.blendshapeKey, out float bsVal))
                    continue;

                float contribution = bsVal * mapping.multiplier;
                if (liveParamValues.ContainsKey(mapping.live2DParamId))
                    liveParamValues[mapping.live2DParamId] += contribution;
                else
                    liveParamValues[mapping.live2DParamId] = contribution;
            }

            foreach (var kvp in liveParamValues)
            {
                faceController.SetParameter(kvp.Key, kvp.Value);
            }
        }

        private void ApplyZeros()
        {
            // Collect unique Live2D param IDs and set each to 0.
            var paramIds = new HashSet<string>();
            foreach (var m in mouthMappings)
                if (!string.IsNullOrEmpty(m.live2DParamId))
                    paramIds.Add(m.live2DParamId);
            foreach (var id in paramIds)
                faceController.SetParameter(id, 0f);
        }

        // ── Message parsing ───────────────────────────────────────────────────

        private void ProcessMessage(string json)
        {
            try
            {
                string msgType = ExtractStringField(json, "type");
                lastMsgType = msgType;

                if (msgType == "reset")
                {
                    // Explicitly zero all mouth params before releasing override,
                    // so the model doesn't freeze at the last non-zero value.
                    ApplyZeros();
                    pendingBlendshapes.Clear();
                    lastDataTime = -999f;
                    isOverriding = false;
                    return;
                }

                // For "lip_sync" and "text_emotion" messages: merge blendshapes
                var bs = ParseBlendshapes(json);
                if (bs != null && bs.Count > 0)
                {
                    foreach (var kvp in bs)
                    {
                        // Only accept keys that have a mapping configured
                        if (watchedKeys.Contains(kvp.Key))
                            pendingBlendshapes[kvp.Key] = kvp.Value;
                    }
                    lastDataTime = Time.time;
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[TextDrivenController] Parse error: {e.Message}");
            }
        }

        private static string ExtractStringField(string json, string fieldName)
        {
            int idx = json.IndexOf($"\"{fieldName}\":", StringComparison.Ordinal);
            if (idx < 0) return "";
            int qs = json.IndexOf('"', idx + fieldName.Length + 3);
            if (qs < 0) return "";
            int qe = json.IndexOf('"', qs + 1);
            if (qe < 0) return "";
            return json.Substring(qs + 1, qe - qs - 1);
        }

        private static Dictionary<string, float> ParseBlendshapes(string json)
        {
            var dict = new Dictionary<string, float>();
            int startIndex = json.IndexOf("\"blendshapes\":", StringComparison.Ordinal);
            if (startIndex < 0) return dict;

            int braceStart = json.IndexOf('{', startIndex);
            if (braceStart < 0) return dict;

            int braceCount = 1, endIndex = braceStart + 1;
            while (endIndex < json.Length && braceCount > 0)
            {
                if (json[endIndex] == '{') braceCount++;
                else if (json[endIndex] == '}') braceCount--;
                endIndex++;
            }
            if (braceCount != 0) return dict;

            string inner = json.Substring(braceStart + 1, endIndex - braceStart - 2);
            int pos = 0;
            while (pos < inner.Length)
            {
                while (pos < inner.Length && char.IsWhiteSpace(inner[pos])) pos++;
                if (pos >= inner.Length || inner[pos] != '"') { pos++; continue; }

                int ks = pos + 1;
                int ke = inner.IndexOf('"', ks);
                if (ke < 0) break;
                string key = inner.Substring(ks, ke - ks);

                int col = inner.IndexOf(':', ke);
                if (col < 0) break;
                int vs = col + 1;
                while (vs < inner.Length && char.IsWhiteSpace(inner[vs])) vs++;
                int ve = vs;
                while (ve < inner.Length && inner[ve] != ',' && inner[ve] != '}') ve++;

                string valStr = inner.Substring(vs, ve - vs).Trim();
                if (float.TryParse(valStr,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out float val))
                {
                    dict[key] = val;
                }
                pos = ve + 1;
            }
            return dict;
        }
    }

    /// <summary>
    /// Configures one ARKit blendshape key → Live2D parameter ID mapping
    /// for the TextDrivenController.
    /// </summary>
    [Serializable]
    public class MouthParamMap
    {
        [HorizontalGroup("Row", Width = 0.38f)]
        [LabelText("ARKit Key")]
        [Tooltip("Blendshape key received via UDP (e.g. 'jawOpen')")]
        public string blendshapeKey;

        [HorizontalGroup("Row", Width = 0.45f)]
        [LabelText("Live2D Param ID")]
        [Tooltip("Live2D parameter ID in your model (e.g. 'ParamMouthOpenY')")]
        public string live2DParamId;

        [HorizontalGroup("Row", Width = 0.17f)]
        [LabelText("×")]
        [Tooltip("Multiplier applied to the blendshape value before adding to the Live2D param")]
        public float multiplier = 1f;
    }
}
