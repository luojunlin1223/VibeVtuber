# Unity Inspector 调试指南

## 功能说明

现在 `FaceDataReceiver` 组件会在 Inspector 面板上实时显示所有接收到的面部追踪参数，无需打开任何 UI 窗口！

## 如何使用

### 步骤 1：选中组件

在 Unity Hierarchy 中选中有 `FaceDataReceiver` 组件的 GameObject（通常是 "FaceTrackingManager"）

### 步骤 2：查看 Inspector

在 Inspector 面板中，你会看到：

```
Face Data Receiver (Script)
├─ Network Settings
│  └─ Port: 11111
│
├─ Inspector Debug Info
│  ├─ Show Debug Info: ✓        ← 勾选以显示调试信息
│  ├─ Connection Status: "CONNECTED (30.0 FPS)"
│  ├─ Fps Info: "30.0 FPS | Total: 1234"
│  └─ Head Rotation: "Yaw: 15.3°, Pitch: -8.2°, Roll: 2.1°"
│
├─ Mouth Parameters
│  ├─ Jaw Open: ▮▮▮▮▮▯▯▯▯▯ 0.456  ← 滑块实时显示
│  ├─ Mouth Smile: ▮▮▯▯▯▯▯▯▯▯ 0.234
│  ├─ Mouth Frown: ▯▯▯▯▯▯▯▯▯▯ 0.012
│  └─ Mouth Pucker: ▮▯▯▯▯▯▯▯▯▯ 0.089
│
├─ Eye Parameters
│  ├─ Eye Blink Left: ▯▯▯▯▯▯▯▯▯▯ 0.001
│  ├─ Eye Blink Right: ▯▯▯▯▯▯▯▯▯▯ 0.002
│  ├─ Eye Look X: ▯▯▯▯▯▮▯▯▯▯ 0.15 (负=左, 正=右)
│  └─ Eye Look Y: ▯▯▯▯▯▮▯▯▯▯ 0.12 (负=下, 正=上)
│
└─ Eyebrow Parameters
   ├─ Brow Inner Up: ▮▯▯▯▯▯▯▯▯▯ 0.123
   └─ Brow Down: ▯▯▯▯▯▯▯▯▯▯ 0.023
```

## 参数说明

### Inspector Debug Info（调试信息）

| 字段 | 说明 |
|-----|------|
| **Show Debug Info** | 勾选以启用 Inspector 调试显示 |
| **Connection Status** | 连接状态（CONNECTED 或 WAITING FOR DATA）+ FPS |
| **Fps Info** | 当前帧率 + 接收到的总消息数 |
| **Head Rotation** | 头部旋转角度（度数） |

### Mouth Parameters（嘴巴参数）

| 参数 | 范围 | 说明 |
|-----|------|------|
| **Jaw Open** | 0.0 - 1.0 | 嘴巴开合（0=闭，1=张到最大）|
| **Mouth Smile** | 0.0 - 1.0 | 微笑程度 |
| **Mouth Frown** | 0.0 - 1.0 | 皱眉/不开心程度 |
| **Mouth Pucker** | 0.0 - 1.0 | 嘟嘴程度 |

### Eye Parameters（眼睛参数）

| 参数 | 范围 | 说明 |
|-----|------|------|
| **Eye Blink Left** | 0.0 - 1.0 | 左眼眨眼（0=睁开，1=闭上）|
| **Eye Blink Right** | 0.0 - 1.0 | 右眼眨眼 |
| **Eye Look X** | -1.0 - 1.0 | 眼睛左右看（负=左，正=右）|
| **Eye Look Y** | -1.0 - 1.0 | 眼睛上下看（负=下，正=上）|

### Eyebrow Parameters（眉毛参数）

| 参数 | 范围 | 说明 |
|-----|------|------|
| **Brow Inner Up** | 0.0 - 1.0 | 眉毛内侧上扬 |
| **Brow Down** | 0.0 - 1.0 | 眉毛下压/皱眉 |

---

## 使用场景

### 场景 1：检查连接状态

查看 **Connection Status**：
- ✅ `CONNECTED (30.0 FPS)` → 正常连接
- ⚠️ `WAITING FOR DATA` → 未收到数据

**如果显示 WAITING FOR DATA：**
1. 检查 Python 是否运行：`python main.py`
2. 检查端口是否匹配（11111）
3. 尝试右键组件 → `Reconnect`

