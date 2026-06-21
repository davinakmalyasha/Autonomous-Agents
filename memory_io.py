import os
import json
import copy
from memory_types import MemorySegmentUpdate

WORKSPACE_DIR = r"d:\MyProject\LangChain"

def load_memory(workspace_path: str = "") -> dict:
    """Loads the workspace memory file, initializing default RBAC segments if missing."""
    ws_dir = workspace_path or WORKSPACE_DIR
    
    default_structure = {
        "past_requests": [],
        "lessons_learned": [],
        "global": {
            "preferences": {}
        },
        "it_department": {
            "technologies": [],
            "db_configs": {},
            "file_blueprints": {}
        },
        "design_department": {
            "themes": {},
            "ui_flow_specs": {}
        },
        "security": {
            "encryption_specs": {},
            "permission_rules": {}
        }
    }
    
    # ── Durable Memory Store Integration ──
    from state_sync import active_store
    store = active_store.get()
    if store is not None:
        try:
            namespace = ("workspace_memory",)
            key = os.path.normpath(os.path.abspath(ws_dir)).lower()
            item = store.get(namespace, key)
            if item is not None and isinstance(item.value, dict):
                data = item.value
                for k in default_structure:
                    if k not in data:
                        data[k] = default_structure[k]
                return data
            return copy.deepcopy(default_structure)
        except Exception as e:
            import sys
            print(f"BaseStore load error: {e}", file=sys.stderr)
            # Fall through to disk fallback on error
            
    # We prefer the cleaner .deep_agents/workspace_memory.json path
    memory_path = os.path.join(ws_dir, ".deep_agents", "workspace_memory.json")
    
    # Fallback to legacy root path if it exists and workspace_path is default
    if not os.path.isfile(memory_path) and ws_dir == WORKSPACE_DIR:
        legacy_path = os.path.join(WORKSPACE_DIR, "workspace_memory.json")
        if os.path.isfile(legacy_path):
            memory_path = legacy_path
            
    if os.path.isfile(memory_path):
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Remove redundant keys to save tokens
            for key in ["client_name", "project_path"]:
                if key in data:
                    del data[key]
            if "global" in data and "client_name" in data["global"]:
                del data["global"]["client_name"]
            # Ensure all segments exist (RBAC initialization)
            for key in default_structure:
                if key not in data:
                    data[key] = default_structure[key]
            return data
        except Exception:
            pass
            
    return copy.deepcopy(default_structure)

def save_memory(data: dict, workspace_path: str = "") -> None:
    """Saves memory with automatic size caps to prevent bloat."""
    # Cap past_requests to 10
    if "past_requests" in data and isinstance(data["past_requests"], list):
        if len(data["past_requests"]) > 10:
            data["past_requests"] = data["past_requests"][-10:]
            
    # Cap lessons_learned to 10
    if "lessons_learned" in data and isinstance(data["lessons_learned"], list):
        if len(data["lessons_learned"]) > 10:
            data["lessons_learned"] = data["lessons_learned"][-10:]
            
    # Cap file_blueprints to 30 (keep newest)
    it = data.get("it_department", {})
    if isinstance(it, dict):
        blueprints = it.get("file_blueprints")
        if isinstance(blueprints, dict) and len(blueprints) > 30:
            keys = list(blueprints.keys())
            for k in keys[:-30]:
                del blueprints[k]
        
        # Cap technologies list to 20 unique entries
        techs = it.get("technologies")
        if isinstance(techs, list):
            unique_techs = list(dict.fromkeys(techs))
            if len(unique_techs) > 20:
                unique_techs = unique_techs[-20:]
            it["technologies"] = unique_techs

    # ── Durable Memory Store Integration ──
    from state_sync import active_store
    store = active_store.get()
    if store is not None:
        try:
            ws_dir = workspace_path or WORKSPACE_DIR
            namespace = ("workspace_memory",)
            key = os.path.normpath(os.path.abspath(ws_dir)).lower()
            store.put(namespace, key, data)
            return
        except Exception as e:
            import sys
            print(f"BaseStore save error: {e}", file=sys.stderr)
            # Fall through to disk fallback on error

    ws_dir = workspace_path or WORKSPACE_DIR
    deep_agents_dir = os.path.join(ws_dir, ".deep_agents")
    os.makedirs(deep_agents_dir, exist_ok=True)
    memory_path = os.path.join(deep_agents_dir, "workspace_memory.json")
    try:
        import tempfile
        tmp_fd, tmp_path = tempfile.mkstemp(dir=deep_agents_dir, suffix=".tmp", text=True)
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, memory_path)  # atomic on same filesystem
        except Exception:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            raise
    except Exception as e:
        print(f"Error saving memory: {e}")

def apply_segment_update(current_dict: dict, update: MemorySegmentUpdate) -> None:
    """Applies additions and deletions to a memory segment to prevent conflicts."""
    # 1. Apply deletions
    for key in update.deletions:
        if key in current_dict:
            del current_dict[key]
    # 2. Apply updates/additions
    for key, val in update.updates.items():
        if isinstance(val, dict) and key in current_dict and isinstance(current_dict[key], dict):
            current_dict[key].update(val)
        else:
            current_dict[key] = val

def load_global_lessons() -> list[str]:
    """Loads global lessons learned from user_profile.json."""
    profile_path = r"d:\MyProject\LangChain\.deep_agents\user_profile.json"
    if os.path.isfile(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("global_lessons", [])
        except Exception:
            pass
    return []

def save_global_lessons(lessons: list[str]) -> None:
    """Saves global lessons learned to user_profile.json."""
    profile_path = r"d:\MyProject\LangChain\.deep_agents\user_profile.json"
    data = {}
    if os.path.isfile(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    unique_lessons = list(dict.fromkeys(lessons))
    data["global_lessons"] = unique_lessons[-5:]
    try:
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving global lessons: {e}")
