using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using UnityEngine.Events;
using Sirenix.OdinInspector;

namespace VibeVtuber.FaceTracking
{
    /// <summary>
    /// 通过UDP接收Python面部追踪数据
    /// 使用后台线程处理网络I/O，避免阻塞Unity主线程
    /// </summary>
    public class FaceDataReceiver : SerializedMonoBehaviour
    {
        [Title("Face Data Receiver", "接收并显示MediaPipe面部追踪数据（55个参数）", TitleAlignments.Centered, HorizontalLine = true)]

        [BoxGroup("网络设置")]
        [LabelText("UDP端口")]
        [Tooltip("UDP接收端口，需与Python端配置一致")]
        [SerializeField] private int port = 11111;

        [BoxGroup("网络设置")]
        [LabelText("自动启动")]
        [Tooltip("启用时自动开始接收数据")]
        [SerializeField] private bool autoStart = true;

        [BoxGroup("网络设置")]
        [LabelText("消息队列大小")]
        [Tooltip("防止队列溢出，超出时丢弃最旧消息")]
        [SerializeField] private int maxQueueSize = 10;

        [BoxGroup("事件")]
        [LabelText("数据接收事件")]
        public UnityEvent<FaceData> OnDataReceived = new UnityEvent<FaceData>();

        [BoxGroup("事件")]
        [LabelText("连接断开事件")]
        public UnityEvent OnConnectionLost = new UnityEvent();

        [BoxGroup("事件")]
        [LabelText("连接建立事件")]
        public UnityEvent OnConnectionEstablished = new UnityEvent();

        [FoldoutGroup("连接状态")]
        [LabelText("状态")]
        [ReadOnly]
        [SerializeField] private string connectionStatus = "未启动";

        [FoldoutGroup("连接状态")]
        [LabelText("帧率")]
        [ReadOnly]
        [SerializeField] private string fpsInfo = "0.0 FPS";

        // ========== 头部旋转参数 ==========
        [Title("头部旋转参数 (Head Rotation)", "3个参数：左右转头、上下点头、左右歪头", TitleAlignments.Left)]

        [HorizontalGroup("头部旋转参数/1")]
        [LabelText("左右转头 (headYaw)")]
        [Tooltip("头部左右旋转角度 | 负值=向左，正值=向右 | 范围: -90° ~ +90°")]
        [SerializeField] [Range(-90f, 90f)] private float headYaw = 0f;

        [HorizontalGroup("头部旋转参数/1")]
        [LabelText("上下点头 (headPitch)")]
        [Tooltip("头部上下旋转角度 | 负值=向下，正值=向上 | 范围: -90° ~ +90°")]
        [SerializeField] [Range(-90f, 90f)] private float headPitch = 0f;

        [HorizontalGroup("头部旋转参数/1")]
        [LabelText("左右歪头 (headRoll)")]
        [Tooltip("头部左右倾斜角度 | 负值=向左歪，正值=向右歪 | 范围: -90° ~ +90°")]
        [SerializeField] [Range(-90f, 90f)] private float headRoll = 0f;

        // ========== 眼睛眨眼参数 ==========
        [Title("眼睛眨眼参数 (Eye Blink)", "2个参数：左眼眨眼、右眼眨眼", TitleAlignments.Left)]

        [HorizontalGroup("眼睛眨眼参数/1")]
        [LabelText("左眼眨眼 (eyeBlinkLeft)")]
        [Tooltip("左眼闭合程度 | 0=完全睁开，1=完全闭合")]
        [ProgressBar(0, 1, ColorGetter = "GetEyeBlinkColor")]
        [SerializeField] [Range(0f, 1f)] private float eyeBlinkLeft = 0f;

        [HorizontalGroup("眼睛眨眼参数/1")]
        [LabelText("右眼眨眼 (eyeBlinkRight)")]
        [Tooltip("右眼闭合程度 | 0=完全睁开，1=完全闭合")]
        [ProgressBar(0, 1, ColorGetter = "GetEyeBlinkColor")]
        [SerializeField] [Range(0f, 1f)] private float eyeBlinkRight = 0f;

        // ========== 眼球移动参数 ==========
        [Title("眼球移动参数 (Eye Look)", "8个参数：眼球朝向（上下左右）", TitleAlignments.Left)]
        [InfoBox("眼球Y轴：Up=向上看，Down=向下看 | 眼球X轴：In=向鼻子看，Out=向外看", InfoMessageType.None)]

