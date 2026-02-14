# Fixing Live2D Parameter Mappings

## Problem
Only mouth parameters are working on your Live2D model, but eyes, eyebrows, and other facial features aren't responding to face tracking data.

## Root Cause
Your Live2D model uses different parameter names than the standard ARKit convention. The default mappings are configured for standard Cubism parameter names like `ParamEyeLOpen`, but your model might use names like `Eye_L_Open`, `MyCharacter_LeftEye`, etc.

## Diagnosis Confirmed
✅ **FaceDataReceiver is working** - Inspector debug panel shows all blendshapes updating correctly
✅ **Pipeline is functional** - Mouth opening proves Python → UDP → Unity → Live2D works
❌ **Parameter names mismatch** - Eyes/eyebrows mappings point to non-existent parameters

---

## Step-by-Step Fix

### Step 1: Get Your Model's Actual Parameter Names

1. In Unity, select the GameObject with your Live2D model
2. Find the **Live2DFaceController** component in the Inspector
3. **Right-click** on the component header
4. Select **"Log All Live2D Parameters"** from the context menu
5. Open the **Console** window (Window > General > Console)
6. You should see output like:
   ```
   Live2D Parameters (25 total):
   [0] ParamAngleX (current: 0.0)
   [1] ParamAngleY (current: 0.0)
   [2] ParamEyeLOpen (current: 1.0)
   [3] ParamEyeROpen (current: 1.0)
   ...
   ```
7. **Copy this entire list** - you'll use it as a reference

### Step 2: Identify Your Model's Eye Parameters

Look through the parameter list and find parameters related to:

**Eye Opening:**
- Standard: `ParamEyeLOpen`, `ParamEyeROpen`
- Common alternatives: `Eye_L_Open`, `Eye_R_Open`, `LeftEyeOpen`, `RightEyeOpen`
- VRoid: `EyeOpenLeft`, `EyeOpenRight`

**Eye Position (gaze):**
- Standard: `ParamEyeBallX`, `ParamEyeBallY`
- Common alternatives: `EyeX`, `EyeY`, `EyeBallPosX`, `EyeBallPosY`

**Eyebrows:**
- Standard: `ParamBrowLY`, `ParamBrowRY`, `ParamBrowLX`, `ParamBrowRX`
- Common alternatives: `BrowLeft`, `BrowRight`, `EyebrowL`, `EyebrowR`

**Mouth:**
- Standard: `ParamMouthOpenY`, `ParamMouthForm`
- Common alternatives: `MouthOpen`, `MouthOpenY`, `MouthSmile`

### Step 3: Update Parameter Mappings in Inspector

1. In Unity Inspector, scroll down to the **Parameter Mappings** section in Live2DFaceController
2. For each mapping that isn't working, update the **Live2D Parameter** field:

#### Example: Fixing Eye Blink Left

**Before (not working):**
```
Description: Eye Blink Left
Enabled: ✓
Live2D Parameter: ParamEyeLOpen  ← Wrong name for your model
Source Blendshapes: eyeBlinkLeft
Combine Mode: Invert
Multiplier: 1.0
```

**After (fixed):**
```
Description: Eye Blink Left
Enabled: ✓
Live2D Parameter: Eye_L_Open  ← Your model's actual parameter name
Source Blendshapes: eyeBlinkLeft
Combine Mode: Invert
Multiplier: 1.0
```

### Step 4: Common Mappings to Update

Here are the mappings you'll likely need to fix:

| Description | Source Blendshape(s) | Find Parameter Like | Combine Mode | Notes |
|-------------|---------------------|---------------------|--------------|-------|
| **Eye Blink Left** | eyeBlinkLeft | Eye, Left, Open, L | Invert | 1.0 - value (MediaPipe 1=closed, Live2D 1=open) |
| **Eye Blink Right** | eyeBlinkRight | Eye, Right, Open, R | Invert | 1.0 - value |
| **Eye Look Horizontal** | eyeLookOutLeft, eyeLookInLeft | Eye, X, Ball, Horizontal | Average or Difference | May need sensitivity tuning |
| **Eye Look Vertical** | eyeLookUpLeft, eyeLookDownLeft | Eye, Y, Ball, Vertical | Average or Difference | May need sensitivity tuning |
| **Eyebrow Left Up** | browInnerUp, browOuterUpLeft | Brow, Left, Up, Y | Average | Raises left eyebrow |
| **Eyebrow Right Up** | browInnerUp, browOuterUpRight | Brow, Right, Up, Y | Average | Raises right eyebrow |
| **Mouth Form (Smile)** | mouthSmile, mouthFrown | Mouth, Form, Smile | Difference | Smile - Frown |

