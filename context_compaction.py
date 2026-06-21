"""
Context Compaction module.
Implements tiered compaction and structured resume summaries to manage token limits.

Covers:
  Pillar 65: Context-Aware Tool Result Compaction
  Pillar 105: Selective Message Hydration using Lazy Load Proxies
  Pillar 108: Multi-Turn Conversation Anchor Pivoting
  Pillar 111: Adaptive Context Compaction Triggers
"""
import os
import re
import uuid
from langchain_core.messages import HumanMessage, AIMessage

def extract_paths_from_text(text: str) -> list[str]:
    """Helper to extract file paths from various write/edit tool result formats,
    including uncompacted, compacted ([TOOL OK]), and resume summaries.
    """
    import os
    import re
    from tools import shared_state, WORKSPACE
    active_ws = os.path.abspath(shared_state.get("project_path") or WORKSPACE or ".")
    
    paths = []
    # 1. Look for uncompacted write/edit markers
    for m in re.finditer(r"(?:[Ww]rote|[Ee]dited|[Aa]pplied diff to)\s+(\S+)", text):
        paths.append(m.group(1))
    
    # 2. Look for explicit JSON-like or Key-value properties
    for m in re.finditer(r"(?:file_path|path|TargetFile|target_file)[:=]\s*([^\s,;\"'\(\)]+)", text):
        paths.append(m.group(1))

    # 3. Look for structured summary lists
    for line in text.split("\n"):
        if line.startswith("Files Modified:") or line.startswith("Files Created:"):
            parts = line.split(":", 1)[1].split(",")
            for p in parts:
                p_clean = p.strip()
                if p_clean:
                    paths.append(p_clean)
                    
    # Clean and resolve to absolute paths
    resolved_paths = []
    for p in paths:
        clean = p.strip("[](),;'\"")
        if clean:
            if not os.path.isabs(clean):
                abs_p = os.path.abspath(os.path.join(active_ws, clean))
            else:
                abs_p = os.path.abspath(clean)
            resolved_paths.append(os.path.normpath(abs_p).lower())
            
    return resolved_paths


def invalidate_stale_reads(messages: list) -> list:
    """
    Pillar 65: Walks conversation history backwards. Detects file writes/edits,
    and replaces older reads of those files with a stale content tag.
    """
    import os
    from tools import shared_state, WORKSPACE
    active_ws = os.path.abspath(shared_state.get("project_path") or WORKSPACE or ".")
    
    modified_files = set()
    result = list(messages)

    for idx in range(len(result) - 1, -1, -1):
        msg = result[idx]
        
        # 1. Detect modified files from AI Message
        if isinstance(msg, AIMessage):
            tool_calls = []
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({"tool": tc.get("name"), "args": tc.get("args")})
            if not tool_calls and msg.content:
                from developer_agent import parse_all_tool_calls
                try:
                    tool_calls = parse_all_tool_calls(msg.content)
                except Exception:
                    pass
            
            for tc in tool_calls:
                tool_name = tc.get("tool", "")
                if tool_name in (
                    "write_file", "write_planning_file", "edit_file", "apply_diff",
                    "batch_edit", "write_to_file", "replace_file_content",
                    "multi_replace_file_content"
                ):
                    args = tc.get("args") or {}
                    path = (
                        args.get("file_path") or args.get("path") or
                        args.get("TargetFile") or args.get("target_file")
                    )
                    if path:
                        if not os.path.isabs(path):
                            abs_p = os.path.abspath(os.path.join(active_ws, path))
                        else:
                            abs_p = os.path.abspath(path)
                        modified_files.add(os.path.normpath(abs_p).lower())
        
        # 2. Detect modified files from Human Message
        elif isinstance(msg, HumanMessage):
            content = msg.content if hasattr(msg, "content") else str(msg)
            content_lower = content.lower()
            
            # Check if this is a tool result of a write/edit
            is_write_edit_result = False
            tool_name = None
            name_match = re.search(r"Tool '([^']+)'|\[([a-zA-Z0-9_-]+)\]", content[:200])
            if name_match:
                tool_name = name_match.group(1) or name_match.group(2)
                
            write_tools = {"write_file", "write_planning_file", "edit_file", "apply_diff", "batch_edit", "write_to_file", "replace_file_content", "multi_replace_file_content"}
            if (tool_name in write_tools) or any(marker in content_lower for marker in ["[write_file]", "[edit_file]", "[apply_diff]", "[batch_edit]", "wrote file", "edited file", "[ok] wrote", "[ok] edited", "[tool ok] write_file", "[tool ok] edit_file", "[tool ok] apply_diff"]):
                is_write_edit_result = True
                
            if is_write_edit_result:
                paths = extract_paths_from_text(content)
                for p in paths:
                    modified_files.add(p)

            # If it's a read result (and not a write/edit result), check if it is stale
            if not is_write_edit_result and "[FILE]" in content:
                m = re.search(r"\[FILE\]\s+([^\s\n]+)", content)
                if m:
                    file_path_str = m.group(1).strip()
                    if not os.path.isabs(file_path_str):
                        abs_read_p = os.path.abspath(os.path.join(active_ws, file_path_str))
                    else:
                        abs_read_p = os.path.abspath(file_path_str)
                    norm_read_path = os.path.normpath(abs_read_p).lower()
                    
                    if norm_read_path in modified_files:
                        stale_content = f"[read_file]:\n[FILE] {file_path_str} (content stale - file was modified later)"
                        result[idx] = type(msg)(
                            content=stale_content, 
                            id=getattr(msg, "id", None),
                            additional_kwargs=getattr(msg, "additional_kwargs", {})
                        )
                            
    return result


