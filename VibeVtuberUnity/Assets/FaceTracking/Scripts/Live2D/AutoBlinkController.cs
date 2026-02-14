using System.Collections;
using UnityEngine;
using Sirenix.OdinInspector;

namespace VibeVtuber.FaceTracking
{
    /// <summary>
    /// 自动眨眼控制器
    /// 让 Live2D 角色定期自动眨眼，可配置频率、随机性和眨眼参数
    /// </summary>
    public class AutoBlinkController : SerializedMonoBehaviour
    {
        [Title("自动眨眼控制器 (Auto Blink Controller)", "让角色像真人一样自然眨眼", TitleAlignments.Centered, HorizontalLine = true)]

        // ========== 基础设置 ==========
        [BoxGroup("基础设置")]
        [LabelText("启用自动眨眼")]
        [Tooltip("勾选后角色会自动眨眼")]
        public bool enableAutoBlink = true;

        [BoxGroup("基础设置")]
        [LabelText("双眼同步")]
        [Tooltip("勾选：两只眼睛同时眨 | 取消：左右眼独立眨眼")]
        public bool syncBothEyes = true;

        [BoxGroup("基础设置")]
        [LabelText("覆盖面部追踪")]
        [Tooltip("勾选后会覆盖 FaceDataReceiver 的眨眼数据（强制使用自动眨眼）")]
        public bool overrideFaceTracking = false;

        // ========== Live2D 参数配置 ==========
        [FoldoutGroup("Live2D 参数配置")]
        [LabelText("左眼参数名 (Left Eye)")]
        [Tooltip("Live2D 左眼睁开程度参数名称，如 'ParamEyeLOpen'")]
        [InfoBox("常见参数名: ParamEyeLOpen, ParamEyeL_Open, EyeOpenL", InfoMessageType.None)]
        public string leftEyeParameter = "ParamEyeLOpen";

        [FoldoutGroup("Live2D 参数配置")]
        [LabelText("右眼参数名 (Right Eye)")]
        [Tooltip("Live2D 右眼睁开程度参数名称，如 'ParamEyeROpen'")]
        public string rightEyeParameter = "ParamEyeROpen";

        [FoldoutGroup("Live2D 参数配置")]
        [LabelText("睁眼值 (Open)")]
        [Tooltip("眼睛完全睁开时的参数值")]
        [Range(0f, 1f)]
        public float eyeOpenValue = 1.0f;

        [FoldoutGroup("Live2D 参数配置")]
        [LabelText("闭眼值 (Closed)")]
        [Tooltip("眼睛完全闭合时的参数值")]
        [Range(0f, 1f)]
        public float eyeClosedValue = 0.0f;

        // ========== 眨眼频率设置 ==========
        [FoldoutGroup("眨眼频率设置")]
        [LabelText("基础间隔 (秒)")]
        [Tooltip("眨眼的基础时间间隔（秒）")]
        [Range(1f, 10f)]
        [SuffixLabel("秒", Overlay = true)]
        public float baseBlinkInterval = 3.5f;

        [FoldoutGroup("眨眼频率设置")]
        [LabelText("随机范围 (±)")]
        [Tooltip("在基础间隔上添加随机偏移量（秒）")]
        [Range(0f, 5f)]
        [SuffixLabel("秒", Overlay = true)]
        public float randomRange = 1.5f;

        [FoldoutGroup("眨眼频率设置")]
        [HorizontalGroup("眨眼频率设置/Preview")]
        [LabelText("实际间隔范围")]
        [ReadOnly]
        [ShowInInspector]
        private string IntervalRangePreview => $"{baseBlinkInterval - randomRange:F1}s ~ {baseBlinkInterval + randomRange:F1}s";

        // ========== 眨眼动画设置 ==========
        [FoldoutGroup("眨眼动画设置")]
        [LabelText("眨眼持续时间 (秒)")]
        [Tooltip("单次眨眼从闭合到睁开的总时长（秒）")]
        [Range(0.05f, 0.5f)]
        [SuffixLabel("秒", Overlay = true)]
        public float blinkDuration = 0.15f;

