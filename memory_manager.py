import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from memory_types import SupervisorMemoryUpdate
from memory_io import load_memory, save_memory, apply_segment_update, load_global_lessons, save_global_lessons

def is_valid_build_request(req: str) -> bool:
    """Checks if a string looks like a real build request, rather than guidance, greetings, or chat."""
    t = req.lower().strip().rstrip(".!?")
    if not t:
        return False
    # Filter out greetings
    greetings = {"hello", "hi", "hey", "what's up", "how are you", "operational and ready"}
    if t in greetings or any(t.startswith(g) for g in ["hello", "hi ", "hey ", "hi, ", "hello, "]):
        return False
        
    # Filter out simple continue/resume commands using similar logic
    continue_words = {
        "continue", "resume", "proceed", "go on", "go", "yes", "confirm", "approve",
        "do it", "run it", "looks good", "yessss continueee", "go on continue",
        "continue please", "please continue", "yesss continueee", "continueee"
    }
    if t in continue_words:
        return False
    words = t.split()
    if len(words) <= 5 and any(w in words for w in ["continue", "resume", "proceed", "go"]):
        return False
    if any(phrase in t for phrase in ["continue from where", "resume from where", "continue where we left", "go on continue", "continue last"]):
        return False

    # Filter out pure guidance responses (like numbering answers or simple yes/no/confirmations)
    if t in ("yes", "no", "y", "n", "ok", "okay", "sure", "sounds good", "go ahead", "do it"):
        return False
    # If it is numbering-only or list-only guidance without any active verbs
    import re
    if re.match(r"^\s*\d+[\.\)]", t):
        action_keywords = {"build", "create", "make", "write", "code", "fix", "implement", "add", "change", "modify", "delete", "remove", "refactor", "install", "deploy", "run", "test", "debug"}
        if not any(kw in t for kw in action_keywords):
            return False
    return True

def clean_and_minify_memory(mem: dict) -> dict:
    """Returns a copy of memory with environment_profile removed and empty keys pruned recursively."""
    def clean(val):
        if isinstance(val, dict):
            cleaned = {k: clean(v) for k, v in val.items()}
            return {k: v for k, v in cleaned.items() if v not in (None, {}, [], "")}
        elif isinstance(val, list):
            cleaned = [clean(x) for x in val]
            return [x for x in cleaned if x not in (None, {}, [], "")]
        return val

    mem_copy = mem.copy()
    if "environment_profile" in mem_copy:
        del mem_copy["environment_profile"]
    
    if "past_requests" in mem_copy:
        mem_copy["past_requests"] = mem_copy["past_requests"][-5:]

    return clean(mem_copy)