# ── Pillar 105: Lazy Message Hydration Store ──
# Maps msg_id → full content for long tool outputs replaced with previews
_LAZY_STORE: dict[str, str] = {}
_LAZY_THRESHOLD = 15000  # chars — messages longer than this get lazified

def _lazy_id() -> str:
    return f"lazy-{uuid.uuid4().hex[:8]}"

def store_lazy_content(full_content: str) -> str:
    """Store full content and return a lazy reference ID."""
    lid = _lazy_id()
    _LAZY_STORE[lid] = full_content
    return lid

def hydrate_on_demand(messages: list, requested_ids: set[str] | None = None) -> list:
    """Expand lazy references in messages. If requested_ids is None, hydrate all."""
    result = []
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(content, str) and content.startswith("[LAZY:"):
            # Parse: [LAZY: <id> — <N chars> — <preview>]
            import re as _re
            m = _re.match(r"\[LAZY:\s*(\S+)\s*—", content)
            if m:
                lid = m.group(1)
                if requested_ids is None or lid in requested_ids:
                    full = _LAZY_STORE.get(lid, content)
                    result.append(type(msg)(content=full))
                    # Don't delete from store — may need to re-hydrate later
                    continue
        result.append(msg)
    return result

def clear_lazy_store() -> None:
    """Clear the lazy hydration store (call at end of graph execution)."""
    _LAZY_STORE.clear()

# ── Pillar 111: Adaptive Compaction Threshold ──

def get_compaction_threshold(thread_depth: int) -> float:
    """
    Return the context-window utilization percentage that triggers compaction.
    Lower = more aggressive compaction = higher DeepSeek prefix cache hit rate.

    Compacting earlier keeps more of the immutable SystemMessage + task prefix
    in the KV cache across turns. The cost is losing some middle-turn detail,
    but structured resume summaries preserve decisions, errors, and artifacts.

    Shallow runs (1-5 turns) → 75% (gentle, preserve detail)
    Medium runs (6-15 turns) → 65% (balanced)
    Deep loops (16+) → 55% (aggressive, maximize cache reuse)
    """
    if thread_depth <= 5:
        return 0.75
    elif thread_depth <= 15:
        return 0.65
    else:
        return 0.55

# ── Pillar 65: Tool Result Success Compaction ──