        [FoldoutGroup("眨眼动画设置")]
        [LabelText("闭眼速度系数")]
        [Tooltip("闭眼阶段占总时长的比例 | 0.5=对称，<0.5=闭眼快睁眼慢，>0.5=闭眼慢睁眼快")]
        [Range(0.2f, 0.8f)]
        public float closeRatio = 0.4f;

        [FoldoutGroup("眨眼动画设置")]
        [LabelText("眨眼曲线")]
        [Tooltip("眨眼动画曲线 | X轴=时间(0-1)，Y轴=眼睛闭合程度(0=睁开，1=闭合)")]
        public AnimationCurve blinkCurve = AnimationCurve.EaseInOut(0f, 0f, 1f, 1f);

        [FoldoutGroup("眨眼动画设置")]
        [LabelText("眨眼强度")]
        [Tooltip("眨眼的强度 | 1.0=完全闭眼，0.5=半闭眼")]
        [Range(0.5f, 1f)]
        [ProgressBar(0.5, 1, ColorGetter = "GetBlinkStrengthColor")]
        public float blinkStrength = 1.0f;

        // ========== 高级设置 ==========
        [FoldoutGroup("高级设置")]
        [LabelText("左眼独立间隔 (秒)")]
        [ShowIf("@!syncBothEyes")]
        [Range(1f, 10f)]
        [SuffixLabel("秒", Overlay = true)]
        public float leftEyeInterval = 3.0f;

        [FoldoutGroup("高级设置")]
        [LabelText("右眼独立间隔 (秒)")]
        [ShowIf("@!syncBothEyes")]
        [Range(1f, 10f)]
        [SuffixLabel("秒", Overlay = true)]
        public float rightEyeInterval = 3.2f;

        [FoldoutGroup("高级设置")]
        [LabelText("左眼随机范围 (±)")]
        [ShowIf("@!syncBothEyes")]
        [Range(0f, 3f)]
        [SuffixLabel("秒", Overlay = true)]
        public float leftEyeRandomRange = 1.0f;

        [FoldoutGroup("高级设置")]
        [LabelText("右眼随机范围 (±)")]
        [ShowIf("@!syncBothEyes")]
        [Range(0f, 3f)]
        [SuffixLabel("秒", Overlay = true)]
        public float rightEyeRandomRange = 1.0f;

        // ========== 状态监控 ==========
        [FoldoutGroup("状态监控", false)]
        [LabelText("运行状态")]
        [ReadOnly]
        [ShowInInspector]
        private string Status => enableAutoBlink ? (isBlinking ? "正在眨眼 🎬" : "等待中 ⏱️") : "已禁用 ⏸️";

        [FoldoutGroup("状态监控")]
        [LabelText("下次眨眼倒计时")]
        [ReadOnly]
        [ShowInInspector]
        [ProgressBar(0, "nextBlinkTime", ColorGetter = "GetCountdownColor")]
        private float countdownTimer = 0f;

        [FoldoutGroup("状态监控")]
        [LabelText("左眼当前值")]
        [ReadOnly]
        [ShowInInspector]
        [ProgressBar(0, 1)]
        private float leftEyeCurrentValue = 1f;

        [FoldoutGroup("状态监控")]
        [LabelText("右眼当前值")]
        [ReadOnly]
        [ShowInInspector]
        [ProgressBar(0, 1)]
        private float rightEyeCurrentValue = 1f;

        [FoldoutGroup("状态监控")]
        [LabelText("总眨眼次数")]
        [ReadOnly]
        [ShowInInspector]
        private int totalBlinks = 0;

        // ========== 内部变量 ==========
        private Live2DFaceController faceController;
        private Coroutine blinkCoroutine;
        private Coroutine leftEyeCoroutine;
        private Coroutine rightEyeCoroutine;
        private bool isBlinking = false;
        private float nextBlinkTime = 0f;
        private float elapsedTime = 0f;
        private bool shouldAutoStart = false; // 延迟自动启动标志

