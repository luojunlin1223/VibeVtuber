# Live2D 参数映射配置指南

## 概述

现在你可以在 Unity Inspector 面板上直接配置 MediaPipe 数据（包括 blendshapes 和头部旋转）到 Live2D 参数的映射，无需修改代码。

**重要更新:** 头部旋转配置已整合到统一的 Parameter Mappings 中，不再有单独的配置区域。

## Inspector 配置说明

### 参数映射列表 (Parameter Mappings)

**✨ 统一配置所有参数（包括头部旋转和 blendshapes）**

这是一个可以添加/删除的列表，每个映射项包含：

```
Parameter Mappings
├─ [0] Left Eye Blink
│  ├─ Description: "Left Eye Blink" (说明文字)
│  ├─ Enabled: ✓ (启用/禁用此映射)
│  ├─ Live2D Parameter: "ParamEyeLOpen" (目标 Live2D 参数)
│  ├─ Source Blendshapes: (源 MediaPipe blendshapes)
│  │  └─ [0] "eyeBlinkLeft"
│  ├─ Combine Mode: Invert (组合模式)
│  ├─ Multiplier: 1.0 (倍数)
│  ├─ Offset: 0.0 (偏移)
│  ├─ Clamp Min: 0.0 (最小值)
│  ├─ Clamp Max: 1.0 (最大值)
│  └─ Use Smoothing: ✓ (是否平滑)
└─ ...
```

---

## 特殊源名称：头部旋转

**重要:** 除了 blendshapes，你还可以使用以下特殊源名称来映射头部旋转：

| 源名称 | 说明 | 数据来源 |
|-------|------|---------|
| `headYaw` | 左右转头 | data.headRotation.yaw（-90° 到 +90°）|
| `headPitch` | 上下点头 | data.headRotation.pitch（-90° 到 +90°）|
| `headRoll` | 左右歪头 | data.headRotation.roll（-90° 到 +90°）|

**示例：配置头部旋转**

```
Parameter Mapping:
├─ Description: "Head Yaw"
├─ Enabled: ✓
├─ Live2D Parameter: "ParamAngleX"
├─ Source Blendshapes: ["headYaw"]  ← 特殊源名称！
├─ Combine Mode: Direct
├─ Multiplier: 1.0
├─ Offset: 0.0
├─ Clamp Min: -30.0
├─ Clamp Max: 30.0
└─ Use Smoothing: ✓
```

**注意:**
- 这些源名称不区分大小写（`headYaw` 和 `HeadYaw` 都可以）
- 头部旋转的单位是度（degrees）
- 建议 Clamp 范围设置为 -30 到 30（Live2D 典型范围）

详细说明请查看 `HEAD_ROTATION_MAPPING.md`

---

## 组合模式 (Combine Mode) 说明

| 模式 | 说明 | 用途 |
|-----|------|-----|
| **Direct** | 直接使用第一个 blendshape 的值 | 单个参数映射 |
| **Average** | 多个 blendshape 的平均值 | 左右眼/左右嘴角的平均 |
| **Sum** | 多个 blendshape 的总和 | 组合多个影响因素 |
| **Max** | 取最大值 | 取多个值中最大的 |
| **Min** | 取最小值 | 取多个值中最小的 |
| **Invert** | 反转值 (1.0 - value) | 眼睛眨眼（MediaPipe 1=闭，Live2D 1=开）|
| **Difference** | 第一个减第二个 | 计算差值（如微笑-皱眉）|

---

## 常见配置示例

### 示例 1: 眼睛眨眼（反转）

```
Description: "Left Eye Blink"
Live2D Parameter: "ParamEyeLOpen"
Source Blendshapes: ["eyeBlinkLeft"]
Combine Mode: Invert
Multiplier: 1.0
```

**原因：** MediaPipe 的 `eyeBlinkLeft` = 1 表示闭眼，但 Live2D 的 `ParamEyeLOpen` = 1 表示睁眼，所以要反转。

---

### 示例 2: 眼睛左右看（平均）

```
Description: "Eye Look Right"
Live2D Parameter: "ParamEyeBallX"
Source Blendshapes: ["eyeLookOutRight", "eyeLookInLeft"]
Combine Mode: Average
Multiplier: 1.0
```

**原因：** 右眼向右看 + 左眼向右看 = 整体向右看，取平均值更自然。

---

### 示例 3: 眉毛上扬（总和）

```
Description: "Left Brow Up"
Live2D Parameter: "ParamBrowLY"
Source Blendshapes: ["browInnerUp", "browOuterUpLeft"]
Combine Mode: Sum
Multiplier: 1.0
```

**原因：** 内眉上扬 + 外眉上扬 = 整个眉毛上扬，累加效果更明显。

---

### 示例 4: 微笑-皱眉（差值）

```
Description: "Mouth Form"
Live2D Parameter: "ParamMouthForm"
Source Blendshapes: ["mouthSmileLeft", "mouthSmileRight"]
Combine Mode: Average
Multiplier: 1.0

（再添加一个相反的）
Description: "Mouth Form (Frown)"
Live2D Parameter: "ParamMouthForm"
Source Blendshapes: ["mouthFrownLeft", "mouthFrownRight"]
Combine Mode: Average
Multiplier: -1.0  ← 注意是负数！
```

**原因：** 微笑是正值，皱眉是负值，控制同一个参数。

---