# Tool result markers — first line of a HumanMessage that is a tool result
_TOOL_RESULT_PATTERNS = (
    "[read_file]:", "[list_files]:", "[search_code]:", "[search_codebase]:",
    "[run_command]:", "[view_signatures]:", "[search_semantic_checkpoints]:",
    "TOOL RESULT:", "Tool '", "[write_file]", "[write_planning_file]",
    "[edit_file]", "[apply_diff]", "[batch_edit]", "[pipeline_tools]",
    "[safe_read_file]", "[exec_command]",
)

# Error/failure indicators — if any present, keep the output intact
_ERROR_SIGNALS = (
    "error", "failed", "traceback", "exception", "exit code: 1",
    "status: fail", "permission denied", "not found", "timeout",
    "command not found", "cannot", "denied", "stack trace",
    "syntaxerror", "indentationerror", "modulenotfounderror",
    "importerror", "attributeerror", "typeerror", "valueerror",
    "keyerror", "indexerror", "runtimeerror", "connectionerror",
)

def compact_successful_tools(messages: list) -> list:
    """
    Pillar 65: Replace successful tool outputs with compact '[TOOL OK]' markers.

    Rules:
      - Error/failure outputs stay intact (never compacted)
      - Last 3 tool results stay intact (needed for immediate next action)
      - Already-compacted messages ([TOOL OK]) are skipped
      - System messages (first 3) are never touched
      - Compaction reduces 200-800 token outputs → ~15-30 token markers

    This is the single highest-impact token saver — it prevents the per-turn
    context inflation visible in chat logs where Developer input grows from
    2.5K → 11.5K tokens across 15 turns.
    """
    import re as _re

    import os
    import re as _re

    # 1. Backwards scan to find which file paths are read in the history
    seen_reads = set()
    superseded_indices = set()
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, HumanMessage):
            content = msg.content if hasattr(msg, "content") else str(msg)
            # Detect if it's a file read output
            if "[FILE]" in content:
                m = _re.search(r"\[FILE\]\s+([^\s\n]+)", content)
                if m:
                    file_path = os.path.normpath(m.group(1).strip()).lower()
                    if file_path in seen_reads:
                        superseded_indices.add(idx)
                    else:
                        seen_reads.add(file_path)

    # Identify tool result messages in the list
    tool_result_indices = []
    for i, msg in enumerate(messages):
        if i < 2:  # Never touch SystemMessage (Zone 1) + Task HumanMessage (Zone 2)
            continue
        if not isinstance(msg, HumanMessage):
            continue
        content = msg.content if hasattr(msg, "content") else str(msg)
        # Skip already-compacted messages
        if content.startswith("[TOOL OK]"):
            continue
        # Detect tool result patterns (check first 80 chars — tool prefix is always at start)
        prefix = content[:80]
        if any(marker in prefix for marker in _TOOL_RESULT_PATTERNS):
            tool_result_indices.append(i)

    if not tool_result_indices:
        return messages

    # Keep last 6 tool results un-compacted (LLM needs recent context)
    protected = set(tool_result_indices[-6:]) if len(tool_result_indices) >= 6 else set(tool_result_indices)

    result = []
    for i, msg in enumerate(messages):
        if i not in tool_result_indices or i in protected:
            result.append(msg)
            continue

        content = msg.content if hasattr(msg, "content") else str(msg)
        content_lower = content.lower()

        # Error check — keep failures intact so the LLM can learn from them
        if any(e in content_lower for e in _ERROR_SIGNALS):
            result.append(msg)
            continue

        # Extract tool name from the result prefix
        tool_name = "tool"
        name_match = _re.search(r"Tool '([^']+)'|\[([a-zA-Z0-9_-]+)\]", content[:200])
        if name_match:
            tool_name = name_match.group(1) or name_match.group(2)

        # SAFETY CHECK 1: Never compact a file read unless it is superseded by a later read
        if tool_name in ("read_file", "safe_read_file") and i not in superseded_indices:
            result.append(msg)
            continue

        # SAFETY CHECK 2: Only compact run_command if it is a noisy test run or very large
        if tool_name in ("run_command", "exec_command"):
            is_noisy_test = "pytest" in content_lower
            is_very_large = len(content) > 5000
            if not is_noisy_test and not is_very_large:
                result.append(msg)
                continue

        # SAFETY CHECK 3: Never compact list_files, search_code, search_codebase, or view_signatures
        # as they provide essential directory maps, code search results, and API signatures.
        if tool_name in ("list_files", "search_code", "search_codebase", "view_signatures"):
            result.append(msg)
            continue

        # Generate one-line summary preserving key info
        summary = _extract_summary_line(content, tool_name)

        # ── Pillar 105: Store large content for potential lazy hydration ──
        if len(content) > _LAZY_THRESHOLD:
            lid = store_lazy_content(content)
            compacted = f"[TOOL OK] {tool_name} — {summary}\n[LAZY: {lid} — {len(content)} chars — {content[:200]}...]"
        else:
            compacted = f"[TOOL OK] {tool_name} — {summary}"

        result.append(HumanMessage(content=compacted))

    return result