        // ========== Unity 生命周期 ==========
        private void Awake()
        {
            // 初始化时查找 Live2DFaceController
            if (faceController == null)
            {
                faceController = GetComponent<Live2DFaceController>();
                if (faceController == null)
                {
                    faceController = FindObjectOfType<Live2DFaceController>();
                }
            }
        }

        private void Start()
        {
            // 标记需要自动启动（延迟到 Update 中检查条件）
            if (enableAutoBlink)
            {
                shouldAutoStart = true;
            }
        }

        private void OnEnable()
        {
            // 组件重新启用时，如果之前是启用状态，则恢复
            if (enableAutoBlink && blinkCoroutine == null && leftEyeCoroutine == null && rightEyeCoroutine == null)
            {
                shouldAutoStart = true;
            }
        }

        private void OnDisable()
        {
            StopBlinking();
            shouldAutoStart = false;
        }

        private void Update()
        {
            // 延迟自动启动：等待 Live2D 初始化完成
            if (shouldAutoStart && CanStartBlinking())
            {
                StartBlinking();
                shouldAutoStart = false;
                Debug.Log("[AutoBlinkController] Live2D 初始化完成，自动启动眨眼");
            }

            // 更新倒计时
            if (enableAutoBlink && !isBlinking)
            {
                elapsedTime += Time.deltaTime;
                countdownTimer = Mathf.Max(0f, nextBlinkTime - elapsedTime);
            }
        }

        /// <summary>
        /// 检查是否可以启动眨眼（Live2D 是否已准备好）
        /// </summary>
        private bool CanStartBlinking()
        {
            // 检查 faceController 是否存在
            if (faceController == null)
            {
                faceController = GetComponent<Live2DFaceController>();
                if (faceController == null)
                {
                    faceController = FindObjectOfType<Live2DFaceController>();
                }

                if (faceController == null)
                {
                    return false; // 还没有找到 FaceController
                }
            }

            // 检查参数是否可以访问（尝试读取一个参数）
            float testValue = faceController.GetParameter(leftEyeParameter);
            if (testValue == -1f)
            {
                // 参数还不可用（可能还在初始化）
                return false;
            }

            return true; // 可以启动
        }

        // ========== Odin 按钮 ==========
        [ButtonGroup("控制按钮")]
        [Button("▶ 开始自动眨眼", ButtonSizes.Large)]
        [GUIColor(0.4f, 0.8f, 0.4f)]
        public void StartBlinking()
        {
            if (!enableAutoBlink)
            {
                enableAutoBlink = true;
            }

            StopBlinking(); // 先停止现有协程

            if (syncBothEyes)
            {
                blinkCoroutine = StartCoroutine(SyncBlinkRoutine());
            }
            else
            {
                leftEyeCoroutine = StartCoroutine(IndependentBlinkRoutine(true));
                rightEyeCoroutine = StartCoroutine(IndependentBlinkRoutine(false));
            }

            Debug.Log("[AutoBlinkController] 已启动自动眨眼");
        }

        [ButtonGroup("控制按钮")]
        [Button("⏸ 停止自动眨眼", ButtonSizes.Large)]
        [GUIColor(0.8f, 0.4f, 0.4f)]
        public void StopBlinking()
        {
            if (blinkCoroutine != null)
            {
                StopCoroutine(blinkCoroutine);
                blinkCoroutine = null;
            }

            if (leftEyeCoroutine != null)
            {
                StopCoroutine(leftEyeCoroutine);
                leftEyeCoroutine = null;
            }

            if (rightEyeCoroutine != null)
            {
                StopCoroutine(rightEyeCoroutine);
                rightEyeCoroutine = null;
            }

            isBlinking = false;

            // 重置眼睛到睁开状态
            SetEyeValue(leftEyeParameter, eyeOpenValue);
            SetEyeValue(rightEyeParameter, eyeOpenValue);
            leftEyeCurrentValue = eyeOpenValue;
            rightEyeCurrentValue = eyeOpenValue;

            Debug.Log("[AutoBlinkController] 已停止自动眨眼");
        }

