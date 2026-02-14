# ADR 001: UDP + JSON for Python-Unity Face Tracking Communication

**Date:** 2026-02-14

**Status:** Accepted

## Context

Need real-time communication between Python MediaPipe face tracker (30 FPS) and Unity for Live2D character animation. Must transmit 52 blendshapes + head rotation with minimal latency.

## Decision

Use **UDP sockets** with **JSON** payloads on localhost port 11111.

## Alternatives Considered

1. **TCP + JSON**
   - ❌ Higher latency due to handshaking and retransmission
   - ❌ Packet ordering guarantees unnecessary for real-time data
   - ✅ Reliable delivery (not needed - missing 1 frame @ 30 FPS is acceptable)

2. **WebSocket**
   - ❌ Additional dependency (websocket library)
   - ❌ Overhead of HTTP upgrade handshake
   - ✅ Easier debugging (browser tools)

3. **Binary Protocol (MessagePack, Protobuf)**
   - ✅ Smaller payload (~500 bytes vs ~2KB JSON)
   - ❌ Harder to debug (can't read raw packets)
   - ❌ Additional serialization complexity
   - ❌ Performance gain negligible for 2KB @ 30 FPS on localhost

4. **Shared Memory**
   - ✅ Fastest possible IPC
   - ❌ Platform-specific implementation
   - ❌ Complex synchronization
   - ❌ Tight coupling between processes

## Rationale

**Why UDP:**
- Latency-critical: Target <50ms total (camera → Unity display)
- Packet loss acceptable: 1-2 dropped frames @ 30 FPS imperceptible
- No ordering needed: Each packet is independent (latest state)
- Simpler than TCP: No connection management, no buffering

**Why JSON:**
- Development speed: Easy to debug (inspect raw packets)
- Human-readable: Can log/analyze data streams
- Built-in support: Python `json` module, Unity `JsonUtility`
- Performance adequate: 2KB @ 30 FPS = 60 KB/s (negligible on localhost)
- Flexibility: Easy to add/remove fields during development

**Why localhost only:**
- Security: No network exposure
- Performance: No actual network overhead
- Simplicity: No firewall configuration

## Consequences

**Positive:**
- ✅ Achieved <50ms latency (typically 30-40ms)
- ✅ Easy debugging (can read JSON in logs)
- ✅ Simple error handling (drop bad packets, continue)
- ✅ No connection state to manage

**Negative:**
- ❌ No delivery guarantee (acceptable trade-off)
- ❌ Slightly larger payload than binary (2KB vs ~500 bytes)
- ❌ JSON parsing overhead (mitigated with custom parser)

**Mitigations:**
- Optimized JSON parser to avoid garbage collection
- Background thread for UDP receive (non-blocking)
- EMA smoothing compensates for occasional packet loss

## Future Considerations

If performance becomes an issue:
1. Switch to MessagePack (drop-in replacement, 4x smaller)
2. Implement simple binary protocol (header + floats)
3. Use shared memory for same-machine deployment

Currently: No changes needed, performance excellent.