def _extract_summary_line(content: str, tool_name: str) -> str:
    """Extract a meaningful one-line summary from tool output, preserving actionable info."""
    import re as _re
    if tool_name in ("read_file", "safe_read_file"):
        m = _re.search(r"\[FILE\]\s+(\S+)", content)
        if m:
            lines = content.count("\n")
            return f"read {m.group(1)} ({lines} lines)"
        return "read file"
    elif tool_name in ("write_file", "write_planning_file"):
        m = _re.search(r"(?:file_path|path)[:=]\s*(\S+)", content)
        return f"wrote {m.group(1)}" if m else "wrote file"
    elif tool_name in ("edit_file", "apply_diff", "batch_edit"):
        m = _re.search(r"(?:file_path|path)[:=]\s*(\S+)", content)
        return f"edited {m.group(1)}" if m else "edited file"
    elif tool_name in ("run_command", "exec_command"):
        # Extract the command from the first line
        first_line = content.strip().split("\n")[0]
        # If first line contains the command itself (format: "[run_command]:\n<output>")
        cmd_line = content.strip().split("\n")
        for line in cmd_line[:3]:
            if line.strip() and not line.startswith("["):
                return f"ran: {line.strip()[:80]}"
        return first_line[:80]
    elif tool_name in ("list_files",):
        count = content.count("\n")
        return f"listed ~{count} entries"
    elif tool_name in ("search_code", "search_codebase"):
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("[")]
        count = len(lines)
        return f"found {count} matches"
    elif tool_name in ("view_signatures",):
        count = content.count("def ") + content.count("class ")
        return f"found ~{count} signatures"
    elif tool_name in ("search_semantic_checkpoints",):
        count = content.count("🟢") + content.count("🟡") + content.count("🟠")
        return f"found {count} checkpoint matches" if count else "no checkpoint matches"
    elif tool_name in ("pipeline_tools",):
        # Count how many steps executed
        count = content.count("[TOOL OK]") + content.count("completed")
        return f"pipeline: {count} steps" if count else "pipeline executed"
    else:
        # Generic: first meaningful line, capped at 100 chars
        for line in content.strip().split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("[") and len(stripped) > 5:
                return stripped[:100]
        return content.strip()[:100]

# ── Pillar 108: Anchor Pivoting ──