### Step 5: Test Each Parameter

1. Enable **Log Parameter Updates** in the Debug section of Live2DFaceController
2. Play the scene
3. Make specific facial expressions:
   - **Blink left eye** → Should see "Setting [YourEyeParam] to X.XX" in Console
   - **Blink right eye** → Check right eye parameter
   - **Raise eyebrows** → Check eyebrow parameters
   - **Smile** → Check mouth form parameter
4. Watch your Live2D model - facial features should respond

### Step 6: Fine-Tune Sensitivity

If parameters are working but too sensitive or not sensitive enough:

1. Adjust **Multiplier**:
   - Too subtle? Increase to 1.5 or 2.0
   - Too exaggerated? Decrease to 0.5 or 0.7

2. Adjust **Offset**:
   - Eyes always half-closed? Add positive offset (+0.2)
   - Eyebrows always raised? Add negative offset (-0.1)

3. Adjust **Clamp Min/Max**:
   - Prevent unrealistic values (e.g., eyes shouldn't open beyond 1.0)

---

## Troubleshooting

### "I can't find an eye parameter in my model's list"

**Check for:**
- Variations: `Eye`, `Pupil`, `Eyelid`, `Blink`
- Language differences: `目` (Japanese for eye)
- Character name prefix: `Haru_Eye_L_Open`

**Last resort:**
- Open your model's `.model3.json` file in a text editor
- Search for `"Id"` fields in the `"Parameters"` section

### "Eye parameters exist but still not working"

1. **Check Combine Mode:**
   - Most eye parameters need `Invert` mode (MediaPipe 1=closed, Live2D 1=open)
   - Try toggling between `Direct` and `Invert`

2. **Check Source Blendshapes:**
   - Make sure the MediaPipe blendshape name is spelled correctly
   - Right-click component → "Log All MediaPipe Blendshapes" to see available names

3. **Check FaceDataReceiver:**
   - Confirm the blendshape value is actually changing in the Inspector debug panel
   - If it's always 0, the issue is in the Python/network layer

### "Eyes work but look in the wrong direction"

**Try different Combine Modes:**
- `Direct`: Uses first blendshape directly
- `Average`: Average of left/right eye look
- `Difference`: OutLeft - InRight (for horizontal gaze)
- `Invert`: 1.0 - value (flip direction)

**Adjust Multiplier:**
- Negative multiplier (-1.0) flips the direction
- Values like -30.0 might be needed for angle parameters

### "Eyebrows are flipped (raise = lower)"

- Change Combine Mode from `Average` to `Invert`
- Or set Multiplier to -1.0

---

## Example: VRoid Model Configuration

If you're using a VRoid model, here are typical parameter names:

```
Eye Blink Left:
  Live2D Parameter: EyeOpenLeft
  Combine Mode: Invert

Eye Blink Right:
  Live2D Parameter: EyeOpenRight
  Combine Mode: Invert

Eye Look Horizontal:
  Live2D Parameter: EyeBallX
  Combine Mode: Difference
  Source: eyeLookOutLeft, eyeLookInLeft

Eye Look Vertical:
  Live2D Parameter: EyeBallY
  Combine Mode: Difference
  Source: eyeLookUpLeft, eyeLookDownLeft

Mouth Open:
  Live2D Parameter: MouthOpenY
  Combine Mode: Direct
```

---

## Quick Reference: Combine Modes

- **Direct**: Use first source blendshape as-is → `value = source[0]`
- **Average**: Average all sources → `value = (s1 + s2 + ...) / count`
- **Sum**: Add all sources → `value = s1 + s2 + ...`
- **Max**: Use highest value → `value = max(s1, s2, ...)`
- **Min**: Use lowest value → `value = min(s1, s2, ...)`
- **Invert**: Flip value → `value = 1.0 - source[0]`
- **Difference**: Subtract → `value = source[0] - source[1]`

---

## Next Steps

1. ✅ Get your model's parameter names (Step 1)
2. ✅ Update all parameter mappings (Steps 2-3)
3. ✅ Test each facial feature (Step 5)
4. ✅ Fine-tune sensitivity (Step 6)
5. 🎯 Enjoy your working face tracking!

Once all parameters are mapped correctly, you should have full facial control over your Live2D model with real-time tracking.
