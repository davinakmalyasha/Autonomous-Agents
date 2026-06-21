"""
Centralized Chat Context Builder.
Provides a single utility to load and format chat history for agent prompts.
"""

def build_chat_context(
    workspace_path: str,
    chat_id: str,
    max_messages: int = 6,
    max_chars_per_msg: int = 300,
    exclude_traces: bool = True,
) -> str:
    """Single source of truth for chat history context injection with smart truncation."""
    if not workspace_path or not chat_id:
        return ""
    try:
        from workspace_manager import get_chat
        chat_data = get_chat(workspace_path, chat_id, include_traces=False, include_usage=False)
        if not chat_data:
            return ""
        
        messages = chat_data.get("messages", [])
        recent = messages[-max_messages:]
        
        lines = []
        for m in recent:
            role = m.get("role") or m.get("sender") or ""
            text = m.get("content") or m.get("text") or ""
            
            if exclude_traces and role == "agent" and m.get("metadata", {}).get("isTrace"):
                continue
            if not role or not text:
                continue
            
            # Smart truncation: keep first 200 + last 100 if over limit
            if len(text) > max_chars_per_msg:
                first_part = text[:200]
                last_part = text[-100:]
                text = f"{first_part}\n...[{len(text) - 300} chars truncated]...\n{last_part}"
            
            lines.append(f"[{role.upper()}]: {text}")
        
        return "\n".join(lines) if lines else ""
    except Exception as e:
        print(f"[CHAT CONTEXT] Error building context: {e}")
        return ""
