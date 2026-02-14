# ADR 002: Inspector-Configurable Parameter Mappings

**Date:** 2026-02-14

**Status:** Accepted

## Context

Different Live2D models use different parameter names and conventions:
- Standard: `ParamEyeLOpen`, `ParamMouthOpenY`
- Custom: `Eye_L_Open`, `MyCharacter_Mouth`
- Ranges vary: Some use 0-1, others 0-2 or -1 to 1

Original hardcoded approach required code changes for each model.

## Decision

Implement fully configurable parameter mappings in Unity Inspector using serialized C# classes:
- `ParameterMapping` class with configurable source blendshapes, target Live2D parameter, combine mode, multiplier, offset, clamps
- 7 combine modes: Direct, Average, Sum, Max, Min, Invert, Difference
- Per-parameter smoothing toggle
- Enable/disable individual mappings

## Alternatives Considered

1. **JSON Configuration File**
   - ✅ Can be version controlled separately
   - ✅ Easy to share between projects
   - ❌ Requires file I/O and parsing at runtime
   - ❌ No Unity Editor validation
   - ❌ Harder to edit (external tool vs Inspector)

2. **ScriptableObject Assets**
   - ✅ Unity-native approach
   - ✅ Can create multiple mapping profiles
   - ❌ Extra asset management complexity
   - ❌ Requires creating/switching assets

3. **Code Generation from Model**
   - ✅ Automatic mapping detection
   - ❌ Complex implementation (parse .model3.json)
   - ❌ Fragile (breaks with model updates)
   - ❌ Can't handle custom logic (like combining blendshapes)

4. **Hardcoded with Preprocessor Directives**
   - ✅ Zero runtime overhead
   - ❌ Requires recompilation
   - ❌ Hard to maintain (multiple #ifdef blocks)
   - ❌ Can't switch models at runtime

## Rationale

**Inspector Configuration Wins Because:**
- **User-friendly**: Artists/non-programmers can configure without code
- **Immediate feedback**: Changes visible in Inspector while testing
- **Unity-native**: Uses familiar Unity serialization system
- **Flexible**: Supports complex mappings (averaging, inverting, summing)
- **Per-model**: Each Live2D model GameObject can have different settings
- **Runtime switchable**: Can change mappings without recompiling

**Design Choices:**
- `[Serializable]` classes for Inspector editing
- `List<ParameterMapping>` for dynamic adding/removing
- `enum CombineMode` for clear dropdown selection
- Default mappings auto-initialize on first run
- Context menu helpers: "Log All Live2D Parameters", "Log All MediaPipe Blendshapes"

## Consequences

**Positive:**
- ✅ Works with any Live2D model (just configure parameter names)
- ✅ No code changes needed for new models
- ✅ Easy to experiment (tweak multipliers, try different combine modes)
- ✅ Self-documenting (parameter names visible in Inspector)
- ✅ Can disable problematic mappings without deleting

**Negative:**
- ❌ Verbose Inspector (can have 20+ mapping entries)
- ❌ Manual configuration required for each model
- ❌ Possible user error (typos in parameter names)

**Mitigations:**
- Headers/tooltips make Inspector readable
- "Log All Live2D Parameters" shows available names (copy-paste)
- Default mappings provide working template
- Validation (shows warnings for missing parameters)

## Implementation Details

```csharp
[Serializable]
public class ParameterMapping
{
    public string description;
    public bool enabled = true;
    public string live2DParameter;
    public List<string> sourceBlendshapes;
    public CombineMode combineMode;
    public float multiplier = 1f;
    public float offset = 0f;
    public float clampMin = 0f;
    public float clampMax = 1f;
    public bool useSmoothing = true;
}
```

Supports complex mappings like:
- Eye blink (invert: MediaPipe 1=closed, Live2D 1=open)
- Eye look (average left+right for combined direction)
- Mouth form (smile - frown = emotional expression)

## Future Enhancements

- Import/export mapping presets as JSON
- Auto-detect common parameter naming patterns
- Mapping templates library (VRoid, Cubism default, etc.)
- Visual mapping editor (drag-drop connections)
