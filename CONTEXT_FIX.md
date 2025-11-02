# Multi-Turn Context Preservation - Fix Documentation

## Problem Identified

The agent was losing all previous conversation context on each new turn because the backend was **replacing** the entire message history instead of **appending** new messages.

### Root Cause

In `backend/server.py` line 370 (original):
```python
session.messages = list(result.get("messages", session.messages))
```

This line **replaced** `session.messages` with only the messages from the current run, which meant:
- ❌ Previous user prompts were lost
- ❌ Previous AI responses were lost
- ❌ Previous tool executions (code, plots, data) were lost
- ❌ Previous ToolMessages with images/outputs were lost
- ❌ Each run started with only: `[SystemMessage, HumanMessage(current_prompt)]`

### Impact

1. **Agent had no memory** - Couldn't reference previous analysis, plots, or code
2. **Log files incomplete** - Each `run_id.txt` only showed the latest exchange
3. **User experience broken** - Multi-turn conversations impossible
4. **Wasted context** - Python namespace persisted but agent couldn't see what was in it

## Solution Applied

### 1. Fixed Message Appending (Lines 370-381)

**Before:**
```python
session.messages = list(result.get("messages", session.messages))
```

**After:**
```python
# Append new messages instead of replacing entire history
run_messages = list(result.get("messages", []))
base_len = len(session.messages)

# Only append messages that are new (beyond what we already sent to the agent)
if base_len < len(run_messages):
    new_messages = run_messages[base_len:]
    session.messages.extend(new_messages)
elif base_len == 0:
    # First turn - use all returned messages
    session.messages = run_messages
# else: agent returned same or fewer messages, keep our session history
```

**What this does:**
- Keeps all existing messages in `session.messages`
- Only appends **new** messages returned by the agent (AI responses, ToolMessages)
- Preserves the full conversation thread across turns

### 2. Added Session-Wide Logging (Lines 386-422)

Created a comprehensive session log that includes **all** messages from **all** turns:

```python
# Save session-wide conversation log
if agent.run_id:
    session_log_path = Config.RUNS_DIR / f"{agent.run_id}_session.txt"
    # ... writes full session.messages to file ...
```

**Output format:**
```
ML Engineer Agent - Session Log
================================================================================
Session ID: abc123...
Run ID: 20250102_143045_dataset_name
Dataset: dataset_name
Model: gpt-4o
Timestamp: 2025-01-02T14:30:45
Total Messages: 15
================================================================================

[Message 1]
Type: SYSTEM
Content:
You are an expert ML Engineer...

[Message 2]
Type: USER
Content:
Analyze the data and create visualizations

[Message 3]
Type: ASSISTANT
Content:
<think>I'll start by loading and exploring...</think>
...

Tool Calls: 2
  - dataset_info
  - execute_python

[Message 4]
Type: ToolMessage
Content:
<plot images and data outputs>

... and so on for ALL turns ...
```

## What Now Works

### ✅ Full Context Preservation

**First Turn:**
```
User: "Analyze the data and plot distributions"
→ Agent sees: [SystemMessage, HumanMessage]
→ Agent generates plots, code, analysis
→ session.messages now has: [System, Human, AI, Tool, Tool, ...]
```

**Second Turn:**
```
User: "Now train a model using the features we just analyzed"
→ Agent sees: [System, Human1, AI1, Tool1, Tool1, Human2]
→ Agent can reference previous plots, code, features!
→ session.messages extends with: [AI2, Tool2, Tool2, ...]
```

**Third Turn:**
```
User: "Compare this model's performance to the baseline"
→ Agent sees: ENTIRE conversation history
→ Agent knows about all previous models, metrics, visualizations
→ Full context available!
```

### ✅ Complete Logs

Each run creates `{run_id}_session.txt` containing:
- System prompt
- ALL user questions (not just latest)
- ALL AI responses with think/plan/solution tags
- ALL tool calls and results
- Images encoded in ToolMessages
- Full conversation thread

### ✅ Agent Memory

The agent can now:
- Reference previous visualizations: "As shown in the earlier histogram..."
- Build on previous code: "Using the features we engineered in step 2..."
- Compare results: "This model performs better than the baseline we trained earlier"
- Answer questions about past analysis: "What did the correlation matrix show?"

### ✅ Namespace + Message Context Together