        [ButtonGroup("控制按钮")]
        [Button("👁️ 立即眨眼一次", ButtonSizes.Large)]
        [GUIColor(0.4f, 0.6f, 0.8f)]
        public void BlinkOnce()
        {
            if (syncBothEyes)
            {
                StartCoroutine(PerformBlink(true, true));
            }
            else
            {
                StartCoroutine(PerformBlink(true, false));
                StartCoroutine(PerformBlink(false, false));
            }
        }

        [ButtonGroup("控制按钮")]
        [Button("🔄 重置计数器", ButtonSizes.Medium)]
        [GUIColor(0.7f, 0.7f, 0.7f)]
        public void ResetCounter()
        {
            totalBlinks = 0;
            Debug.Log("[AutoBlinkController] 计数器已重置");
        }

        // ========== 眨眼协程 ==========

        /// <summary>
        /// 双眼同步眨眼协程
        /// </summary>
        private IEnumerator SyncBlinkRoutine()
        {
            while (true)
            {
                // 计算下次眨眼时间（基础间隔 + 随机偏移）
                nextBlinkTime = baseBlinkInterval + Random.Range(-randomRange, randomRange);
                nextBlinkTime = Mathf.Max(0.5f, nextBlinkTime); // 最小间隔 0.5 秒
                elapsedTime = 0f;

                // 等待
                yield return new WaitForSeconds(nextBlinkTime);

                // 执行眨眼
                yield return PerformBlink(true, true);
            }
        }

        /// <summary>
        /// 独立眨眼协程（左眼或右眼）
        /// </summary>
        private IEnumerator IndependentBlinkRoutine(bool isLeftEye)
        {
            float interval = isLeftEye ? leftEyeInterval : rightEyeInterval;
            float randomRng = isLeftEye ? leftEyeRandomRange : rightEyeRandomRange;

            while (true)
            {
                float waitTime = interval + Random.Range(-randomRng, randomRng);
                waitTime = Mathf.Max(0.5f, waitTime);

                yield return new WaitForSeconds(waitTime);
                yield return PerformBlink(isLeftEye, false);
            }
        }

