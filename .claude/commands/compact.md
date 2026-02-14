# /compact — Compress Context Before /clear

Run this when the context window is getting full. After this completes, run /clear (built-in), then /iterate to resume.

Execute these steps in order:

1. **Get timestamp:**
   ```
   powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"
   ```
   Store as TIMESTAMP. Extract DATE.

2. **Cold-start check.** Same as /checkpoint step 2 — create memory-bank/ structure if missing.

3. **Create today's session log if needed.** Same as /checkpoint step 4.

4. **Append a COMPACT session log entry** to `memory-bank/session-logs/DATE.md`:
   ```
   ---
   ## Session Entry — TIMESTAMP [COMPACT]

   **Focus:** [one-sentence summary of what was being worked on when /compact was invoked]

   **Completed:**
   - [everything finished so far in this session]

   **In Progress (resume here):**
   - [CRITICAL: Specific description of exactly what was being done. Include file paths, which step of a process was being executed, and what the next action should be. The next session must resume from this exact point.]

   **Blocked / Notes:**
   - [any blockers or context that would otherwise be lost]

   **Files touched:**
   - [files modified so far in this session]

   ---
   ```
   The `[COMPACT]` marker in the heading and the `In Progress (resume here)` section distinguish this from a regular checkpoint entry.

5. **Rewrite `memory-bank/progress.md`** using the same structure as /checkpoint step 7, but prepend this note at the very top:
   ```
   > **COMPACT IN PROGRESS** — Conversation was compacted at TIMESTAMP.
   > Resume from the [COMPACT] entry in `session-logs/DATE.md`.
   ```

6. **ADR check.** Same logic as /checkpoint step 6 — create any pending ADRs before context is lost.

7. **Update architecture.md / tech-stack.md** if needed (same as /checkpoint step 8).

8. **Tell the user:** "Memory saved. Commit `memory-bank/` to git when ready (suggested message: `chore(memory-bank): compact TIMESTAMP — [summary]`). Then run /clear to reset the context window, followed by /iterate to resume."