## 操作步骤

### 1. 查看你的 Live2D 模型有哪些参数

在 Inspector 中右键点击 `Live2DFaceController` 组件，选择：
```
右键菜单 → Log All Live2D Parameters
```

Unity Console 会输出类似：
```
=== Live2D Parameters (25) ===
ParamAngleX | min: -30 | max: 30 | default: 0
ParamAngleY | min: -30 | max: 30 | default: 0
ParamEyeLOpen | min: 0 | max: 1 | default: 1
MyCustomEye_L | min: 0 | max: 2 | default: 1  ← 自定义参数！
...
```

### 2. 查看 MediaPipe 有哪些 blendshapes

右键菜单 → Log All MediaPipe Blendshapes

Console 输出：
```
=== MediaPipe ARKit Blendshapes (52 total) ===
- eyeBlinkLeft
- eyeBlinkRight
- jawOpen
- mouthSmileLeft
...
```

### 3. 添加新的映射

1. 在 Inspector 的 **Parameter Mappings** 列表中点击 `+` 按钮
2. 展开新添加的元素
3. 填写：
   - **Description**: 给这个映射起个名字（如 "我的自定义眼睛"）
   - **Live2D Parameter**: 填入你的 Live2D 参数名（从步骤1复制）
   - **Source Blendshapes**: 点击 `+` 添加 MediaPipe blendshape 名称
   - **Combine Mode**: 选择组合方式
   - **Multiplier**: 调整灵敏度（1.0 正常，-1.0 反转，2.0 加倍）
   - **Clamp Min/Max**: 设置输出范围

### 4. 测试调整

1. 运行 Python 脸部追踪：`python main.py`
2. Unity 点击 Play
3. 启用 **Debug** → **Log Parameter Updates** 查看实时数值
4. 调整 `Multiplier` 和 `Clamp Min/Max` 直到效果满意
5. 可以随时勾掉 `Enabled` 来禁用某个映射测试

---

## 调试技巧

### 问题：参数没反应

**检查：**
1. `Enabled` 是否勾选 ✓
2. `Live2D Parameter` 名称是否正确（区分大小写！）
3. `Source Blendshapes` 名称是否正确
4. 启用 `Log Parameter Updates` 查看是否有警告

### 问题：方向反了

**解决：** 把 `Multiplier` 从 `1.0` 改成 `-1.0`

### 问题：幅度太小/太大

**解决：** 调整 `Multiplier`：
- 太小 → 增加到 `1.5` 或 `2.0`
- 太大 → 减少到 `0.5` 或 `0.3`

### 问题：动作太抖

**解决：**
1. 确保 `Use Smoothing` 勾选 ✓
2. 增加全局 `Smoothing Factor`（0.3 → 0.5）

---

## 高级技巧

### 技巧 1: 一个 Live2D 参数受多个 blendshape 影响

可以创建多个映射指向同一个 Live2D 参数：

```
[0] Mouth Open (jaw)
    Live2D Parameter: "ParamMouthOpenY"
    Source: ["jawOpen"]
    Multiplier: 1.0

[1] Mouth Wide (stretch)
    Live2D Parameter: "ParamMouthOpenY"  ← 同一个参数！
    Source: ["mouthStretchLeft", "mouthStretchRight"]
    Combine Mode: Average
    Multiplier: 0.5  ← 影响较小
```

两个映射会**累加**到同一个参数上。

### 技巧 2: 禁用默认映射

如果你想完全自定义，可以：
1. 清空 `Parameter Mappings` 列表（选中所有按 `-` 删除）
2. 添加你自己的映射

或者：
1. 不删除，只把不需要的映射的 `Enabled` 取消勾选

### 技巧 3: 为不同模型创建预设

1. 配置好映射后，在 Scene 中复制整个 Live2D 模型 GameObject
2. 或者创建 Prefab 保存配置
3. 不同模型使用不同的配置

---

## 常见 Live2D 参数名称对照表

| 功能 | 标准参数名 | 可能的变体 |
|-----|----------|----------|
| 头部左右 | ParamAngleX | Angle_X, HeadX, Head_Yaw |
| 头部上下 | ParamAngleY | Angle_Y, HeadY, Head_Pitch |
| 头部倾斜 | ParamAngleZ | Angle_Z, HeadZ, Head_Roll |
| 左眼睁开 | ParamEyeLOpen | Eye_L_Open, EyeOpenL |
| 右眼睁开 | ParamEyeROpen | Eye_R_Open, EyeOpenR |
| 眼球 X | ParamEyeBallX | EyeBall_X, Eye_X |
| 眼球 Y | ParamEyeBallY | EyeBall_Y, Eye_Y |
| 嘴巴开合 | ParamMouthOpenY | Mouth_Open, MouthY |
| 嘴巴形状 | ParamMouthForm | Mouth_Form, MouthShape |
| 左眉毛 Y | ParamBrowLY | Brow_L_Y, BrowL |
| 右眉毛 Y | ParamBrowRY | Brow_R_Y, BrowR |

**提示：** 使用 `Log All Live2D Parameters` 查看你的模型实际使用的参数名！

---

## 总结

✅ 所有映射都可以在 Inspector 中配置
✅ 无需修改代码
✅ 支持多种组合模式
✅ 可随时启用/禁用/调整
✅ 使用右键菜单快速查看参数列表

祝你配置顺利！🎭
