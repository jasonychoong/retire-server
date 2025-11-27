# Completeness Tools – Manual Smoke Test

1. **Prepare a fresh session**
   ```bash
   cd server
   source ../.venv/bin/activate
   export RETIRE_SYSTEM_PROMPT=server/tools/.chat/system-prompts/completeness.txt
   ./tools/chat --new-session
   ```

2. **Capture two facts**
   - Provide a prompt such as: “We plan to retire at 60 and will keep our home in Austin.”
   - Observe in the CLI output that the agent calls the `information` tool twice (topics `income_cash_flow` and `housing_geography`).
   - Verify `server/tools/.chat/sessions/<session-id>/information.jsonl` now has two entries.

3. **Trigger `information_query`**
   - Ask: “What have you captured so far?”
   - Confirm the assistant calls `information_query` and references the stored facts.

4. **Persist completeness scores**
   - Say: “Based on this, I think income is mostly covered; housing is partially covered.”
   - Confirm the agent calls the `completeness` tool.
   - Check `completeness.jsonl` for a new snapshot with entries for the two topics.

5. **Validate tool logging**
   - Inspect `history.json` and `metadata.json` for the session to confirm tool usage entries exist for all three tools.

6. **Observe live monitors (optional but recommended)**
   - In a second terminal, run the completeness monitor to watch per-topic arrows update:
     ```bash
     cd server
     ./tools/completeness
     ```
     - You can pass `--session <id>` to monitor a specific session.
     - Enter a topic number (1–8) to print the recommended “explore this topic” prompt, then press Enter to resume monitoring.
   - In a third terminal, run the profile monitor to view captured facts grouped by topic/subtopic:
     ```bash
     cd server
     ./tools/profile
     ```
   - Keep both windows open while you chat; they should refresh every ~2 seconds.