Before: Namespace persisted but agent didn't know what was in it
After: Agent sees both:
1. **Namespace state** - Variables, functions, data still loaded in Python
2. **Message history** - What code was run, what plots were made, what analysis was done

## Implementation Details

### Message Flow

```
Turn 1:
  session.messages = []
  ↓ add HumanMessage
  session.messages = [System, Human1]
  ↓ agent.run(messages=session.messages)
  ↓ returns [System, Human1, AI1, Tool1, Tool2]
  ↓ append new messages [AI1, Tool1, Tool2]
  session.messages = [System, Human1, AI1, Tool1, Tool2]

Turn 2:
  session.messages = [System, Human1, AI1, Tool1, Tool2]
  ↓ add HumanMessage
  session.messages = [System, Human1, AI1, Tool1, Tool2, Human2]
  ↓ agent.run(messages=session.messages)  ← Full context!
  ↓ returns [System, Human1, AI1, Tool1, Tool2, Human2, AI2, Tool3]
  ↓ append new messages [AI2, Tool3]
  session.messages = [System, Human1, AI1, Tool1, Tool2, Human2, AI2, Tool3]

Turn 3:
  session.messages = [...all previous..., Human3]
  ↓ agent.run(messages=session.messages)  ← Even more context!
  ...
```

### Key Code Locations

**Message handling:**
- `backend/server.py` lines 370-381 - Message appending logic
- `backend/server.py` line 348 - Agent receives `messages=list(session.messages)`

**Session state:**
- `backend/server.py` line 47 - `session.messages: List[BaseMessage]` storage
- `backend/server.py` line 346 - `session.messages.append(human_message)`

**Logging:**
- `backend/server.py` lines 386-422 - Session-wide log writer
- Output: `{RUNS_DIR}/{run_id}_session.txt`

**Agent execution:**
- `backend/ml_engineer/agent.py` line 514 - `run(messages=...)` accepts full history
- Python namespace persists when `reset_namespace=False` (line 333 logic)

## Testing the Fix

### Test Scenario 1: Sequential Analysis

```
Turn 1: "Load the data and show me the first few rows"
→ Agent loads data, shows df.head()
→ session.messages: [System, Human, AI, Tool]

Turn 2: "Create visualizations of the numeric columns"
→ Agent sees previous data loading
→ Can reference df directly from namespace
→ Creates plots
→ session.messages: [...previous..., Human, AI, Tool, Tool, Tool]

Turn 3: "What patterns did you notice in those plots?"
→ Agent sees ALL previous messages including plot ToolMessages
→ Can analyze the visualizations it just created
→ Provides insights based on full context
```

### Test Scenario 2: Iterative Modeling

```
Turn 1: "Train a baseline logistic regression model"
→ session.messages: [System, Human, AI, Tool, Tool]

Turn 2: "Now try a random forest with the same features"
→ Agent remembers: which features were used, what the baseline score was
→ Can compare: "Random Forest (0.89) outperforms Logistic Regression (0.82)"

Turn 3: "Tune the hyperparameters of the random forest"
→ Agent knows: current model, current score, feature set
→ Can optimize based on full context
```

### Verification

Check the session log file after multiple turns:
```bash
cat {RUNS_DIR}/20250102_143045_dataset_name_session.txt
```

Should show:
- ✅ All user prompts from all turns
- ✅ All AI responses from all turns
- ✅ All tool executions from all turns
- ✅ Properly ordered conversation thread

## Remaining Considerations

### Token Limits

Long conversations may hit LLM context limits. Consider:
- **Summarization** - Compress older turns
- **Retrieval** - Keep recent turns, retrieve older context as needed
- **Pruning** - Remove very old system messages if conversation grows large

### Performance

Each turn processes more messages. Monitor:
- **Latency** - Does response time increase significantly?
- **Memory** - Session state grows with each turn
- **Cost** - More tokens = higher API costs

### Session Reset

The reset endpoint (`POST /sessions/{id}/reset`) now:
- Clears `session.messages`
- Resets Python namespace
- Starts fresh conversation

Users can reset when they want a clean slate while keeping the same dataset.

## Summary

**Problem:** Agent forgot everything after each turn
**Cause:** Message history was replaced instead of appended
**Fix:** Changed line 370 to append new messages, added session-wide logging
**Result:** Agent now has full context of all previous analysis, code, and visualizations

The agent can now truly have multi-turn conversations and build on previous work!
