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


