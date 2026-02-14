# /iterate — Load Context and Resume

This command is READ-ONLY. It does not create, modify, or commit any files.

Execute these steps in order:

1. **Read all state files:**
   - `memory-bank/progress.md`
   - `memory-bank/architecture.md`
   - `memory-bank/tech-stack.md`

2. **Read recent decisions.** List files in `memory-bank/decisions/`. Read the most recent 2-3 ADRs (highest numbers). If none exist, skip.

3. **Get today's date:**
   ```
   powershell -Command "Get-Date -Format 'yyyy-MM-dd'"
   ```

4. **Read today's session log** if `memory-bank/session-logs/DATE.md` exists. If not, that is normal — no checkpoint has been run today yet.

5. **Handle edge cases:**
   - If `memory-bank/` does not exist at all: inform the user that no memory-bank has been initialized. Suggest running `/checkpoint` after doing some work.
   - If `progress.md` is still at its initial template state: say so and note the first `/checkpoint` has not been run yet.

6. **Synthesize and present a briefing.** Do NOT dump raw file contents. Synthesize into:
   - **Project:** What this is.
   - **Current Focus:** From progress.md.
   - **Last Activity:** Summary of the most recent session log entry. If a `[COMPACT]` entry exists, highlight it prominently — that is the resume point.
   - **Active Tasks / Next Steps:** From progress.md.
   - **Recent Decisions:** Brief summary of any ADRs.

7. Close with: "Memory loaded. Ready to continue — what would you like to work on?"