def pivot_anchor_to_stable_checkpoint(messages: list, plan_checkpoint_idx: int) -> list:
    """
    Drop intermediate messages between start and the stable plan checkpoint,
    keeping only system + dynamic context + plan checkpoint + a compact summary.
    Called when transitioning from planning → execution phases.
    """
    if plan_checkpoint_idx <= 3 or plan_checkpoint_idx >= len(messages):
        return messages

    # Build compact summary of what was dropped
    dropped = messages[3:plan_checkpoint_idx]
    dropped_summary_parts = []
    for m in dropped:
        c = m.content if hasattr(m, "content") else str(m)
        dropped_summary_parts.append(c[:200])

    summary_text = (
        f"[ANCHOR PIVOT] Planning phase completed. "
        f"{len(dropped)} intermediate messages compacted.\n"
        f"Summary of planning activity:\n" +
        "\n".join(f"- {s}" for s in dropped_summary_parts[:5]) +
        (f"\n... and {len(dropped_summary_parts) - 5} more" if len(dropped_summary_parts) > 5 else "")
    )

    # Keep: system (0), dynamic context (1), task (2), summary, plan checkpoint, rest after checkpoint
    return [messages[0], messages[1], messages[2],
            HumanMessage(content=summary_text),
            messages[plan_checkpoint_idx]] + messages[plan_checkpoint_idx + 1:]

def strip_thinking(content: str) -> str:
    return re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL).strip()

def get_header_indices(messages: list) -> set[int]:
    """Helper to detect SystemMessage, Task HumanMessage, and Resume/Checkpoint summaries."""
    header_indices = set()
    if len(messages) > 0:
        header_indices.add(0)  # SystemMessage
    if len(messages) > 1:
        header_indices.add(1)  # Task HumanMessage
    if len(messages) > 2:
        content = messages[2].content if hasattr(messages[2], "content") else str(messages[2])
        if any(marker in content for marker in ["[SYSTEM RESUME INFO]", "[SYSTEM INFO] History compacted", "[ANCHOR PIVOT]"]):
            header_indices.add(2)
    return header_indices

def tier1_compact(messages: list, keep_last_n: int = 6) -> list:
    """
    Tier 1 (Light Compaction):
      - Strips thinking blocks.
      - Deduplicates superseded file reads.
      - Compresses successful action tools (write_file, edit_file, apply_diff, run_command [if noisy/large]) to [TOOL OK] markers.
      - Truncates very long tool outputs (>5000 chars) in older messages.
      - Protects headers and last N messages.
    """
    import os

    header_indices = get_header_indices(messages)
    mid_idx = len(messages) - keep_last_n

    # 1. Backwards scan to find which file paths are read in the history
    seen_reads = set()
    superseded_indices = set()
    for idx in range(len(messages) - 1, -1, -1):
        if idx in header_indices or idx >= mid_idx:
            continue
        msg = messages[idx]
        if isinstance(msg, HumanMessage):
            content = msg.content if hasattr(msg, "content") else str(msg)
            if "[FILE]" in content:
                m = re.search(r"\[FILE\]\s+([^\s\n]+)", content)
                if m:
                    file_path = os.path.normpath(m.group(1).strip()).lower()
                    if file_path in seen_reads:
                        superseded_indices.add(idx)
                    else:
                        seen_reads.add(file_path)

    compacted = []
    for i, msg in enumerate(messages):
        if i in header_indices or i >= mid_idx:
            compacted.append(msg)
            continue

        content = msg.content if hasattr(msg, "content") else str(msg)

        if isinstance(msg, AIMessage):
            content = strip_thinking(content)
            # Retain only tool blocks if they exist to keep AI messages compact
            tool_blocks = re.findall(r"```tool\s*\n.*?\n```", content, flags=re.DOTALL)
            if tool_blocks:
                content = "\n\n".join(tool_blocks)
            compacted.append(AIMessage(
                content=content, 
                id=getattr(msg, "id", None),
                tool_calls=getattr(msg, "tool_calls", []),
                additional_kwargs=getattr(msg, "additional_kwargs", {})
            ))
            continue

        if isinstance(msg, HumanMessage):
            # Check if this is a superseded read
            if i in superseded_indices:
                read_match = re.search(r"\[FILE\]\s+([^\s\n]+)", content)
                file_name = read_match.group(1) if read_match else "file"
                compacted.append(HumanMessage(
                    content=f"[read_file]:\n[FILE] {file_name} (content superseded by a later read)", 
                    id=getattr(msg, "id", None),
                    additional_kwargs=getattr(msg, "additional_kwargs", {})
                ))
                continue

            content_lower = content.lower()
            # If it's an error, keep it intact
            if any(e in content_lower for e in _ERROR_SIGNALS):
                compacted.append(msg)
                continue

            # Extract tool name from content
            tool_name = "tool"
            name_match = re.search(r"Tool '([^']+)'|\[([a-zA-Z0-9_-]+)\]", content[:200])
            if name_match:
                tool_name = name_match.group(1) or name_match.group(2)

            # Safety: informational tools are kept fully intact
            if tool_name in ("list_files", "search_code", "search_codebase", "view_signatures"):
                compacted.append(msg)
                continue

            # Action tools compression removed in Tier 1 (moved to Tier 2)

            # If it's another type of tool result and exceeds 5000 characters, truncate it
            if len(content) > 5000:
                prefix = "TOOL RESULT:\n" if content.startswith("TOOL RESULT:\n") else ""
                cleaned = content[len(prefix):].strip()
                if len(cleaned) > 5000:
                    content = f"{prefix}[TOOL RESULT TRUNCATED: {cleaned[:1000]} ... [truncated {len(cleaned)-2000} chars] ... {cleaned[-1000:]}]"

            compacted.append(HumanMessage(
                content=content, 
                id=getattr(msg, "id", None),
                additional_kwargs=getattr(msg, "additional_kwargs", {})
            ))
            continue

        compacted.append(msg)

    return compacted

