# /checkpoint — Save Current Progress

Execute these steps in order:

1. **Get timestamp.** Run:
   ```
   powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"
   ```
   Store the result as TIMESTAMP (e.g. `2026-01-31 14:35`). Extract the date as DATE (e.g. `2026-01-31`).

2. **Cold-start check.** If `memory-bank/` does not exist, create the full directory structure:
   - `memory-bank/progress.md`
   - `memory-bank/architecture.md`
   - `memory-bank/tech-stack.md`
   - `memory-bank/session-logs/`
   - `memory-bank/decisions/`
   Use the project's CLAUDE.md as reference for initial content in architecture.md and tech-stack.md.

3. **Read current state.** Read:
   - `memory-bank/progress.md`
   - The most recent file in `memory-bank/session-logs/` (if any)

4. **Create today's session log if needed.** If `memory-bank/session-logs/DATE.md` does not exist, create it as an empty file.

5. **Append session log entry** to `memory-bank/session-logs/DATE.md`:
   ```
   ---
   ## Session Entry — TIMESTAMP

   **Focus:** [one-sentence summary of this session]

   **Completed:**
   - [what was finished]

   **Blocked / Notes:**
   - [blockers or incomplete items; "None" if clear]

   **Files touched:**
   - [files created or modified; omit this section entirely if none]

   ---
   ```
   Fill in based on what actually happened in this conversation.

6. **ADR check.** If a significant architectural or technical decision was made (trade-off evaluated, choice made about system design or technology), create an ADR:
   - Find the highest existing ADR number in `memory-bank/decisions/`. If none, start at 001.
   - Create `memory-bank/decisions/ADR-NNN.md` using the ADR format.
   - Reference the ADR number in the session log entry under Blocked / Notes.

7. **Rewrite `memory-bank/progress.md`** with this structure:
   ```
   # Progress

   **Last Updated:** TIMESTAMP

   ## Current Focus
   [What the project is working on right now — 1-2 sentences]

   ## Active Tasks
   - [bullet list of tasks in progress or queued]

   ## Recent Completions
   - [last 3-5 completed items, from this and recent session logs]

   ## Key Context
   - [anything a new Claude session needs to not lose thread]
   ```

8. **Update architecture.md / tech-stack.md** only if the session involved changes to system architecture or technology choices/constraints. Otherwise leave untouched.

9. **Confirm** to the user that the checkpoint was saved. Remind them to commit `memory-bank/` to git when ready. Suggest commit message: `chore(memory-bank): checkpoint TIMESTAMP — [one-line focus summary]`
