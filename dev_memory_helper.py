import os
import json
from memory_io import load_memory, load_global_lessons

def get_developer_memory_context(project_path: str, request: str) -> str:
    """Loads, filters, and formats the memory context relevant to the user request."""
    if not request:
        return ""
        
    req_lower = request.lower()
    words = [w.strip() for w in req_lower.split() if len(w) > 2]
    if not words:
        words = ["code", "build"]

    # 1. Load workspace memory
    mem = load_memory(project_path)
    
    # 2. Load global lessons
    g_lessons = load_global_lessons()
    
    # 3. Filter workspace lessons
    ws_lessons = mem.get("lessons_learned", [])
    relevant_ws = [l for l in ws_lessons if any(w in l.lower() for w in words)]
    if not relevant_ws and ws_lessons:
        relevant_ws = ws_lessons[-3:]
    else:
        relevant_ws = relevant_ws[-5:]

    # 4. Filter global lessons
    relevant_g = [l for l in g_lessons if any(w in l.lower() for w in words)]
    if not relevant_g and g_lessons:
        relevant_g = g_lessons[-3:]
    else:
        relevant_g = relevant_g[-5:]

    # 5. Filter file blueprints
    it_dept = mem.get("it_department", {})
    blueprints = it_dept.get("file_blueprints", {})
    relevant_bp = {}
    if isinstance(blueprints, dict):
        for name, desc in blueprints.items():
            if any(w in name.lower() or w in str(desc).lower() for w in words):
                relevant_bp[name] = desc
        if not relevant_bp and blueprints:
            keys = list(blueprints.keys())[:3]
            relevant_bp = {k: blueprints[k] for k in keys}
        else:
            keys = list(relevant_bp.keys())[-5:]
            relevant_bp = {k: relevant_bp[k] for k in keys}

    # 6. Format prompt block
    parts = []
    if relevant_g:
        parts.append("### Global Lessons (Universal rules to avoid repeating past bugs):\n" + "\n".join(f"- {l}" for l in relevant_g))
        
    if relevant_ws:
        parts.append("### Project Lessons (Workspace-specific fixes/workarounds):\n" + "\n".join(f"- {l}" for l in relevant_ws))
        
    if relevant_bp:
        parts.append("### Existing File Blueprints (Context of files previously created/modified):\n" + json.dumps(relevant_bp, indent=2))

    if parts:
        return "\n\n".join([
            "=========================================",
            "RELEVANT MEMORY CONTEXT (Tier 2)",
            "=========================================",
            ""
        ] + parts + [
            "",
            "========================================="
        ])
    return ""