        [FoldoutGroup("眼球移动参数/左眼", false)]
        [HorizontalGroup("眼球移动参数/左眼/1")]
        [LabelText("向上看 (eyeLookUpLeft)")]
        [Tooltip("左眼球向上看的程度 | 0=不看，1=完全向上")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookUpLeft = 0f;

        [HorizontalGroup("眼球移动参数/左眼/1")]
        [LabelText("向下看 (eyeLookDownLeft)")]
        [Tooltip("左眼球向下看的程度 | 0=不看，1=完全向下")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookDownLeft = 0f;

        [FoldoutGroup("眼球移动参数/左眼")]
        [HorizontalGroup("眼球移动参数/左眼/2")]
        [LabelText("向内看 (eyeLookInLeft)")]
        [Tooltip("左眼球向鼻子方向看 | 0=不看，1=完全向内")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookInLeft = 0f;

        [HorizontalGroup("眼球移动参数/左眼/2")]
        [LabelText("向外看 (eyeLookOutLeft)")]
        [Tooltip("左眼球向外侧看 | 0=不看，1=完全向外")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookOutLeft = 0f;

        [FoldoutGroup("眼球移动参数/右眼", false)]
        [HorizontalGroup("眼球移动参数/右眼/1")]
        [LabelText("向上看 (eyeLookUpRight)")]
        [Tooltip("右眼球向上看的程度 | 0=不看，1=完全向上")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookUpRight = 0f;

        [HorizontalGroup("眼球移动参数/右眼/1")]
        [LabelText("向下看 (eyeLookDownRight)")]
        [Tooltip("右眼球向下看的程度 | 0=不看，1=完全向下")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookDownRight = 0f;

        [FoldoutGroup("眼球移动参数/右眼")]
        [HorizontalGroup("眼球移动参数/右眼/2")]
        [LabelText("向内看 (eyeLookInRight)")]
        [Tooltip("右眼球向鼻子方向看 | 0=不看，1=完全向内")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookInRight = 0f;

        [HorizontalGroup("眼球移动参数/右眼/2")]
        [LabelText("向外看 (eyeLookOutRight)")]
        [Tooltip("右眼球向外侧看 | 0=不看，1=完全向外")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeLookOutRight = 0f;

        // ========== 眼睛眯眼/睁大参数 ==========
        [Title("眼睛眯眼/睁大参数 (Eye Squint/Wide)", "4个参数", TitleAlignments.Left)]

        [HorizontalGroup("眼睛眯眼/睁大参数/1")]
        [LabelText("左眼眯眼 (eyeSquintLeft)")]
        [Tooltip("左眼眯起的程度 | 0=正常，1=完全眯起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeSquintLeft = 0f;

        [HorizontalGroup("眼睛眯眼/睁大参数/1")]
        [LabelText("右眼眯眼 (eyeSquintRight)")]
        [Tooltip("右眼眯起的程度 | 0=正常，1=完全眯起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeSquintRight = 0f;

        [HorizontalGroup("眼睛眯眼/睁大参数/2")]
        [LabelText("左眼睁大 (eyeWideLeft)")]
        [Tooltip("左眼睁大的程度 | 0=正常，1=完全睁大")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeWideLeft = 0f;

        [HorizontalGroup("眼睛眯眼/睁大参数/2")]
        [LabelText("右眼睁大 (eyeWideRight)")]
        [Tooltip("右眼睁大的程度 | 0=正常，1=完全睁大")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float eyeWideRight = 0f;

        // ========== 眉毛参数 ==========
        [Title("眉毛参数 (Eyebrow)", "5个参数：眉毛上扬、下皱", TitleAlignments.Left)]

        [HorizontalGroup("眉毛参数/1")]
        [LabelText("左眉下皱 (browDownLeft)")]
        [Tooltip("左眉向下皱的程度 | 0=正常，1=完全下皱")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float browDownLeft = 0f;

        [HorizontalGroup("眉毛参数/1")]
        [LabelText("右眉下皱 (browDownRight)")]
        [Tooltip("右眉向下皱的程度 | 0=正常，1=完全下皱")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float browDownRight = 0f;

        [HorizontalGroup("眉毛参数/2")]
        [LabelText("内眉上扬 (browInnerUp)")]
        [Tooltip("眉毛内侧（靠近鼻子）上扬程度 | 0=正常，1=完全上扬")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float browInnerUp = 0f;

        [HorizontalGroup("眉毛参数/3")]
        [LabelText("左外眉上扬 (browOuterUpLeft)")]
        [Tooltip("左眉外侧上扬程度 | 0=正常，1=完全上扬")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float browOuterUpLeft = 0f;

        [HorizontalGroup("眉毛参数/3")]
        [LabelText("右外眉上扬 (browOuterUpRight)")]
        [Tooltip("右眉外侧上扬程度 | 0=正常，1=完全上扬")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float browOuterUpRight = 0f;

        // ========== 下巴参数 ==========
        [Title("下巴参数 (Jaw)", "4个参数：张嘴、前伸、左右移动", TitleAlignments.Left)]

        [HorizontalGroup("下巴参数/1")]
        [LabelText("张嘴 (jawOpen)")]
        [Tooltip("下巴张开程度 | 0=闭嘴，1=完全张开")]
        [ProgressBar(0, 1, ColorGetter = "GetJawOpenColor")]
        [SerializeField] [Range(0f, 1f)] private float jawOpen = 0f;

        [HorizontalGroup("下巴参数/1")]
        [LabelText("前伸 (jawForward)")]
        [Tooltip("下巴向前伸的程度 | 0=正常，1=完全前伸")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float jawForward = 0f;

        [HorizontalGroup("下巴参数/2")]
        [LabelText("向左移动 (jawLeft)")]
        [Tooltip("下巴向左移动程度 | 0=正常，1=完全向左")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float jawLeft = 0f;

        [HorizontalGroup("下巴参数/2")]
        [LabelText("向右移动 (jawRight)")]
        [Tooltip("下巴向右移动程度 | 0=正常，1=完全向右")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float jawRight = 0f;

        // ========== 嘴巴参数 ==========
        [Title("嘴巴参数 (Mouth)", "24个参数：微笑、皱眉、撅嘴等", TitleAlignments.Left)]

        [FoldoutGroup("嘴巴参数/基本形状", false)]
        [HorizontalGroup("嘴巴参数/基本形状/1")]
        [LabelText("闭嘴 (mouthClose)")]
        [Tooltip("嘴巴闭合程度 | 0=正常，1=用力闭合")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthClose = 0f;

        [HorizontalGroup("嘴巴参数/基本形状/1")]
        [LabelText("漏斗形 (mouthFunnel)")]
        [Tooltip("嘴巴呈漏斗形（如发'O'音）| 0=正常，1=完全漏斗形")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthFunnel = 0f;

        [HorizontalGroup("嘴巴参数/基本形状/1")]
        [LabelText("撅嘴 (mouthPucker)")]
        [Tooltip("嘴巴撅起程度 | 0=正常，1=完全撅起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthPucker = 0f;

        [FoldoutGroup("嘴巴参数/左右移动")]
        [HorizontalGroup("嘴巴参数/左右移动/1")]
        [LabelText("向左 (mouthLeft)")]
        [Tooltip("嘴巴向左移动 | 0=正常，1=完全向左")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthLeft = 0f;

        [HorizontalGroup("嘴巴参数/左右移动/1")]
        [LabelText("向右 (mouthRight)")]
        [Tooltip("嘴巴向右移动 | 0=正常，1=完全向右")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthRight = 0f;

        [FoldoutGroup("嘴巴参数/微笑/皱眉")]
        [HorizontalGroup("嘴巴参数/微笑/皱眉/1")]
        [LabelText("左侧微笑 (mouthSmileLeft)")]
        [Tooltip("嘴角左侧上扬（微笑）| 0=正常，1=完全微笑")]
        [ProgressBar(0, 1, ColorGetter = "GetSmileColor")]
        [SerializeField] [Range(0f, 1f)] private float mouthSmileLeft = 0f;

        [HorizontalGroup("嘴巴参数/微笑/皱眉/1")]
        [LabelText("右侧微笑 (mouthSmileRight)")]
        [Tooltip("嘴角右侧上扬（微笑）| 0=正常，1=完全微笑")]
        [ProgressBar(0, 1, ColorGetter = "GetSmileColor")]
        [SerializeField] [Range(0f, 1f)] private float mouthSmileRight = 0f;

        [FoldoutGroup("嘴巴参数/微笑/皱眉")]
        [HorizontalGroup("嘴巴参数/微笑/皱眉/2")]
        [LabelText("左侧皱眉 (mouthFrownLeft)")]
        [Tooltip("嘴角左侧下压（皱眉/悲伤）| 0=正常，1=完全皱眉")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthFrownLeft = 0f;

        [HorizontalGroup("嘴巴参数/微笑/皱眉/2")]
        [LabelText("右侧皱眉 (mouthFrownRight)")]
        [Tooltip("嘴角右侧下压（皱眉/悲伤）| 0=正常，1=完全皱眉")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthFrownRight = 0f;

        [FoldoutGroup("嘴巴参数/酒窝")]
        [HorizontalGroup("嘴巴参数/酒窝/1")]
        [LabelText("左侧酒窝 (mouthDimpleLeft)")]
        [Tooltip("左侧脸颊凹陷（酒窝）| 0=正常，1=明显酒窝")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthDimpleLeft = 0f;

        [HorizontalGroup("嘴巴参数/酒窝/1")]
        [LabelText("右侧酒窝 (mouthDimpleRight)")]
        [Tooltip("右侧脸颊凹陷（酒窝）| 0=正常，1=明显酒窝")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthDimpleRight = 0f;

        [FoldoutGroup("嘴巴参数/拉伸")]
        [HorizontalGroup("嘴巴参数/拉伸/1")]
        [LabelText("左侧拉伸 (mouthStretchLeft)")]
        [Tooltip("嘴巴左侧横向拉伸 | 0=正常，1=完全拉伸")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthStretchLeft = 0f;

        [HorizontalGroup("嘴巴参数/拉伸/1")]
        [LabelText("右侧拉伸 (mouthStretchRight)")]
        [Tooltip("嘴巴右侧横向拉伸 | 0=正常，1=完全拉伸")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthStretchRight = 0f;

        [FoldoutGroup("嘴巴参数/嘴唇卷曲")]
        [HorizontalGroup("嘴巴参数/嘴唇卷曲/1")]
        [LabelText("下唇内卷 (mouthRollLower)")]
        [Tooltip("下嘴唇向内卷曲 | 0=正常，1=完全卷曲")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthRollLower = 0f;

        [HorizontalGroup("嘴巴参数/嘴唇卷曲/1")]
        [LabelText("上唇内卷 (mouthRollUpper)")]
        [Tooltip("上嘴唇向内卷曲 | 0=正常，1=完全卷曲")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthRollUpper = 0f;

        [FoldoutGroup("嘴巴参数/嘴唇耸肩")]
        [HorizontalGroup("嘴巴参数/嘴唇耸肩/1")]
        [LabelText("下唇上抬 (mouthShrugLower)")]
        [Tooltip("下嘴唇向上抬起 | 0=正常，1=完全抬起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthShrugLower = 0f;

        [HorizontalGroup("嘴巴参数/嘴唇耸肩/1")]
        [LabelText("上唇下压 (mouthShrugUpper)")]
        [Tooltip("上嘴唇向下压 | 0=正常，1=完全下压")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthShrugUpper = 0f;

        [FoldoutGroup("嘴巴参数/嘴唇紧闭")]
        [HorizontalGroup("嘴巴参数/嘴唇紧闭/1")]
        [LabelText("左侧紧闭 (mouthPressLeft)")]
        [Tooltip("嘴唇左侧紧闭 | 0=正常，1=完全紧闭")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthPressLeft = 0f;

        [HorizontalGroup("嘴巴参数/嘴唇紧闭/1")]
        [LabelText("右侧紧闭 (mouthPressRight)")]
        [Tooltip("嘴唇右侧紧闭 | 0=正常，1=完全紧闭")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthPressRight = 0f;

        [FoldoutGroup("嘴巴参数/嘴唇移动")]
        [HorizontalGroup("嘴巴参数/嘴唇移动/1")]
        [LabelText("左下唇下拉 (mouthLowerDownLeft)")]
        [Tooltip("下嘴唇左侧向下拉 | 0=正常，1=完全下拉")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthLowerDownLeft = 0f;

        [HorizontalGroup("嘴巴参数/嘴唇移动/1")]
        [LabelText("右下唇下拉 (mouthLowerDownRight)")]
        [Tooltip("下嘴唇右侧向下拉 | 0=正常，1=完全下拉")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthLowerDownRight = 0f;

        [FoldoutGroup("嘴巴参数/嘴唇移动")]
        [HorizontalGroup("嘴巴参数/嘴唇移动/2")]
        [LabelText("左上唇上抬 (mouthUpperUpLeft)")]
        [Tooltip("上嘴唇左侧向上抬 | 0=正常，1=完全上抬")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthUpperUpLeft = 0f;

        [HorizontalGroup("嘴巴参数/嘴唇移动/2")]
        [LabelText("右上唇上抬 (mouthUpperUpRight)")]
        [Tooltip("上嘴唇右侧向上抬 | 0=正常，1=完全上抬")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float mouthUpperUpRight = 0f;

        // ========== 鼻子参数 ==========
        [Title("鼻子参数 (Nose)", "2个参数：鼻翼皱起", TitleAlignments.Left)]

        [HorizontalGroup("鼻子参数/1")]
        [LabelText("左鼻翼皱起 (noseSneerLeft)")]
        [Tooltip("左侧鼻翼向上皱起 | 0=正常，1=完全皱起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float noseSneerLeft = 0f;

        [HorizontalGroup("鼻子参数/1")]
        [LabelText("右鼻翼皱起 (noseSneerRight)")]
        [Tooltip("右侧鼻翼向上皱起 | 0=正常，1=完全皱起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float noseSneerRight = 0f;

        // ========== 脸颊参数 ==========
        [Title("脸颊参数 (Cheek)", "3个参数：鼓腮、眯眼脸颊", TitleAlignments.Left)]

        [HorizontalGroup("脸颊参数/1")]
        [LabelText("鼓腮 (cheekPuff)")]
        [Tooltip("两侧脸颊鼓起 | 0=正常，1=完全鼓起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float cheekPuff = 0f;

        [HorizontalGroup("脸颊参数/2")]
        [LabelText("左侧脸颊眯眼 (cheekSquintLeft)")]
        [Tooltip("左侧脸颊因眯眼而抬起 | 0=正常，1=完全抬起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float cheekSquintLeft = 0f;

        [HorizontalGroup("脸颊参数/2")]
        [LabelText("右侧脸颊眯眼 (cheekSquintRight)")]
        [Tooltip("右侧脸颊因眯眼而抬起 | 0=正常，1=完全抬起")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float cheekSquintRight = 0f;

        // ========== 舌头参数 ==========
        [Title("舌头参数 (Tongue)", "1个参数：伸舌头", TitleAlignments.Left)]

        [LabelText("伸舌头 (tongueOut)")]
        [Tooltip("舌头伸出程度 | 0=正常，1=完全伸出")]
        [ProgressBar(0, 1)]
        [SerializeField] [Range(0f, 1f)] private float tongueOut = 0f;

        // ========== Odin 颜色辅助方法 ==========
        private Color GetEyeBlinkColor(float value)
        {
            return Color.Lerp(Color.green, Color.yellow, value);
        }

        private Color GetJawOpenColor(float value)
        {
            return Color.Lerp(Color.green, Color.cyan, value);
        }

        private Color GetSmileColor(float value)
        {
            return Color.Lerp(Color.green, new Color(1f, 0.5f, 0f), value); // Orange
        }

        // ========== 内部变量 ==========
        private ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();
        private UdpClient udpClient;
        private Thread receiveThread;
        private bool isRunning = false;
        private bool wasConnected = false;
        private float lastDataTime = 0f;
        private const float ConnectionTimeout = 2f;

        public bool IsReceiving { get; private set; }
        public int MessagesReceivedThisFrame { get; private set; }
        public int TotalMessagesReceived { get; private set; }
        public float CurrentFPS { get; private set; }

        private float fpsUpdateTime = 0f;
        private int frameCount = 0;
        private FaceData latestFaceData = null;

        private void OnEnable()
        {
            if (autoStart)
            {
                StartReceiving();
            }
        }

        private void OnDisable()
        {
            StopReceiving();
        }

        [ButtonGroup]
        [Button("开始接收", ButtonSizes.Large)]
        [GUIColor(0.4f, 0.8f, 0.4f)]
        public void StartReceiving()
        {
            if (isRunning)
            {
                Debug.LogWarning("[FaceDataReceiver] 已在接收数据");
                return;
            }

            try
            {
                if (udpClient != null)
                {
                    try { udpClient.Close(); udpClient.Dispose(); } catch { }
                    udpClient = null;
                }

                udpClient = new UdpClient();
                udpClient.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                udpClient.Client.Bind(new IPEndPoint(IPAddress.Any, port));
                udpClient.Client.ReceiveTimeout = 1000;

                isRunning = true;
                receiveThread = new Thread(ReceiveData);
                receiveThread.IsBackground = true;
                receiveThread.Start();

                Debug.Log($"[FaceDataReceiver] 已在端口 {port} 启动接收");
            }
            catch (Exception e)
            {
                Debug.LogError($"[FaceDataReceiver] 启动失败: {e.Message}");
                isRunning = false;
            }
        }

        [ButtonGroup]
        [Button("停止接收", ButtonSizes.Large)]
        [GUIColor(0.8f, 0.4f, 0.4f)]
        public void StopReceiving()
        {
            if (!isRunning)
            {
                return;
            }

            Debug.Log("[FaceDataReceiver] 正在停止接收...");
            isRunning = false;

            if (receiveThread != null && receiveThread.IsAlive)
            {
                if (!receiveThread.Join(1000))
                {
                    Debug.LogWarning("[FaceDataReceiver] 线程未正常停止");
                }
            }

            if (udpClient != null)
            {
                try { udpClient.Close(); udpClient.Dispose(); } catch { }
                udpClient = null;
            }

            while (messageQueue.TryDequeue(out _)) { }
            Debug.Log("[FaceDataReceiver] 已停止接收");
        }

        [ButtonGroup]
        [Button("重新连接", ButtonSizes.Large)]
        [GUIColor(0.4f, 0.6f, 0.8f)]
        public void Reconnect()
        {
            Debug.Log("[FaceDataReceiver] 正在重新连接...");
            StopReceiving();
            System.Threading.Thread.Sleep(100);
            StartReceiving();
        }

        private void ReceiveData()
        {
            IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);

            while (isRunning)
            {
                try
                {
                    byte[] data = udpClient.Receive(ref remoteEndPoint);
                    string message = Encoding.UTF8.GetString(data);

                    if (messageQueue.Count >= maxQueueSize)
                    {
                        messageQueue.TryDequeue(out _);
                    }
                    messageQueue.Enqueue(message);
                }
                catch (SocketException e)
                {
                    if (e.SocketErrorCode != SocketError.TimedOut && isRunning)
                    {
                        Debug.LogWarning($"[FaceDataReceiver] Socket错误: {e.Message}");
                    }
                }
                catch (Exception e)
                {
                    if (isRunning)
                    {
                        Debug.LogError($"[FaceDataReceiver] 接收错误: {e.Message}");
                    }
                }
            }
        }

        private void Update()
        {
            MessagesReceivedThisFrame = 0;

            while (messageQueue.TryDequeue(out string message))
            {
                ProcessMessage(message);
                MessagesReceivedThisFrame++;
                TotalMessagesReceived++;
                lastDataTime = Time.time;
            }

            IsReceiving = (Time.time - lastDataTime) < ConnectionTimeout;

            if (IsReceiving && !wasConnected)
            {
                OnConnectionEstablished.Invoke();
                Debug.Log("[FaceDataReceiver] 连接已建立");
            }
            else if (!IsReceiving && wasConnected)
            {
                OnConnectionLost.Invoke();
                Debug.Log("[FaceDataReceiver] 连接已断开");
            }
            wasConnected = IsReceiving;

            frameCount += MessagesReceivedThisFrame;
            if (Time.time - fpsUpdateTime >= 1f)
            {
                CurrentFPS = frameCount / (Time.time - fpsUpdateTime);
                frameCount = 0;
                fpsUpdateTime = Time.time;
            }

            UpdateInspectorDebugInfo();
        }

        private void UpdateInspectorDebugInfo()
        {
            connectionStatus = IsReceiving ? $"已连接 ({CurrentFPS:F1} FPS)" : "等待数据";
            fpsInfo = $"{CurrentFPS:F1} FPS | 总计: {TotalMessagesReceived}";

            if (latestFaceData != null && latestFaceData.faceDetected)
            {
                headYaw = latestFaceData.GetBlendshape("headYaw");
                headPitch = latestFaceData.GetBlendshape("headPitch");
                headRoll = latestFaceData.GetBlendshape("headRoll");

                eyeBlinkLeft = latestFaceData.GetBlendshape("eyeBlinkLeft");
                eyeBlinkRight = latestFaceData.GetBlendshape("eyeBlinkRight");

                eyeLookUpLeft = latestFaceData.GetBlendshape("eyeLookUpLeft");
                eyeLookUpRight = latestFaceData.GetBlendshape("eyeLookUpRight");
                eyeLookDownLeft = latestFaceData.GetBlendshape("eyeLookDownLeft");
                eyeLookDownRight = latestFaceData.GetBlendshape("eyeLookDownRight");
                eyeLookInLeft = latestFaceData.GetBlendshape("eyeLookInLeft");
                eyeLookInRight = latestFaceData.GetBlendshape("eyeLookInRight");
                eyeLookOutLeft = latestFaceData.GetBlendshape("eyeLookOutLeft");
                eyeLookOutRight = latestFaceData.GetBlendshape("eyeLookOutRight");

                eyeSquintLeft = latestFaceData.GetBlendshape("eyeSquintLeft");
                eyeSquintRight = latestFaceData.GetBlendshape("eyeSquintRight");
                eyeWideLeft = latestFaceData.GetBlendshape("eyeWideLeft");
                eyeWideRight = latestFaceData.GetBlendshape("eyeWideRight");

                browDownLeft = latestFaceData.GetBlendshape("browDownLeft");
                browDownRight = latestFaceData.GetBlendshape("browDownRight");
                browInnerUp = latestFaceData.GetBlendshape("browInnerUp");
                browOuterUpLeft = latestFaceData.GetBlendshape("browOuterUpLeft");
                browOuterUpRight = latestFaceData.GetBlendshape("browOuterUpRight");

                jawOpen = latestFaceData.GetBlendshape("jawOpen");
                jawForward = latestFaceData.GetBlendshape("jawForward");
                jawLeft = latestFaceData.GetBlendshape("jawLeft");
                jawRight = latestFaceData.GetBlendshape("jawRight");

                mouthClose = latestFaceData.GetBlendshape("mouthClose");
                mouthFunnel = latestFaceData.GetBlendshape("mouthFunnel");
                mouthPucker = latestFaceData.GetBlendshape("mouthPucker");
                mouthLeft = latestFaceData.GetBlendshape("mouthLeft");
                mouthRight = latestFaceData.GetBlendshape("mouthRight");
                mouthSmileLeft = latestFaceData.GetBlendshape("mouthSmileLeft");
                mouthSmileRight = latestFaceData.GetBlendshape("mouthSmileRight");
                mouthFrownLeft = latestFaceData.GetBlendshape("mouthFrownLeft");
                mouthFrownRight = latestFaceData.GetBlendshape("mouthFrownRight");
                mouthDimpleLeft = latestFaceData.GetBlendshape("mouthDimpleLeft");
                mouthDimpleRight = latestFaceData.GetBlendshape("mouthDimpleRight");
                mouthStretchLeft = latestFaceData.GetBlendshape("mouthStretchLeft");
                mouthStretchRight = latestFaceData.GetBlendshape("mouthStretchRight");
                mouthRollLower = latestFaceData.GetBlendshape("mouthRollLower");
                mouthRollUpper = latestFaceData.GetBlendshape("mouthRollUpper");
                mouthShrugLower = latestFaceData.GetBlendshape("mouthShrugLower");
                mouthShrugUpper = latestFaceData.GetBlendshape("mouthShrugUpper");
                mouthPressLeft = latestFaceData.GetBlendshape("mouthPressLeft");
                mouthPressRight = latestFaceData.GetBlendshape("mouthPressRight");
                mouthLowerDownLeft = latestFaceData.GetBlendshape("mouthLowerDownLeft");
                mouthLowerDownRight = latestFaceData.GetBlendshape("mouthLowerDownRight");
                mouthUpperUpLeft = latestFaceData.GetBlendshape("mouthUpperUpLeft");
                mouthUpperUpRight = latestFaceData.GetBlendshape("mouthUpperUpRight");

                noseSneerLeft = latestFaceData.GetBlendshape("noseSneerLeft");
                noseSneerRight = latestFaceData.GetBlendshape("noseSneerRight");

                cheekPuff = latestFaceData.GetBlendshape("cheekPuff");
                cheekSquintLeft = latestFaceData.GetBlendshape("cheekSquintLeft");
                cheekSquintRight = latestFaceData.GetBlendshape("cheekSquintRight");

                tongueOut = latestFaceData.GetBlendshape("tongueOut");
            }
            else
            {
                headYaw = 0f; headPitch = 0f; headRoll = 0f;
                eyeBlinkLeft = 0f; eyeBlinkRight = 0f;
                eyeLookUpLeft = 0f; eyeLookUpRight = 0f; eyeLookDownLeft = 0f; eyeLookDownRight = 0f;
                eyeLookInLeft = 0f; eyeLookInRight = 0f; eyeLookOutLeft = 0f; eyeLookOutRight = 0f;
                eyeSquintLeft = 0f; eyeSquintRight = 0f; eyeWideLeft = 0f; eyeWideRight = 0f;
                browDownLeft = 0f; browDownRight = 0f; browInnerUp = 0f;
                browOuterUpLeft = 0f; browOuterUpRight = 0f;
                jawOpen = 0f; jawForward = 0f; jawLeft = 0f; jawRight = 0f;
                mouthClose = 0f; mouthFunnel = 0f; mouthPucker = 0f; mouthLeft = 0f; mouthRight = 0f;
                mouthSmileLeft = 0f; mouthSmileRight = 0f; mouthFrownLeft = 0f; mouthFrownRight = 0f;
                mouthDimpleLeft = 0f; mouthDimpleRight = 0f; mouthStretchLeft = 0f; mouthStretchRight = 0f;
                mouthRollLower = 0f; mouthRollUpper = 0f; mouthShrugLower = 0f; mouthShrugUpper = 0f;
                mouthPressLeft = 0f; mouthPressRight = 0f; mouthLowerDownLeft = 0f; mouthLowerDownRight = 0f;
                mouthUpperUpLeft = 0f; mouthUpperUpRight = 0f;
                noseSneerLeft = 0f; noseSneerRight = 0f;
                cheekPuff = 0f; cheekSquintLeft = 0f; cheekSquintRight = 0f;
                tongueOut = 0f;
            }
        }

        private void ProcessMessage(string json)
        {
            try
            {
                FaceData data = JsonUtility.FromJson<FaceData>(json);
                data.blendshapes = ParseBlendshapes(json);
                latestFaceData = data;
                OnDataReceived.Invoke(data);
            }
            catch (Exception e)
            {
                Debug.LogError($"[FaceDataReceiver] JSON解析错误: {e.Message}");
            }
        }

        private Dictionary<string, float> ParseBlendshapes(string json)
        {
            var dict = new Dictionary<string, float>();

            try
            {
                int startIndex = json.IndexOf("\"blendshapes\":");
                if (startIndex == -1) return dict;

                int braceStart = json.IndexOf('{', startIndex);
                if (braceStart == -1) return dict;

                int braceCount = 1;
                int endIndex = braceStart + 1;
                while (endIndex < json.Length && braceCount > 0)
                {
                    if (json[endIndex] == '{') braceCount++;
                    else if (json[endIndex] == '}') braceCount--;
                    endIndex++;
                }

                if (braceCount != 0) return dict;

                string blendshapesStr = json.Substring(braceStart + 1, endIndex - braceStart - 2);
                if (string.IsNullOrWhiteSpace(blendshapesStr)) return dict;

                int currentPos = 0;
                while (currentPos < blendshapesStr.Length)
                {
                    while (currentPos < blendshapesStr.Length && char.IsWhiteSpace(blendshapesStr[currentPos]))
                        currentPos++;

                    if (currentPos >= blendshapesStr.Length) break;

                    if (blendshapesStr[currentPos] != '"')
                    {
                        currentPos++;
                        continue;
                    }

                    int keyStart = currentPos + 1;
                    int keyEnd = blendshapesStr.IndexOf('"', keyStart);
                    if (keyEnd == -1) break;

                    string key = blendshapesStr.Substring(keyStart, keyEnd - keyStart);

                    int colonPos = blendshapesStr.IndexOf(':', keyEnd);
                    if (colonPos == -1) break;

                    int valueStart = colonPos + 1;
                    while (valueStart < blendshapesStr.Length && char.IsWhiteSpace(blendshapesStr[valueStart]))
                        valueStart++;

                    int valueEnd = valueStart;
                    while (valueEnd < blendshapesStr.Length &&
                           blendshapesStr[valueEnd] != ',' &&
                           blendshapesStr[valueEnd] != '}')
                    {
                        valueEnd++;
                    }

                    string valueStr = blendshapesStr.Substring(valueStart, valueEnd - valueStart).Trim();

                    if (float.TryParse(valueStr, System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out float value))
                    {
                        dict[key] = value;
                    }

                    currentPos = valueEnd + 1;
                }
            }
            catch { }

            return dict;
        }

        private void OnDestroy()
        {
            StopReceiving();
        }

        private void OnApplicationQuit()
        {
            StopReceiving();
        }

        [Button("记录所有参数到控制台", ButtonSizes.Large)]
        [GUIColor(0.6f, 0.6f, 0.8f)]
        public void LogAllBlendshapes()
        {
            if (latestFaceData == null || latestFaceData.blendshapes == null)
            {
                Debug.Log("[FaceDataReceiver] 暂无数据");
                return;
            }

            Debug.Log($"[FaceDataReceiver] === 所有参数 ({latestFaceData.blendshapes.Count} 个) ===");

            var sortedBlendshapes = new List<KeyValuePair<string, float>>(latestFaceData.blendshapes);
            sortedBlendshapes.Sort((a, b) => string.Compare(a.Key, b.Key));

            foreach (var kvp in sortedBlendshapes)
            {
                Debug.Log($"  {kvp.Key,-30} = {kvp.Value:F4}");
            }

            Debug.Log($"[FaceDataReceiver] === 结束 ===");
        }

        private void OnValidate()
        {
            if (port < 1024 || port > 65535)
            {
                Debug.LogWarning("[FaceDataReceiver] 端口应在 1024-65535 之间");
            }
        }
    }
}