def tier2_compact(messages: list, keep_last_n: int = 6) -> list:
    """
    Tier 2 (Medium Compaction):
      - Runs Tier 1 compaction first.
      - Collapses successful edits, writes, and test runs to [TOOL OK].
      - Replaces all older file read contents with a brief metadata label.
    """
    # 1. Run Tier 1 compaction first
    messages = tier1_compact(messages, keep_last_n)

    header_indices = get_header_indices(messages)
    mid_idx = len(messages) - keep_last_n

    compacted = []
    for i, msg in enumerate(messages):
        if i in header_indices or i >= mid_idx:
            compacted.append(msg)
            continue

        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(msg, HumanMessage):
            content_lower = content.lower()
            
            # Extract tool name from content
            tool_name = "tool"
            name_match = re.search(r"Tool '([^']+)'|\[([a-zA-Z0-9_-]+)\]", content[:200])
            if name_match:
                tool_name = name_match.group(1) or name_match.group(2)

            action_tools = {"apply_diff", "edit_file", "write_file", "run_command", "exec_command", "write_planning_file"}
            if tool_name in action_tools and not any(e in content_lower for e in _ERROR_SIGNALS):
                if tool_name in ("run_command", "exec_command"):
                    is_noisy_test = "pytest" in content_lower
                    is_very_large = len(content) > 5000
                    if is_noisy_test or is_very_large:
                        summary = _extract_summary_line(content, tool_name)
                        compacted.append(HumanMessage(
                            content=f"[TOOL OK] {tool_name} — {summary}", 
                            id=getattr(msg, "id", None),
                            additional_kwargs=getattr(msg, "additional_kwargs", {})
                        ))
                        continue
                else:
                    summary = _extract_summary_line(content, tool_name)
                    compacted.append(HumanMessage(
                        content=f"[TOOL OK] {tool_name} — {summary}", 
                        id=getattr(msg, "id", None),
                        additional_kwargs=getattr(msg, "additional_kwargs", {})
                    ))
                    continue

            # Check for file read metadata replacement
            if "[FILE]" in content or "read_file" in content:
                # Check if this is already a superseded placeholder
                if "content superseded by a later read" in content or "content stale - file was modified later" in content:
                    compacted.append(msg)
                    continue

                file_match = re.search(r"\[FILE\]\s+(\S+)", content)
                if file_match:
                    lines = content.count("\n")
                    content = f"TOOL RESULT:\n[Previously read: {file_match.group(1)}, ~{lines} lines]"
                    compacted.append(HumanMessage(
                        content=content, 
                        id=getattr(msg, "id", None),
                        additional_kwargs=getattr(msg, "additional_kwargs", {})
                    ))
                    continue

        compacted.append(msg)
    return compacted