        /// <summary>
        /// 执行单次眨眼动画
        /// 从当前眼睛值开始闭眼，然后睁回到开始时的值
        /// </summary>
        private IEnumerator PerformBlink(bool isLeftEye, bool isBothEyes)
        {
            isBlinking = true;
            totalBlinks++;

            // 获取眨眼开始时的眼睛当前值（从 Live2D 参数读取）
            float leftStartValue = GetEyeValue(leftEyeParameter);
            float rightStartValue = GetEyeValue(rightEyeParameter);

            // 如果无法读取当前值，使用默认睁眼值
            if (leftStartValue < 0) leftStartValue = eyeOpenValue;
            if (rightStartValue < 0) rightStartValue = eyeOpenValue;

            float elapsed = 0f;
            float closeDuration = blinkDuration * closeRatio;
            float openDuration = blinkDuration * (1f - closeRatio);

            // 闭眼阶段：从当前值 → 闭眼值
            while (elapsed < closeDuration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / closeDuration;
                float curveValue = blinkCurve.Evaluate(t);

                if (isBothEyes)
                {
                    // 双眼：从各自的起始值闭眼
                    float leftEyeValue = Mathf.Lerp(leftStartValue, eyeClosedValue, curveValue * blinkStrength);
                    float rightEyeValue = Mathf.Lerp(rightStartValue, eyeClosedValue, curveValue * blinkStrength);

                    SetEyeValue(leftEyeParameter, leftEyeValue);
                    SetEyeValue(rightEyeParameter, rightEyeValue);
                    leftEyeCurrentValue = leftEyeValue;
                    rightEyeCurrentValue = rightEyeValue;
                }
                else if (isLeftEye)
                {
                    // 仅左眼：从左眼起始值闭眼
                    float eyeValue = Mathf.Lerp(leftStartValue, eyeClosedValue, curveValue * blinkStrength);
                    SetEyeValue(leftEyeParameter, eyeValue);
                    leftEyeCurrentValue = eyeValue;
                }
                else
                {
                    // 仅右眼：从右眼起始值闭眼
                    float eyeValue = Mathf.Lerp(rightStartValue, eyeClosedValue, curveValue * blinkStrength);
                    SetEyeValue(rightEyeParameter, eyeValue);
                    rightEyeCurrentValue = eyeValue;
                }

                yield return null;
            }

            // 睁眼阶段：从闭眼值 → 回到起始值
            elapsed = 0f;
            while (elapsed < openDuration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / openDuration;
                float curveValue = blinkCurve.Evaluate(1f - t);

                if (isBothEyes)
                {
                    // 双眼：睁回到各自的起始值
                    float leftEyeValue = Mathf.Lerp(leftStartValue, eyeClosedValue, curveValue * blinkStrength);
                    float rightEyeValue = Mathf.Lerp(rightStartValue, eyeClosedValue, curveValue * blinkStrength);

                    SetEyeValue(leftEyeParameter, leftEyeValue);
                    SetEyeValue(rightEyeParameter, rightEyeValue);
                    leftEyeCurrentValue = leftEyeValue;
                    rightEyeCurrentValue = rightEyeValue;
                }
                else if (isLeftEye)
                {
                    // 仅左眼：睁回到左眼起始值
                    float eyeValue = Mathf.Lerp(leftStartValue, eyeClosedValue, curveValue * blinkStrength);
                    SetEyeValue(leftEyeParameter, eyeValue);
                    leftEyeCurrentValue = eyeValue;
                }
                else
                {
                    // 仅右眼：睁回到右眼起始值
                    float eyeValue = Mathf.Lerp(rightStartValue, eyeClosedValue, curveValue * blinkStrength);
                    SetEyeValue(rightEyeParameter, eyeValue);
                    rightEyeCurrentValue = eyeValue;
                }

                yield return null;
            }

            // 确保完全恢复到起始值
            if (isBothEyes)
            {
                SetEyeValue(leftEyeParameter, leftStartValue);
                SetEyeValue(rightEyeParameter, rightStartValue);
                leftEyeCurrentValue = leftStartValue;
                rightEyeCurrentValue = rightStartValue;
            }
            else if (isLeftEye)
            {
                SetEyeValue(leftEyeParameter, leftStartValue);
                leftEyeCurrentValue = leftStartValue;
            }
            else
            {
                SetEyeValue(rightEyeParameter, rightStartValue);
                rightEyeCurrentValue = rightStartValue;
            }

            isBlinking = false;
        }

        // ========== Live2D 参数设置 ==========
        private void SetEyeValue(string parameterName, float value)
        {
            if (faceController != null)
            {
                faceController.SetParameter(parameterName, value);
            }
        }

        /// <summary>
        /// 获取 Live2D 参数的当前值
        /// </summary>
        private float GetEyeValue(string parameterName)
        {
            if (faceController != null)
            {
                return faceController.GetParameter(parameterName);
            }
            return -1f; // 返回 -1 表示无法读取
        }

        // ========== Odin 颜色辅助 ==========
        private Color GetBlinkStrengthColor(float value)
        {
            return Color.Lerp(new Color(1f, 0.8f, 0.4f), new Color(0.4f, 0.8f, 0.4f), value);
        }

        private Color GetCountdownColor(float value)
        {
            float ratio = value / nextBlinkTime;
            return Color.Lerp(new Color(0.8f, 0.4f, 0.4f), new Color(0.4f, 0.8f, 0.4f), ratio);
        }

        // ========== 编辑器辅助 ==========
        private void OnValidate()
        {
            // 确保闭眼值不大于睁眼值（如果是 0-1 范围）
            if (eyeClosedValue > eyeOpenValue)
            {
                Debug.LogWarning("[AutoBlinkController] 闭眼值大于睁眼值，请检查配置");
            }
        }
    }
}
