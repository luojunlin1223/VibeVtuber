# Python Face Tracker 调试指南

## 调试功能

### 1. 调试窗口（OpenCV 可视化）

运行 `python main.py` 后，会弹出一个窗口显示：

```
=== HEAD ROTATION ===
Yaw:    15.3
Pitch:  -8.2
Roll:    2.1

=== MOUTH ===
JawOpen: 0.456  ████████░░
Smile:   0.234  ██░░░░░░░░
Frown:   0.012  ░░░░░░░░░░
Pucker:  0.089

=== EYES ===
BlinkL:  0.001  ░░░░░░░░░░
BlinkR:  0.002  ░░░░░░░░░░

=== EYEBROWS ===
BrowUp:  0.123  █░░░░░░░░░
```

**绿色进度条** = 参数值的可视化（0.0 到 1.0 映射到 0-100px）

---

### 2. 终端输出

#### 简洁模式（默认）
```
[Status] FPS: 30.0 | FACE | Jaw: 0.45 | Smile: 0.23 | BlinkL: 0.00 | BlinkR: 0.00
```

#### 详细模式（按 'd' 键切换）
```
[Status] FPS: 30.0 | FACE DETECTED
  Head: Yaw=  15.3° Pitch=  -8.2° Roll=   2.1°
  Mouth: Jaw=0.456 Smile=0.234 Frown=0.012 Pucker=0.089
  Eyes: BlinkL=0.001 BlinkR=0.002
  Brow: InnerUp=0.123
```

---

## 键盘快捷键

| 按键 | 功能 |
|-----|------|
| **q** | 退出程序 |
| **s** | 切换调试窗口显示/隐藏 |
| **d** | 切换终端详细输出模式 |

---

## 如何使用调试功能排查问题

### 问题：嘴巴参数不变化

#### 步骤 1：查看 Python 调试窗口
1. 确保调试窗口打开（按 's' 如果关闭了）
2. 张嘴、微笑、皱眉
3. 观察 **MOUTH** 部分的值

**期望结果：**
- 张嘴时，`JawOpen` 应该从 `0.000` 增加到 `0.5-0.8`
- 微笑时，`Smile` 应该增加
- 皱眉时，`Frown` 应该增加

**如果值不变化** → MediaPipe 没有检测到面部动作
- 检查光线是否充足
- 脸是否完全在镜头内
- 尝试更夸张的表情

**如果值在变化** → Python 端正常，问题在 Unity 端

---

#### 步骤 2：查看终端输出
1. 按 **'d'** 键启用详细输出
2. 观察终端中的数值

如果看到：
```
Mouth: Jaw=0.000 Smile=0.000 Frown=0.000 Pucker=0.000
```
一直是 0.000 → MediaPipe 配置或模型问题

如果看到：
```
Mouth: Jaw=0.456 Smile=0.234 Frown=0.012 Pucker=0.089
```
数值在变化 → Python 端正常

---

#### 步骤 3：检查网络发送
在 `network_sender.py` 中，数据会通过 UDP 发送到 Unity。

确认：
1. 终端显示：`[NetworkSender] Initialized UDP sender to 127.0.0.1:11111`
2. 没有错误信息

如果看到错误 → 检查端口是否被占用

---

### 问题：眼睛眨眼不工作

查看调试窗口 **EYES** 部分：

**正常值：**
- 睁眼：`BlinkL: 0.000`, `BlinkR: 0.000`
- 闭眼：`BlinkL: 1.000`, `BlinkR: 1.000`

**如果始终是 0.000** → 检测失败，尝试：
- 确保眼睛在画面中清晰可见
- 调整光线
- 更夸张的眨眼动作

---

### 问题：头部旋转不工作

查看调试窗口 **HEAD ROTATION** 部分：

**正常值：**
- 正视镜头：`Yaw: 0.0`, `Pitch: 0.0`, `Roll: 0.0`
- 左转头：`Yaw: -15.0 到 -30.0`
- 右转头：`Yaw: +15.0 到 +30.0`
- 低头：`Pitch: -15.0 到 -30.0`
- 抬头：`Pitch: +15.0 到 +30.0`

**如果值不变化** → MediaPipe 问题
**如果值在变化** → Unity 参数映射问题

---

## 参数值含义

### Blendshape 值范围：0.0 到 1.0

| 参数 | 0.0 | 1.0 |
|-----|-----|-----|
| **JawOpen** | 嘴闭 | 嘴张到最大 |
| **Smile** | 不笑 | 微笑到最大 |
| **Frown** | 不皱眉 | 皱眉到最大 |
| **BlinkL/R** | 眼睛睁开 | 眼睛完全闭上 |
| **BrowUp** | 眉毛正常 | 眉毛抬起到最高 |

### Head Rotation 值范围：-30° 到 +30°

| 轴 | 负值 | 正值 |
|----|-----|------|
| **Yaw** | 左转 | 右转 |
| **Pitch** | 低头 | 抬头 |
| **Roll** | 左倾 | 右倾 |

---

## 性能调试

### 查看 FPS

终端输出第一行总是显示：
```
[Status] FPS: 30.0 | ...
```

**期望值：** 25-30 FPS

**如果 FPS < 20：**
1. 降低摄像头分辨率（在 `config.json` 中修改）
2. 关闭调试窗口（按 's'）
3. 关闭其他占用 CPU 的程序

---

## 常见调试场景

### 场景 1：所有参数都不变化
**可能原因：**
- 没有检测到脸部
- 摄像头没有打开
- MediaPipe 模型加载失败

**检查：**
- 调试窗口是否显示 "NO FACE DETECTED"（红色）
- 终端是否显示 "NO FACE"

**解决：**
- 确保脸部在画面中央
- 改善光线
- 检查摄像头是否被其他程序占用

---

### 场景 2：只有头部转动工作，面部表情不工作
**可能原因：**
- MediaPipe 模型版本问题
- blendshapes 输出被禁用

**检查：**
- 模型文件是否完整下载
- 文件名是否正确：`face_landmarker_v2_with_blendshapes.task`

---

### 场景 3：Python 值正常，Unity 没有反应
**说明：** 网络或 Unity 映射问题

**检查：**
1. Unity 是否在运行
2. Unity DebugFaceVisualizer 是否显示 "CONNECTED"
3. Unity 参数映射是否正确

---

## 高级调试：查看原始 JSON 数据

如果需要查看发送到 Unity 的原始数据，修改 `network_sender.py`：

```python
# 在 send_face_data() 方法中添加：
print(json_data)  # 打印发送的 JSON
```

会输出类似：
```json
{
  "timestamp": 1234567890.123,
  "faceDetected": true,
  "headRotation": {"yaw": 15.5, "pitch": -10.2, "roll": 2.1},
  "blendshapes": {
    "jawOpen": 0.456,
    "mouthSmileLeft": 0.234,
    ...
  }
}
```

---

## 小贴士

1. **先测试 Python 端**：确保所有参数在调试窗口中正常变化
2. **再测试 Unity 端**：使用 Unity DebugFaceVisualizer 确认数据接收
3. **最后调整映射**：在 Unity Inspector 中微调参数映射

按这个顺序排查，可以快速定位问题在哪一层！