def refine_memory_milestone(client_request: str, requirements: str, tech_spec: str, log_text: str, project_path: str = "") -> None:
    """Runs the Archivist Sub-Agent to extract facts from the run and update memory segments."""
    mem = load_memory(project_path)

    # Skip MemoryArchivist LLM call entirely for non-build / trivial requests to save resources
    if not is_valid_build_request(client_request):
        print(">> Memory: Done. (Skipped)")
        return

    api_key = os.getenv("GEMINI_API_KEY")
    compacted_logs = compact_logs(log_text)

    sys_msg = (
        "You are the Memory Archivist Agent for a Virtual IT Office.\n"
        "Your task is to analyze the execution outputs (User request, requirements, specs, logs) "
        "and extract key facts, preferences, blueprints, and QA bug fixes.\n\n"
        "Organize updates into four Role-Based Access Control (RBAC) divisions:\n"
        "1. global: General client profile, preferences, and name.\n"
        "2. it_department: Software architecture, database schemas, codebase structures, and file locations.\n"
        "3. design_department: Business rules, color themes, UI elements, specification metrics, and requirements version history.\n"
        "4. security: Security standards, password formats, file permissions, and keys.\n\n"
        "Additionally, extract new lessons learned. You MUST split lessons into two distinct categories:\n"
        "- lessons_learned_updates: Workspace-level (local) lessons. These are project-specific, detailed code configurations, file pathways, database structures, or small workarounds that apply to this project specifically.\n"
        "- global_lessons_learned_updates: Global-level lessons. These are universal runtime errors, OS-specific terminal issues (e.g. Windows paths, commands), language/tool bugs (like pytest module resolution), or architectural patterns that affect the global way of coding across all projects. Keep these rare and extremely high-impact.\n\n"
        "All lessons must be compressed to a single, short, and dense line. Avoid conversational filler or long descriptions.\n\n"
        "Guidelines:\n"
        "- Do not create duplicate information. If information has changed (e.g. database type or folder path), "
        "add the old key to 'deletions' and the new one to 'updates' to avoid conflicts.\n"
        "- Integrate updates into pre-existing nested structures where possible (e.g., place frameworks/libraries under `technologies`, file structures under `file_blueprints`, styling details under `themes`, and layouts/components under `ui_flow_specs`), instead of cluttering each segment with flat root keys.\n"
        "- Summarize the raw data into short, dense facts."
    )

    from workspace_manager import get_client_name
    client_name = get_client_name()
    active_path = project_path or r"d:\MyProject\LangChain"

    user_msg = (
        f"Client Name: {client_name}\n"
        f"Active Project Path: {active_path}\n"
        f"Current Memory Database:\n{json.dumps(clean_and_minify_memory(mem), separators=(',', ':'))}\n\n"
        f"Client Request: \"{client_request}\"\n\n"
        f"Generated Requirements:\n{requirements[:3000]}\n\n"
        f"Generated Specs:\n{tech_spec[:3000]}\n\n"
        f"Execution Logs:\n{compacted_logs}\n\n"
        "Inspect the above and output the structured Memory Updates."
    )

    from llm import invoke_with_fallback
    try:
        decision = invoke_with_fallback(
            role="MemoryArchivist",
            sys_inst=sys_msg,
            prompt=user_msg,
            schema=SupervisorMemoryUpdate,
            temp=0.2
        )
    except Exception as e:
        print(f"Memory Archivist LLM execution failed: {e}")
        decision = None

    if decision is None:
        print("Memory Archivist: All LLM models exhausted. Memory refinement skipped.")
        # Programmatic fallback: ensure the request is added to past_requests anyway!
        clean_req = client_request.strip()
        if clean_req and is_valid_build_request(clean_req):
            past_reqs = mem.setdefault("past_requests", [])
            if not past_reqs or past_reqs[-1] != clean_req:
                past_reqs.append(clean_req)
            save_memory(mem, project_path)
        return

    apply_segment_update(mem["global"], decision.global_segment)
    apply_segment_update(mem["it_department"], decision.it_segment)
    apply_segment_update(mem["design_department"], decision.design_segment)
    apply_segment_update(mem["security"], decision.security_segment)

    # 1. Save Workspace lessons
    if hasattr(decision, "lessons_learned_updates") and decision.lessons_learned_updates:
        for lesson in decision.lessons_learned_updates:
            lesson = lesson.strip()
            if lesson and lesson not in mem.setdefault("lessons_learned", []):
                mem["lessons_learned"].append(lesson)
        if len(mem["lessons_learned"]) > 10:
            mem["lessons_learned"] = mem["lessons_learned"][-10:]

    # 2. Save Global lessons (written to user_profile.json)
    if hasattr(decision, "global_lessons_learned_updates") and decision.global_lessons_learned_updates:
        g_lessons = load_global_lessons()
        updated_g = False
        for lesson in decision.global_lessons_learned_updates:
            lesson = lesson.strip()
            if lesson and lesson not in g_lessons:
                g_lessons.append(lesson)
                updated_g = True
        if updated_g:
            save_global_lessons(g_lessons)

    if decision.new_request_to_add:
        req = decision.new_request_to_add
        if is_valid_build_request(req):
            if req not in mem["past_requests"]:
                mem["past_requests"].append(req)
    else:
        # Fallback to the client_request if the archivist skipped it
        clean_req = client_request.strip()
        if clean_req and is_valid_build_request(clean_req):
            past_reqs = mem.setdefault("past_requests", [])
            if not past_reqs or past_reqs[-1] != clean_req:
                past_reqs.append(clean_req)

    print(">> Memory: Done.")
    save_memory(mem, project_path)

def compact_logs(log_text: str) -> str:
    """Deterministic Python-based log compacter. Extracts key events and errors, eliminating LLM log compact calls."""
    if not log_text:
        return "(empty logs)"
        
    lines = log_text.splitlines()
    cleaned = []
    
    # Track context around errors/tracebacks
    keep_next_n = 0
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        # Detect errors, tracebacks, exceptions
        is_error_related = any(kw in line_str.lower() for kw in [
            "traceback", "exception", "error", "fail", "stderr", "invalid syntax", "syntaxerror", "jsondecodeerror"
        ])
        
        # Detect tool call notifications
        is_tool_call = any(kw in line_str for kw in [
            "[DEVELOPER] 🔧 Calling", "Calling run_command", "[OK]", "[WARNING]", "Tool '"
        ])
        
        # Detect test statistics/outcomes
        is_test_summary = any(kw in line_str.lower() for kw in [
            "failed,", "passed,", "skipped in", "seconds ==="
        ])
        
        if is_error_related or is_tool_call or is_test_summary:
            cleaned.append(line)
            # If it's a traceback start, keep the next 5 lines of context
            if "traceback" in line_str.lower():
                keep_next_n = 5
        elif keep_next_n > 0:
            cleaned.append(line)
            keep_next_n -= 1
            
    # Join and limit size to prevent prompt bloating
    output = "\n".join(cleaned)
    if len(output) > 8000:
        output = output[:4000] + "\n\n... [TRUNCATED LOG MIDDLE TO SAVE TOKENS] ...\n\n" + output[-4000:]
        
    return output