---

### 场景 2：测试嘴巴动作是否被捕捉

1. **张嘴** → 观察 `Jaw Open` 滑块
   - 应该从 `0.0` 增加到 `0.5-0.8`
   - 如果不变化 → 问题在 Python/MediaPipe 端

2. **微笑** → 观察 `Mouth Smile` 滑块
   - 应该增加
   - 如果变化但 Live2D 不动 → 参数映射问题

3. **嘟嘴** → 观察 `Mouth Pucker` 滑块

---

### 场景 3：调试 Live2D 参数映射

**步骤：**
1. 在 Inspector 中观察参数值（如 `Jaw Open = 0.456`）
2. 切换到 `Live2DFaceController` 组件
3. 启用 **Debug** → **Log Parameter Updates** ✓
4. 查看 Console 输出：
   ```
   [Live2D] ParamMouthOpenY = 0.456
   ```
5. 如果 Console 显示的值和 Inspector 一致 → 网络正常
6. 如果 Live2D 模型不动 → 参数名不对

---

### 场景 4：对比 Python 和 Unity 的值

**Python 端（调试窗口）：**
```
JawOpen: 0.456  ████████░░
```

**Unity 端（Inspector）：**
```
Jaw Open: ▮▮▮▮▮▯▯▯▯▯ 0.456
```

**如果两边的值不一致：**
- Python 有值，Unity 是 0 → 网络连接问题
- 两边值都有但不同 → 可能是延迟（正常）

---

## 快速诊断流程

```
1. 查看 Connection Status
   ├─ WAITING FOR DATA → 检查 Python 是否运行
   └─ CONNECTED → 继续

2. 张嘴，观察 Jaw Open 滑块
   ├─ 不动 → Python/MediaPipe 问题
   └─ 移动 → 继续

3. 查看 Live2D 模型是否张嘴
   ├─ 不动 → 检查参数映射（Parameter Mappings）
   └─ 移动 → 工作正常！
```

---

## 优势

### ✅ 相比 DebugFaceVisualizer UI

| 特性 | Inspector 调试 | DebugFaceVisualizer UI |
|-----|---------------|----------------------|
| 无需额外 UI | ✓ | ✗ 需要 Canvas |
| Play 模式下可见 | ✓ | ✓ |
| 编辑模式下可见 | ✗ | ✗ |
| 实时滑块显示 | ✓ | ✗ 只有文本 |
| 占用屏幕空间 | 无 | 有 |
| 需要按键切换 | ✗ | ✓ (F1) |

### ✅ 相比 Python 调试窗口

| 特性 | Inspector | Python 窗口 |
|-----|----------|-----------|
| 在 Unity 内查看 | ✓ | ✗ |
| 确认网络传输 | ✓ | ✗ |
| 对比映射结果 | ✓ | ✗ |

---

## 小技巧

### 技巧 1: 锁定 Inspector

为了方便对比多个组件：
1. 选中 `FaceDataReceiver`
2. 点击 Inspector 右上角的 **🔒 锁定** 图标
3. 现在可以选择其他对象（如 Live2D 模型）
4. 打开新的 Inspector 窗口（右键 Inspector 标签 → Add Tab → Inspector）
5. 两个 Inspector 可以同时显示不同组件

### 技巧 2: 隐藏不需要的参数

如果你只关心嘴巴参数：
1. 在脚本中注释掉其他 `[Header]` 部分
2. 或者折叠 Inspector 中的其他部分

### 技巧 3: 录制参数变化

Unity 可以录制 Inspector 中的值：
1. Window → General → Recorder
2. 开始录制
3. 做表情
4. 回放查看参数变化曲线

---

## 禁用调试显示

如果不需要调试信息（发布时）：

在 Inspector 中**取消勾选** `Show Debug Info`

这样可以节省一点性能（虽然影响很小）。

---

## 总结

现在你有 **三层调试工具**：

1. **Python 调试窗口** → 检查 MediaPipe 是否正确捕捉
2. **Unity Inspector** → 检查网络传输是否正常
3. **Unity DebugFaceVisualizer UI** → 额外的可视化（可选）

推荐工作流程：
1. 先看 Python 窗口确认捕捉正常
2. 再看 Unity Inspector 确认接收正常
3. 最后调整 Live2D 参数映射

这样可以快速定位问题在哪一层！🎯