def build_structured_resume_summary(tool_call_log: list, created: list, modified: list) -> str:
    """Build structured summary preserving decisions, errors, and outcomes."""
    sections = []
    if created:
        sections.append(f"Files Created: {', '.join(created)}")
    if modified:
        sections.append(f"Files Modified: {', '.join(modified)}")
    
    errors = []
    for i, call in enumerate(tool_call_log):
        if not isinstance(call, dict):
            continue
        res = call.get("result_preview", "")
        if any(kw in res.lower() for kw in ["error", "fail", "traceback", "exception"]):
            fix_note = ""
            if i + 1 < len(tool_call_log):
                nxt = tool_call_log[i+1]
                if isinstance(nxt, dict) and nxt.get("tool") in ("edit_file", "apply_diff", "write_file"):
                    nxt_args = nxt.get("args", {}) if isinstance(nxt.get("args"), dict) else {}
                    fix_note = f" -> Fixed via {nxt['tool']}({nxt_args.get('file_path', '')})"
            errors.append(f"- {call.get('tool', '?')}: {res[:500]}{fix_note}")
    if errors:
        sections.append("Errors Encountered:\n" + "\n".join(errors[-5:]))

    writes = [c for c in tool_call_log if isinstance(c, dict) and c.get("tool") in ("write_file", "edit_file", "apply_diff")]
    if writes:
        write_summary = [f"- {w.get('tool', '?')}({(w.get('args', {}) or {}).get('file_path', '?')})" for w in writes[-12:]]
        sections.append("Key Changes Made:\n" + "\n".join(write_summary))

    cmds = [c for c in tool_call_log if isinstance(c, dict) and c.get("tool") == "run_command"]
    if cmds:
        cmd_summary = [f"- `{(c.get('args', {}) or {}).get('command', '?')}` -> {c.get('result_preview', '')[:250]}" for c in cmds[-6:]]
        sections.append("Commands Executed:\n" + "\n".join(cmd_summary))
        
    return "\n\n".join(sections)


def checkpoint_compact(messages: list, tool_call_log: list, created: list, modified: list, keep_last_n: int = 6) -> list:
    """Summarizes history into a single structured checkpoint block to preserve the prefix cache.
    Replaces messages from index 2 (after Zone 1 SystemMessage + Zone 2 Task) up to
    len(messages) - keep_last_n with a single summary message.
    Archives cleared logs to /conversation_history/.
    """
    # Zone 1 + Zone 2 = 2 header messages (SystemMessage + Task HumanMessage)
    HEADER_COUNT = 2
    if len(messages) <= keep_last_n + HEADER_COUNT:
        return messages

    # 1. Archive the cleared logs
    import time
    import uuid
    from tools import write_file
    history_id = f"{int(time.time())}_{uuid.uuid4().hex[:4]}"
    vfs_path = f"/conversation_history/history_{history_id}.txt"

    log_parts = []
    for idx in range(HEADER_COUNT, len(messages) - keep_last_n):
        msg = messages[idx]
        mtype = getattr(msg, "type", msg.__class__.__name__)
        log_parts.append(f"=== Message [{mtype}] ===\n{msg.content}")

    full_log = "\n\n".join(log_parts)
    try:
        write_file(vfs_path, full_log)
        archive_info = f"\n\n(Original detailed intermediate logs archived to VFS path: {vfs_path})"
    except Exception as e:
        print(f"Error archiving history logs: {e}")
        archive_info = ""

    summary_content = build_structured_resume_summary(tool_call_log, created, modified)
    summary_header = f"[SYSTEM INFO] History compacted. Summary of progress so far:\n\n"

    from langchain_core.messages import HumanMessage
    summary_msg = HumanMessage(content=summary_header + summary_content + archive_info + "\n\n(Original intermediate history messages cleared to save tokens and optimize cache)")

    compacted = [messages[0], messages[1], summary_msg] + messages[-keep_last_n:]
    return compacted


