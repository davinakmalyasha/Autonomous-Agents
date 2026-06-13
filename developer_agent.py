"""
Developer Agent v3 — Tool-using agentic loop (Claude Code / Codex pattern).
The Developer receives a task, uses file/code tools iteratively, and returns results.

v3.1 — Fixed: Uses proper LangChain multi-turn messages instead of flat strings.
"""
import os
import json
import re
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, RemoveMessage
from state_sync import shared_state
from it_department_nodes_base import ITState
from tools import TOOL_DEFINITIONS, execute_tool, list_files
from llm import invoke_messages_with_fallback
from deepagents import HarnessProfile, register_harness_profile

def get_harness_profile(name: str):
    try:
        import deepagents.profiles.harness.harness_profiles as hp
        return hp._HARNESS_PROFILES.get(name)
    except Exception:
        return None


def dynamic_prompt(func):
    """Decorator to mark a function as generating dynamic prompt suffixes."""
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

MAX_ITERATIONS = 50  # safety ceiling; agent should finish in 5-15 turns naturally


def _detect_test_command(project_path: str) -> str:
    """Detect the appropriate test command for the project type."""
    if not project_path or not os.path.isdir(project_path):
        return ""
    
    # Python: pytest
    py_test_files = [f for f in os.listdir(project_path) 
                     if f.startswith("test_") and f.endswith(".py")]
    if py_test_files:
        return f"cd /d {project_path} && python -m pytest -x -q"
    
    # Node.js: npm test
    pkg_json = os.path.join(project_path, "package.json")
    if os.path.isfile(pkg_json):
        try:
            import json
            with open(pkg_json, "r") as f:
                pkg = json.load(f)
            if pkg.get("scripts", {}).get("test"):
                return f"cd /d {project_path} && npm test"
        except Exception:
            pass
    
    # Go: go test
    go_test_files = [f for f in os.listdir(project_path) 
                     if f.endswith("_test.go")]
    if go_test_files:
        return f"cd /d {project_path} && go test ./..."
    
    # PHP/Laravel: php artisan test
    if os.path.isfile(os.path.join(project_path, "artisan")):
        return f"cd /d {project_path} && php artisan test"
    
    return ""


def _build_compact_tool_defs(valid_tools_list: list[str] = None) -> str:
    """Build compact one-line tool definitions to save token space."""
    COMPACT_DEFS = {
        "read_file": "read_file(file_path, offset?, limit?)",
        "write_file": "write_file(file_path, content)",
        "edit_file": "edit_file(file_path, old_string?, new_string?, diff?)",
        "run_command": "run_command(command, timeout?, background?)",
        "search_codebase": "search_codebase(query, top_k?)",
        "search_code": "search_code(pattern, path?, glob?)",
        "list_files": "list_files(path?, pattern?, recursive?)",
        "view_signatures": "view_signatures(file_path)",
        "write_planning_file": "write_planning_file(file_path, goal, analysis, proposed_changes, steps)",
        "search_past_conversations": "search_past_conversations(query)",
        "compact_conversation": "compact_conversation()",
        "read_conversation_history": "read_conversation_history(file_path)",
        "task": "task(name, task)",
        "start_async_task": "start_async_task(name, task)",
        "check_async_task": "check_async_task(task_id)",
        "list_async_tasks": "list_async_tasks()",
    }
    if valid_tools_list is not None:
        return "\n".join(f"- {COMPACT_DEFS[t]}" for t in valid_tools_list if t in COMPACT_DEFS)
    return "\n".join(f"- {k}: {v}" for k, v in COMPACT_DEFS.items())


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC system prompt — MUST be byte-identical across all calls to maximize
# DeepSeek KV cache hits (98% input cost discount on cache hit).
# ═══════════════════════════════════════════════════════════════════════════════
_STATIC_SYSTEM_TEMPLATE = r"""You are an expert software engineer and general-purpose AI assistant with full tool access. You handle any task — greenfield projects, bug fixes, refactors, exploration, architecture, devops, testing. Your default approach is to understand the workspace, then act immediately with tools. Complete tasks in the minimum number of turns. Every extra turn costs money.

## CORE RULE

Every single response you give MUST contain at least one tool call until the task is fully complete. Never output a response that is only text. Never describe what you would do — do it. Never output a plan without executing the first step of that plan in the same response. The only exception: when all work is verified done, output a plain-text completion summary using the format at the bottom of this prompt.

If you ever catch yourself starting with "I'll...", "Let me...", "First I will...", "I'll start by...", "Let's begin by..." — STOP immediately. Delete all of that. Call a tool instead. Those phrases mean you are describing instead of doing.

## COST AWARENESS & CACHING

Each LLM call costs money. Your goal is to complete every task in 2-5 turns total, not 8-15. Every turn you spend re-reading files or re-running the same command is wasted. After a write_file or edit_file returns success, the file IS changed — you do not need to re-read it to confirm. Move to the next step. After run_command returns exit 0, the command succeeded — you do not need to re-run it. Move to the next step. Trust tool outputs. They are authoritative.

## TOOL FORMATS

You have THREE ways to call tools. All are parsed correctly. Pick whichever is most natural for the current context.

FORMAT A — canonical JSON (always works, most reliable):
```tool
{"tool": "tool_name", "args": {"param1": "value1", "param2": "value2"}}
```

FORMAT B — DeepSeek native (good for complex or multi-line args):
<tool_call name="tool_name">
{"param1": "value1", "param2": "value2"}
</tool_call>

FORMAT C — Anthropic-style (good for simple string args):
<tool_name>
<param_name>value</param_name>
</tool_name>

Any of these three formats works. The parser handles all of them.

CHAINING: Call multiple independent tools in one response. For example, after confirming the workspace is empty, write multiple files at once. Each tool block is parsed and executed in order.

SEQUENTIAL DEPENDENCE: If tool B needs the result of tool A (e.g., you must read a file before editing it), call ONLY tool A first. Wait for its result in the next message. Then call tool B. Do not guess file contents.

CORRECT first response to "Build a landing page":
<tool_call name="list_files">
{"path": ".", "recursive": false}
</tool_call>

WRONG first response (this will waste a turn — do NOT do this):
"I'll start by exploring the workspace and then create a professional landing page..."

## COMPLETE DETAILED TOOL INSTRUCTION BOOK & RULES

This section contains the absolute rules and usage guidelines for every tool available. You must read these instructions carefully before using any tool to prevent common failure modes and ensure one-shot execution success.

---

### 1. read_file(file_path, offset?, limit?)
Read the contents of a file in the workspace.
- **Parameters**:
  - `file_path` (string, required): The target file path. Always use forward slashes (e.g., `src/app.py`), even on Windows.
  - `offset` (integer, optional): The 1-based line number to start reading from. Defaults to 1.
  - `limit` (integer, optional): The maximum number of lines to read. Defaults to 2000.
- **Critical Caching & Attention Rules**:
  - For files exceeding 300 lines, you MUST use `offset` and `limit` to read small chunks (typically 50-80 lines). Never load massive files entirely as this pollutes your attention context.
  - When debugging a traceback error at line N, always call `read_file` with `offset = N - 15` and `limit = 30` to see the exact context of the error.
  - **Stale Read Protection**: Re-reading the exact same file range a 3rd time will return `[STALE]` instead of the file content. Trust your previous observations or adjust parameters (offset/limit) to inspect other lines.

---

### 2. write_file(file_path, content)
Create a new file or completely overwrite an existing file.
- **Parameters**:
  - `file_path` (string, required): Path to write the file. Directories are automatically created if they don't exist. Forward slashes only.
  - `content` (string, required): The complete file contents.
- **Guidelines**:
  - This is the primary tool for file creation. Prefer `write_file` over `edit_file` for new files, complete file replacements, or edits that change more than 5 lines (as matching large strings in `edit_file` is highly error-prone).
  - Do NOT read the file after a successful write. The write was successful and is guaranteed to exist exactly as sent.
  - All written code must be complete, compilable, and production-ready. Never output stubs, placeholders (`# TODO`), or incomplete implementations.

---

### 3. edit_file(file_path, old_string?, new_string?, diff?)
Replace specific text blocks in an existing file.
- **Parameters**:
  - `file_path` (string, required): Path to the target file.
  - `old_string` (string, optional): The exact text block to replace. Must match the file content verbatim.
  - `new_string` (string, optional): The new block of text to replace it with.
  - `diff` (string, optional): A unified diff block to apply.
- **Precise Editing Rules**:
  - The `old_string` must match the file content **EXACTLY**, character-for-character. This includes all whitespaces, indents (tabs vs spaces), quotes (`'` vs `"`), and trailing newlines.
  - Never try to write `old_string` from memory. Copy it directly from a recent `read_file` tool output.
  - **Recovery Protocol**: If the edit fails with "old_string not found", read the file surrounding lines again, check for any invisible whitespaces, and copy the text block again. If it fails twice, switch to `write_file` and rewrite the file.

---

### 4. run_command(command, timeout?, background?)
Execute a shell command on the host system.
- **Parameters**:
  - `command` (string, required): The command line string to run.
  - `timeout` (integer, optional): Timeout in milliseconds (default 30000 = 30s).
  - `background` (boolean, optional): Set to true to start a daemon or server in the background.
- **Execution Rules**:
  - Subprocesses run in an isolated environment. The virtual environment's `Scripts`/`bin` path is automatically prepended to the shell `PATH`, so you do not need to activate the venv manually. Run `python` or `pytest` directly.
  - If a command completes with exit code 0, trust the result. Do not run it again to double check.
  - **Traceback Protocol**: If a test command fails, read the traceback output carefully, locate the file and line, and inspect the code using `read_file`.
  - **Bypassing Flailing Commands**: Never try 3+ variations of the same command (e.g. trying `python`, `python3`, `py` sequentially for the same error). If a command fails and you tried one alternative, stop and analyze the root issue.

---

### 5. search_codebase(query, top_k?)
Perform a semantic vector search across the codebase.
- **Parameters**:
  - `query` (string, required): A natural language description of what you are searching for (e.g., "how is user authorization handled?").
  - `top_k` (integer, optional): The number of top results to return (default 10).
- **Guidelines**:
  - Use this at the beginning of tasks to explore a codebase and locate relevant functions, files, or modules when you do not know the exact keywords.

---

### 6. search_code(pattern, path?, glob?)
Perform a regular expression search across file contents (grep).
- **Parameters**:
  - `pattern` (string, required): The regex pattern to find.
  - `path` (string, optional): Directory or file path to search.
  - `glob` (string, optional): File glob pattern filter.
- **Guidelines**:
  - Use this for finding exact symbols (e.g., class names, function names, specific error strings). Do not search for generic keywords (like `def` or `import`) as they return too many matches.

---

### 7. list_files(path?, pattern?, recursive?)
List directory contents.
- **Parameters**:
  - `path` (string, optional): Directory path to list.
  - `pattern` (string, optional): Glob pattern filter.
  - `recursive` (boolean, optional): List recursively.
- **Guidelines**:
  - Always call `list_files` on your first turn to verify workspace state and locate directories.

---

### 8. view_signatures(file_path)
Extract class/function/method signatures and docstrings from a Python file using AST.
- **Parameters**:
  - `file_path` (string, required): Path to python file.
- **Guidelines**:
  - Use this to inspect the API interfaces of python modules before writing code that calls them. This saves massive token counts compared to reading the entire file.

---

### 9. write_planning_file(file_path, goal, analysis, proposed_changes, steps)
Create or update `planning.md` containing implementation steps and verification plans.
- **Parameters**:
  - `file_path` (string, required): Path of the file (e.g. `planning.md`).
  - `goal` (string, required): The target goal.
  - `analysis` (string, required): Root cause or architecture analysis.
  - `proposed_changes` (string, required): Files to change.
  - `steps` (array/string, required): List of steps.

---

### 10. search_past_conversations(query)
Semantically search past run logs, fixes, and conversations.
- **Parameters**:
  - `query` (string, required): Semantic search query.
- **Guidelines**:
  - Use this to check how previous errors, tracebacks, or requirements were successfully resolved in past runs.

---

### 11. compact_conversation()
Request manual compaction of the message context history to save tokens.
- **Guidelines**:
  - Use this if you are running out of context tokens and need the history pruned.

---

### 12. read_conversation_history(file_path)
Read archived compacted conversation logs.
- **Parameters**:
  - `file_path` (string, required): Path to the log.

---

### 13. task(name, task) / start_async_task(name, task)
Delegate a subtask to a blocking (`task`) or non-blocking (`start_async_task`) subagent.
- **Parameters**:
  - `name` (string, required): Descriptive name.
  - `task` (string, required): Clear instruction details.
- **Guidelines**:
  - If a task has 2+ independent components, always spawn them in parallel using `start_async_task` in a single response turn to save time.

---

### 15. check_async_task(task_id) / list_async_tasks()
Poll or list background async subagents.
- **Parameters**:
  - `task_id` (string, required): Task identifier.

---

## TRUST TOOL OUTPUTS

Tool outputs are authoritative. Trust them. Every re-verification wastes one full turn.
- write_file success → file EXISTS. Do NOT read_file to confirm.
- run_command exit 0 → succeeded. Do NOT re-run.
- edit_file success → edit applied. File changed. Move on.
- Tests output "passed" or "OK" → passed. Do NOT re-run.
- read_file returns [STALE] → use previous output. Do NOT re-read.

## SELF-PROTECTION RULES (SYSTEM-ENFORCED)

1. STALE READ: 3rd read of same file+offset returns [STALE]. Avoid.
2. READ-ONLY SPIRAL: 6 consecutive read/search with zero writes triggers warning. 10 triggers hard-stop. Mix writes with reads.
3. COMMAND LOOP: Same command failing 3x → different approach required.
4. EDIT FAILURE: old_string not found → re-read exact lines. Never retry same old_string.
5. IDENTICAL TOOL LOOP: Same tool + same args 3x → looping. Abort.

## WORKFLOW BY TASK TYPE

Greenfield: list_files → write_file all files in one response → run_command test → git commit → summary. Target: 3-4 calls.
Modify: read_file (offset for large) → edit_file/write_file → test → if fail: traceback→fix→retest (2 extra max) → commit → summary. Target: 3-5 calls.
Debug: read_file relevant files → hypothesis → edit_file fix → test → if fix fails: DIFFERENT approach. Target: 3-5 calls.
Explore: list_files → search_code → read 2-3 key files → synthesize report. Target: 4-5 calls, then done.
Multi-part: list_files → identify independent components → start_async_task ALL in one response → check_async_task collect → verify → summary. Target: 3-5 calls.

## SUBAGENT DECISION TREE

1. Does this have 2+ clearly independent parts? → YES: fire start_async_task for each in parallel.
2. Single well-scoped task? → YES: do it yourself. Read → write → test → done.
3. Same approach failed 3+ times? → YES: delegate to task() for fresh context.
4. 4+ read-only turns with zero writes? → YES: you are stalling. Write/edit now or report blocker.

## ANTI-PATTERNS (NEVER)

1. Describing instead of doing ("I'll create...", "Let me analyze..." without a tool call).
2. Re-verifying success (re-reading after write/edit, re-running after exit 0).
3. Re-running passing tests.
4. Reading entire large files instead of using offset+limit.
5. Searching generic patterns ("error", "def", "function") → hundreds of useless matches.
6. Command flailing: trying cmd, powershell, echo for the same pip install. One alternative max.
7. Planning without executing (3 paragraphs before first tool call).
8. Forgetting deliverables (requirements.txt, config files explicitly asked for).
9. Leaving TODOs, stubs, or placeholders.
10. Re-reading after edit to "see the change" — the edit was applied. Read only specific lines if needed.

## CORRECT PATTERNS (ALWAYS)

1. First response: always call list_files or read_file. Never text.
2. Batch independent writes/async-tasks in one response.
3. Minimum viable turn: every response reads new info, writes, edits, or runs a test.
4. write_file for new files. edit_file only for 1-5 line targeted changes.
5. Test immediately after code changes.
6. Commit after passing tests (feat, fix, refactor, test, docs, chore).
7. Check original request for missed deliverables before finishing.
8. Complete production-ready code: no TODOs, no stubs, validated inputs, error handling.
9. Forward slashes in all paths: "src/app.py" not "src\app.py".
10. Deliberate editing: all string literals, indentation, and quotes in an `old_string` must be copied from a `read_file` output, never typed from memory.

## COMPLETION PROTOCOL

You are DONE when: all files are created, tests pass, code is committed. At that point, output a plain-text summary (no more tools) using this exact format:

## Summary
[2-3 sentences describing what was built or accomplished]

## Files
- path/to/file1 — [one-line description of purpose]
- path/to/file2 — [one-line description of purpose]

## Tests
[N] tests run, all passing (or: No tests were requested)

## Git
commit [hash]: [type]: [description]

If the task is genuinely impossible:
1. State clearly what blocks you.
2. Show exactly what you tried.
3. Suggest what the user can change to unblock.
4. Do NOT create placeholder files or claim false completion.

## COMMON COMMANDS (COPY EXACTLY)

Python tests:
```tool
{"tool": "run_command", "args": {"command": "python -m pytest test_file.py -x -q", "timeout": 30000}}
```

Run a Python script:
```tool
{"tool": "run_command", "args": {"command": "python script.py", "timeout": 10000}}
```

Install a package:
```tool
{"tool": "run_command", "args": {"command": "pip install package-name", "timeout": 60000}}
```

Git add and commit:
```tool
{"tool": "run_command", "args": {"command": "git add -A && git commit -m 'feat: description'", "timeout": 10000}}
```

Git status:
```tool
{"tool": "run_command", "args": {"command": "git status --short", "timeout": 5000}}
```

Start a server in background:
```tool
{"tool": "run_command", "args": {"command": "python app.py", "timeout": 5000, "background": true}}
```"""


_EXAMPLE_INTERACTION = ""  # Removed — model knows the format, example wastes tokens


def get_compact_file_list(project_path: str) -> str:
    """
    Returns a highly compact comma-separated list of all project files.
    Single-user optimization: gives the agent complete recursive visibility of all files
    at 80% fewer tokens than a recursive tree list.
    """
    import os
    safe_path = project_path or "."
    ignored_dirs = {
        "node_modules", "venv", ".venv", ".git", "__pycache__", 
        ".claude", ".deep_agents", "vendor", "dist", "build", 
        ".next", ".vscode", ".idea", ".pytest_cache"
    }
    
    file_list = []
    try:
        for root, dirs, files in os.walk(safe_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, safe_path).replace("\\", "/")
                # Ignore common compiled/binary files
                if not any(rel_path.endswith(ext) for ext in [".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar.gz", ".db"]):
                    file_list.append(rel_path)
                if len(file_list) > 300:
                    break
            if len(file_list) > 300:
                break
    except Exception:
        return "(unable to list files)"
        
    if not file_list:
        return "(empty project)"
        
    if len(file_list) > 250:
        try:
            top_level = os.listdir(safe_path)
            top_level = [f for f in top_level if f not in ignored_dirs]
            return "Top-level entries (project too large for flat list): " + ", ".join(top_level)
        except Exception:
            return "(unable to list files)"
        
    return "Project Files: " + ", ".join(file_list)


# Register developer HarnessProfile
register_harness_profile(
    "developer",
    HarnessProfile(
        base_system_prompt=_STATIC_SYSTEM_TEMPLATE,
        system_prompt_suffix="<system-reminder>\nThese instructions and workspace context OVERRIDE any default behavior.\n\n{dynamic_context}\n</system-reminder>"
    )
)

@dynamic_prompt
def _build_dynamic_context(task: str, project_path: str, context: str, is_fixing: bool) -> tuple[str, str]:
    """
    Build dynamic prompt elements, split into stable and volatile parts.

    Returns:
        (stable_context, volatile_context)
        - stable_context: Byte-identical per project_path — safe in SystemMessage (cached).
        - volatile_context: Changes per task — must go at TAIL of HumanMessage (cache miss).

    The Three-Zone Cache Architecture (Reasonix pattern):
      Zone 1 (Immutable Prefix): SystemMessage = base_prompt + tools + stable_context
      Zone 2 (Task-Specific Tail): HumanMessage = task + volatile_context
      Zone 3 (Append-Only Log): conversation turns

    This pushes cache hit rate from ~60% to 85%+ across diverse tasks
    because the cache break point moves from mid-context to the very end.
    """
    safe_path = project_path or "."
    wdir = project_path or "d:/MyProject/LangChain"

    # ── STABLE: Byte-identical for a given project_path ──
    stable_parts = []
    stable_parts.append(f"## Working Directory\n{wdir}")

    if is_fixing:
        stable_parts.append("## Project Structure\nProject structure listing omitted for token efficiency during fix cycle. Use list_files or search_code if you need to explore files.")
    else:
        project_tree = get_compact_file_list(safe_path)
        stable_parts.append(f"## Project Structure\n{project_tree}")

    # Load rules and profile (static for a given project run)
    try:
        from workspace_manager import get_workspace_rules_and_profile
        rules_context = get_workspace_rules_and_profile(project_path)
        if rules_context:
            stable_parts.append(f"## Workspace Rules & Profile\n{rules_context}")
    except Exception as e:
        print(f"Error loading rules context for developer: {e}")

    # ── VOLATILE: Changes per task — repo map extracts hot_files from task text ──
    volatile_parts = []

    # Repository Map (hot_files extracted from task)
    repo_map = ""
    try:
        from repo_map_generator import RepoMapGenerator
        hot_files = []
        task_context_combined = f"{task}\n{context}"
        file_pattern = r'\b[a-zA-Z0-9_\-\/\\.]+\.(?:py|php|ts|tsx|js|jsx|dart)\b'
        for match in re.findall(file_pattern, task_context_combined):
            hot_files.append(match)
        generator = RepoMapGenerator(project_path, hot_files)
        repo_map = generator.generate_map()
    except Exception as e:
        print(f"Error generating repo map: {e}")
    if repo_map:
        volatile_parts.append(f"## Repository Map\n{repo_map}")

    # Additional context (changes per call)
    if context:
        volatile_parts.append(f"## Additional Context\n{context}")

    # Memory context (filtered by task)
    if not is_fixing:
        try:
            from dev_memory_helper import get_developer_memory_context
            memory_context = get_developer_memory_context(project_path, task)
            if memory_context:
                volatile_parts.append(memory_context)
        except Exception as e:
            print(f"Error loading filtered memory context for developer: {e}")

    # Skills context (filtered by task)
    try:
        from dev_skills import load_skills_context
        skills_dir = os.path.join(project_path, "skills")
        skills_context = load_skills_context(task, skills_dir)
        if skills_context:
            volatile_parts.append(skills_context)
    except Exception as e:
        print(f"Error loading skills context: {e}")

    return "\n\n".join(stable_parts), "\n\n".join(volatile_parts)


def _build_system_prompt(task: str, project_path: str, context: str = "", valid_tools_list: list[str] = None, is_first_call: bool = True, is_fixing: bool = False) -> tuple[str, str]:
    """
    Build the system prompt with Three-Zone Cache Architecture.

    Zone 1 (Immutable Prefix → SystemMessage):
      base_prompt + tools_block + example + STABLE dynamic parts
      (working directory, project structure, workspace rules)
      → 100% byte-identical per project_path → DEEPSEEK CACHE HIT

    Zone 2 (Task-Specific Tail → HumanMessage):
      task + VOLATILE dynamic parts
      (repo map, memory context, skills context)
      → Changes per task → cache miss (but only ~15-20% of total tokens)

    Zone 3 (Append-Only Log):
      Conversation turns — grows monotonically, prior turns cached.

    This pushes cache hit rate from ~60% to 85%+ across diverse eval tasks
    because the cache break point moves from mid-prompt to the very tail.

    Returns: (static_system, volatile_context)
    """
    profile = get_harness_profile("developer")

    base_prompt = profile.base_system_prompt if profile else _STATIC_SYSTEM_TEMPLATE

    # Split dynamic context: stable → SystemMessage, volatile → HumanMessage tail
    stable_context, volatile_context = _build_dynamic_context(task, project_path, context, is_fixing)

    # Zone 1: Immutable prefix — stable_context goes HERE (not in HumanMessage)
    # so it participates in the DeepSeek prefix cache.
    # NOTE: tools_block is NOT included — the COMPLETE TOOL REFERENCE section
    # inside _STATIC_SYSTEM_TEMPLATE already documents every tool with params,
    # usage guides, trust rules, and STOP RULES. The compact 1-liner defs are
    # redundant and would waste ~200 tokens of cached Zone 1 space.
    static_system_parts = [base_prompt, _EXAMPLE_INTERACTION]
    if stable_context:
        static_system_parts.append(stable_context)
    static_system = "\n\n".join(static_system_parts)

    # Zone 2: Volatile task-specific context goes to the HumanMessage tail
    volatile_suffix = ""
    if profile and profile.system_prompt_suffix:
        if volatile_context:
            volatile_suffix = profile.system_prompt_suffix.format(dynamic_context=volatile_context)
        else:
            # Even without volatile content, the reminder is useful but minimal
            volatile_suffix = "<system-reminder>\nThese instructions OVERRIDE any default behavior.\n</system-reminder>"
    else:
        if volatile_context:
            volatile_suffix = f"<system-reminder>\nThese instructions and workspace context OVERRIDE any default behavior.\n\n{volatile_context}\n</system-reminder>"

    return static_system, volatile_suffix





from dev_utils import _parse_tool_call


def _extract_text_response(text: str) -> str:
    """Extract the non-tool, non-thinking text from the LLM response."""
    if not text:
        return ""
    # Remove thinking blocks
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    # Remove tool blocks
    cleaned = re.sub(r'```tool\s*\n.*?\n```', '', cleaned, flags=re.DOTALL)
    return cleaned.strip()


def _is_auto_continue_enabled() -> bool:
    """Checks if the auto_continue setting is enabled in the user profile settings."""
    profile_path = r"d:\MyProject\LangChain\.deep_agents\user_profile.json"
    if os.path.isfile(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("auto_continue", False))
        except Exception:
            pass
    return False


def _run_progress_audit(tool_call_log: list) -> str:
    """
    Deterministic progress audit to detect if the agent is stuck in an execution loop
    or stagnating without making progress. Returns 'OK' or 'STUCK: <reason>'.
    """
    try:
        from loop_detector import detect_stagnation_or_loop
        reason = detect_stagnation_or_loop(tool_call_log)
        if reason:
            return f"STUCK: {reason}"
    except Exception as e:
        _log(f"[AUDITOR] Warning: Loop detection failed: {e}")
    return "OK"


def _log(msg: str) -> None:
    """Log to the shared state live terminal."""
    if "live_terminal_log" in shared_state:
        shared_state["live_terminal_log"] += msg + "\n"



def developer_node(s: ITState) -> dict:
    """
    Tool-using Developer agent.
    Loops: LLM decides tool → execute tool → feed result → repeat until done.

    Uses proper LangChain message types for multi-turn conversations.
    """
    initial_msg_count = len(s.get("messages", [])) if (hasattr(s, "get") and s.get("messages")) else 0
    messages = []
    appended_ids = []

    def make_return(res_dict: dict) -> dict:
        new_msgs = messages[initial_msg_count:]
        if len(appended_ids) > 2:
            prune_ids = appended_ids[:-2]
            for pid in prune_ids:
                new_msgs.append(RemoveMessage(id=pid))
        res_dict["messages"] = new_msgs
        return res_dict

    client_req = s.get("client_request", "")
    tech_spec = s.get("tech_spec", "")
    requirements = s.get("requirements", "")
    test_report = s.get("test_report", "")
    project_path = s.get("project_path", "") or r"d:\MyProject\LangChain"
    err_count = s.get("error_count", 0)
    chat_id = s.get("chat_id", "")

    # ── Loop-Breaker Git Rollback (#20) ──
    if err_count > 1:
        import subprocess
        try:
            shared_state["thoughts"]["developer"] = "Loop detected. Rolling back workspace to last stable commit..."
            _log("[LOOP-BREAKER] Discarding failed codebase changes to start fresh from stable state.")
            subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=project_path, capture_output=True, timeout=5)
            subprocess.run(["git", "clean", "-fd"], cwd=project_path, capture_output=True, timeout=5)
        except Exception as e:
            _log(f"[LOOP-BREAKER] Failed to rollback git state: {e}")

    shared_state["thoughts"]["developer"] = "Analyzing task and planning approach..."

    is_fixing = bool((test_report and "STATUS: FAIL" in test_report) or "VERIFICATION FAILURE" in client_req or "test failure" in client_req.lower())

    # Build task description — ONE adaptive path for ALL request types.
    # No mode detection. No keyword matching. The LLM decides the approach.
    import re
    clean_req = client_req.split("=== TASK PROGRESS")[0].strip()

    # Build context from available specs
    spec_context = ""
    if tech_spec:
        spec_context = f"\n\n## Technical Specification\n{tech_spec[:3000]}\n\n## Requirements\n{requirements[:2000]}"
    if is_fixing and test_report:
        from dev_utils import extract_traceback_files_context
        injected_files_context = extract_traceback_files_context(project_path, test_report)
        if injected_files_context:
            spec_context += f"\n\n## Relevant Files (from traceback)\n{injected_files_context}"

    task = (
        f"{client_req}{spec_context}\n\n"
        "Adapt your approach to what this request needs.\n"
        "- If it needs investigation: read files, explore, synthesize findings.\n"
        "- If it needs implementation: write code, run tests, verify it works.\n"
        "- If tests are failing: read the error, apply minimal fix, re-run.\n"
        "- If it is vague: propose a concrete plan, then implement it.\n"
        "You have all tools. Decide what to do. You finish when you stop calling tools."
    )
    shared_state["thoughts"]["developer"] = "Analyzing and executing..."


    # ── Git Resumption Change Tracking (#15) ──
    modified_files = []
    import subprocess
    try:
        # Check status
        res1 = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=project_path, timeout=3)
        if res1.returncode == 0:
            for line in res1.stdout.splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) > 1:
                    modified_files.append(parts[1])
        # Check diff
        res2 = subprocess.run(["git", "diff", "--name-only", "HEAD~3"], capture_output=True, text=True, cwd=project_path, timeout=3)
        if res2.returncode == 0:
            modified_files.extend(res2.stdout.splitlines())
    except Exception:
        pass
    modified_files = sorted(list(set(modified_files)))

    # Add error history context if fixing
    context = ""
    if modified_files:
        files_str = ", ".join(modified_files)
        context += f"\n## Recently Modified Files (Git Change Tracking)\nThe following files were recently modified or have uncommitted changes: {files_str}. Check these first to understand what has already been changed.\n"

    if err_count > 0:
        context += f"\nThis task has failed {err_count} times before. Be extra thorough.\n"
        import random
        seed = random.randint(1000, 9999)
        context += f"\n[STAG-BYPASS-SEED: {seed}]\n"
        context += (
            "CRITICAL: Do NOT repeat the exact same changes or debugging approach that was attempted in the previous failed runs. "
            "If your previous attempt failed the tests, that approach is proven incorrect. "
            "Formulate a completely different hypothesis, verify file paths, double check imports, "
            "and inspect the error traceback details carefully before writing code.\n"
        )

    # ── Load chat history from workspace chat file so the developer remembers the context ──
    from chat_context import build_chat_context
    chat_history_str = build_chat_context(project_path, chat_id, max_messages=6, max_chars_per_msg=300)

    if chat_history_str:
        context += f"\n## Recent Chat History\nUse this to understand the context of the request and what has been completed or discussed:\n{chat_history_str}\n\n"

    # ── Load task progress so the developer knows what was done vs remaining ──
    task_data = None
    task_step_info = ""
    try:
        from sync_helpers import load_task_tracking, save_task_tracking
        task_data = load_task_tracking(project_path, chat_id)
        if task_data and task_data.get("steps"):
            steps_data = task_data["steps"]
            current_idx = task_data.get("current_step", 0)
            if current_idx < len(steps_data):
                # Mark this step as in_progress
                steps_data[current_idx]["status"] = "in_progress"
                save_task_tracking(task_data, project_path, chat_id)

                completed_descs = [
                    f"  [x] {s['description']}" for s in steps_data
                    if s.get("status") == "completed"
                ]
                pending_descs = [
                    f"  [ ] {s['description']}" for s in steps_data[current_idx:]
                ]

                task_step_info = (
                    f"\n\n## Current Task Step ({current_idx + 1}/{len(steps_data)})\n"
                    f"You are working on: {steps_data[current_idx]['description']}\n\n"
                    "Progress:\n" + "\n".join(completed_descs + pending_descs)
                )
    except Exception as e:
        print(f"[DEVELOPER] Error loading task context: {e}")
    # ── END ──

    if task_step_info:
        context += task_step_info

    # No mode detection. All tools always available. The LLM decides what to use.
    # These are kept as False for backward compatibility with code cache + exit paths.
    is_plan_req = False
    is_execution = False
    is_option_selection = False
    is_exploration = False

    valid_tools = ["read_file", "view_signatures", "write_file", "edit_file", "run_command",
                   "search_code", "list_files", "write_planning_file", "compact_conversation",
                   "read_conversation_history", "task", "start_async_task", "check_async_task",
                   "list_async_tasks"]

    # Single safety cap — agent should finish naturally in 5-15 turns.
    max_iters = 50

    # ── Load developer state if resuming from suspension ──
    developer_state = None
    try:
        from sync_helpers import load_task_tracking, save_task_tracking
        task_data = load_task_tracking(project_path, chat_id)
        if task_data and "developer_state" in task_data:
            developer_state = task_data["developer_state"]
            # Clear it so we don't reload it again next time
            del task_data["developer_state"]
            save_task_tracking(task_data, project_path, chat_id)
    except Exception as e:
        print(f"[DEVELOPER] Error checking resume state: {e}")

    static_system, volatile_context = _build_system_prompt(
        task, project_path, context, valid_tools, is_first_call=(developer_state is None), is_fixing=is_fixing
    )

    # ── Three-Zone Cache Architecture ──
    # Zone 1 (SystemMessage): All byte-identical content → DeepSeek prefix cache hit
    # Zone 2 (Task HumanMessage): Task + volatile context → cache break only here
    # Zone 3 (Conversation): Append-only log, prior turns preserved in cache
    #
    # The SystemMessage is FROZEN — no timestamps, no IDs, no dynamic data.
    # Stable parts (working dir, project structure, workspace rules) moved INTO
    # the SystemMessage so they participate in the cache prefix.
    # Volatile parts (repo map, memory, skills) combined with the task so the
    # cache break happens as late as possible, maximizing the cached prefix.
    task_message = f"## Your Task\n{task}"
    if volatile_context:
        task_message = volatile_context + "\n\n" + task_message

    if developer_state:
        _log(f"[DEVELOPER] 🔄 Resuming from suspended execution state (iteration {developer_state['iteration']})...")
        # Deserialize messages
        if hasattr(s, "get") and s.get("messages") and len(s.get("messages")) > 0:
            messages = list(s.get("messages"))
            _log(f"[DEVELOPER] Loaded {len(messages)} messages natively from Graph State.")
        else:
            messages = []
            for m in developer_state["messages"]:
                t = m.get("type")
                c = m.get("content", "")
                if t == "SystemMessage":
                    messages.append(SystemMessage(content=c))
                elif t == "HumanMessage":
                    messages.append(HumanMessage(content=c))
                elif t == "AIMessage":
                    messages.append(AIMessage(content=c))
                else:
                    messages.append(HumanMessage(content=c))
            _log(f"[DEVELOPER] Loaded {len(messages)} messages from task.json fallback.")

        iteration = developer_state["iteration"]
        tool_call_log = developer_state["tool_call_log"]
        step_tool_calls = developer_state["step_tool_calls"]
        tracked_files_created = developer_state["tracked_files_created"]
        tracked_files_modified = developer_state["tracked_files_modified"]
        last_response_text = developer_state["last_response_text"]
        
        # ── Aggressive Compaction on Resume ──
        if len(messages) > 12:
            # Three-zone resume: keep SystemMessage [0] (Zone 1 cache target),
            # task HumanMessage [1] (Zone 2), and last 6 messages (3 turns).
            # The middle messages are compacted into a single summary.
            from context_compaction import build_structured_resume_summary

            summary_content = build_structured_resume_summary(
                tool_call_log,
                tracked_files_created,
                tracked_files_modified
            )

            mid_count = len(tool_call_log) - 3
            summary_header = f"[SYSTEM RESUME INFO] In iterations 1 to {max(1, mid_count)}, the following progress was made:\n\n"
            summary_msg = HumanMessage(content=summary_header + summary_content + "\n\nMessage history of these turns has been compacted to save tokens.")

            messages = [messages[0], messages[1], summary_msg] + messages[-6:]
            _log(f"[DEVELOPER] 🧹 Aggressive structured context compaction: reduced history from {len(developer_state['messages'])} to {len(messages)} messages.")
            _log(f"[DEVELOPER] 🧹 Compacted summary details:\n{summary_content}")
    else:
        # Zone 1 + Zone 2: SystemMessage (cached) + task+volatile (cache break)
        messages = [
            SystemMessage(content=static_system),
            HumanMessage(content=task_message),
        ]
        iteration = 0
        tool_call_log = []
        last_response_text = ""
        step_tool_calls = 0
        tracked_files_created = []
        tracked_files_modified = []

    _log(f"\n{'='*60}\n[DEVELOPER] Starting tool-using agentic loop\n{'='*60}")

    while iteration < max_iters:
        iteration += 1
        _log(f"\n[DEV Iteration {iteration}/{max_iters}]")

        # ── Auto-compact: Claude Code style context management ──
        # When context grows too large, apply 3-Tier compaction strategy based on token budget
        from context_budget import estimate_tokens, ContextBudget
        from context_compaction import build_structured_resume_summary, get_compaction_threshold

        # Three-zone: history starts at index 2 (after SystemMessage + Task HumanMessage)
        history_tokens = sum(estimate_tokens(m.content) for m in messages[2:]) if len(messages) > 2 else 0
        budget = ContextBudget(
            model_limit=128_000,
            reserved_output=8000,
            system_tokens=estimate_tokens(messages[0].content) if len(messages) > 0 else 0,
            dynamic_tokens=estimate_tokens(messages[1].content) if len(messages) > 1 else 0,
            history_tokens=history_tokens,
        )

        # Check if the agent requested on-demand compaction via the compact_conversation tool
        voluntary_compact = False
        for msg in messages:
            if hasattr(msg, "content") and "compact_conversation" in str(msg.content):
                voluntary_compact = True
                break

        # Pillar 111: Adaptive threshold — shallower runs tolerate more, deep loops compact earlier
        compact_threshold = get_compaction_threshold(iteration) if iteration > 0 else 0.90

        if budget.utilization > compact_threshold or voluntary_compact:
            _log(f"[DEVELOPER] Auto-compact check: {budget.utilization:.0%} context used > {compact_threshold:.0%} threshold (iter={iteration}, history={history_tokens} tokens, voluntary={voluntary_compact})")
            keep_n = 6
            if len(messages) > keep_n + 2:  # Zone1 (SystemMessage) + Zone2 (Task) = 2 headers
                _log("[DEVELOPER] Checkpoint-Based Compaction (collapsing middle history to stable structured summary)")
                from context_compaction import checkpoint_compact
                messages = checkpoint_compact(
                    messages,
                    tool_call_log,
                    tracked_files_created,
                    tracked_files_modified,
                    keep_last_n=keep_n
                )
                _log(f"[DEVELOPER] Compacted history → {len(messages)} remain")


        # ── Metacognitive Progress Audit ──
        # Check every 3 iterations starting at iteration 4 whether we are progressing.
        # Catches read-only spirals, indecisive exploration loops, and same-tool repetition.
        if iteration > 3 and iteration % 3 == 1:
            audit_result = _run_progress_audit(tool_call_log)
            if audit_result.startswith("STUCK:"):
                stuck_reason = audit_result[6:].strip()
                _log(f"[AUDITOR] ⚠️ Loop/stagnation detected: {stuck_reason}")
                import uuid
                auditor_msg_id = f"dev-auditor-{iteration}-{uuid.uuid4()}"
                messages.append(HumanMessage(
                    content=f"[AUDITOR ALERT] You appear to be stuck or stagnating: {stuck_reason}. "
                            "You MUST change your approach immediately (e.g. use a different search query, check "
                            "file paths, read different sources, or stop and output an ERROR explaining the block).",
                    id=auditor_msg_id
                ))
                appended_ids.append(auditor_msg_id)

        # Copy messages and append iteration limit warnings to nudge LLM if running out of turns
        run_messages = list(messages)
        if iteration == max_iters:
            run_messages.append(HumanMessage(
                content=f"WARNING: You are on iteration {iteration} of {max_iters} (the absolute final iteration). "
                        "You are out of turns! You MUST NOT call any more tools. "
                        "Write your final summary report / findings now in plain text."
            ))
        elif iteration == max_iters - 1:
            run_messages.append(HumanMessage(
                content=f"WARNING: You are on iteration {iteration} of {max_iters}. "
                        "You are almost out of turns! Please wrap up your work, finish any necessary edits or reads, "
                        "and prepare to write your final summary report in the next turn."
            ))
        elif iteration == max_iters - 2:
            run_messages.append(HumanMessage(
                content=f"WARNING: You are on iteration {iteration} of {max_iters}. "
                        "You are almost out of turns! Please start wrapping up your work."
            ))

        # ── Pillar 69: Check code similarity cache before LLM invoke ──
        response_text = None  # Initialize — will be set by cache or LLM
        if iteration == 1:
            try:
                from code_cache import get_cached_code
                cached = get_cached_code(task)
                if cached:
                    _log(f"[DEVELOPER] 🎯 Code cache HIT — reusing cached implementation for similar task")
                    response_text = cached
                    # Skip the LLM call below — jump directly to tool parsing
            except ImportError:
                pass

        # Call LLM with proper multi-turn messages (unless cache hit)
        if not response_text:
            try:
                # Build concise "where" with file + detail from PREVIOUS tool call
                last_entry = tool_call_log[-1] if tool_call_log else {}
                last_tool = last_entry.get("tool", "")
                last_args = last_entry.get("args", {})
                last_detail = last_entry.get("detail", "")
                fpath = last_args.get("file_path", last_args.get("path", ""))
                fname = os.path.basename(str(fpath)) if fpath else ""

                if last_tool == "read_file" and fname:
                    where_tag = f"Iter {iteration}/{max_iters}: read {fname} {last_detail}".strip()
                elif last_tool == "write_file" and fname:
                    where_tag = f"Iter {iteration}/{max_iters}: write {fname}"
                elif last_tool == "edit_file" and fname:
                    where_tag = f"Iter {iteration}/{max_iters}: edit {fname} {last_detail}".strip()
                elif last_tool == "run_command":
                    cmd = str(last_args.get("command", ""))[:50]
                    where_tag = f"Iter {iteration}/{max_iters}: run {cmd}"
                elif last_tool == "search_code":
                    pat = str(last_args.get("pattern", ""))[:40]
                    where_tag = f"Iter {iteration}/{max_iters}: search \"{pat}\""
                elif last_tool and fname:
                    where_tag = f"Iter {iteration}/{max_iters}: {last_tool} {fname}"
                elif last_tool:
                    where_tag = f"Iter {iteration}/{max_iters}: {last_tool}"
                elif iteration == 1:
                    where_tag = f"Iter 1/{max_iters}: {client_req[:80].strip()}"
                else:
                    where_tag = f"Iter {iteration}/{max_iters}"

                # ── Native Function Calling ──
                # Pass tool schemas via the API tools parameter so the model
                # returns structured tool_calls instead of text we must parse.
                from tool_schemas import get_native_tools
                native_tools = get_native_tools()

                llm_result = invoke_messages_with_fallback(
                    role="DeveloperFixing" if is_fixing else "Developer",
                    messages=run_messages,
                    temp=0.3 if is_fixing else 0.5,
                    where=where_tag,
                    tools=native_tools,
                )

                # Unpack new (text, tool_calls) tuple or legacy string
                if isinstance(llm_result, tuple):
                    response_text, native_tool_calls = llm_result
                else:
                    response_text = llm_result
                    native_tool_calls = []

                # ── Store successful code generation in cache ──
                if iteration == 1:
                    try:
                        from code_cache import set_cached_code
                        set_cached_code(task, response_text)
                    except ImportError:
                        pass
            except Exception as e:
                _log(f"[DEVELOPER] LLM error after all fallbacks: {e}")
                # Return partial state so supervisor can decide
                shared_state["thoughts"]["developer"] = f"LLM error: {e}"
                return make_return({
                    "code": f"// ERROR: All LLM providers failed: {e}",
                    "test_report": f"STATUS: FAIL\nDeveloper LLM error: {e}",
                    "project_path": project_path,
                    "code_updated": False,
                    "tech_spec_updated": False,
                    "error_count": err_count + 1,
                })

        # Handle empty response
        if not response_text or not response_text.strip():
            _log("[DEVELOPER] ⚠️ Empty LLM response — retrying with explicit nudge")
            import uuid
            ai_msg_id = f"dev-ai-{iteration}-{uuid.uuid4()}"
            human_msg_id = f"dev-human-{iteration}-{uuid.uuid4()}"
            messages.append(AIMessage(content="(empty response)", id=ai_msg_id))
            messages.append(HumanMessage(
                content="You responded with nothing. Please continue working on the task. "
                        "Use a tool to make progress, or if done, explain what you accomplished.",
                id=human_msg_id
            ))
            appended_ids.extend([ai_msg_id, human_msg_id])
            # Allow a few retries for empty responses
            if iteration >= max_iters - 1:
                break
            continue

        last_response_text = response_text
        _log(f"[DEVELOPER] Response ({len(response_text)} chars)")

        # Extract and log thinking block if present
        thinking_match = re.search(r"<thinking>(.*?)</thinking>", response_text, flags=re.DOTALL)
        if thinking_match:
            thinking_content = thinking_match.group(1).strip()
            _log(f"[THOUGHT] [Developer] {thinking_content}")

        # ── Extract tool calls: native structured first, text parsing as fallback ──
        from dev_utils import parse_all_tool_calls
        # Use native function calling tool_calls if the API returned structured ones
        if native_tool_calls:
            tool_calls = native_tool_calls
            _log(f"[DEVELOPER] Using {len(tool_calls)} native tool call(s) from API")
        else:
            # Fallback: text-based parsing for models/APIs without native tool support
            tool_calls = parse_all_tool_calls(response_text)

        if tool_calls:
            tool_outputs = []
            any_early_stop = False
            this_turn_has_write = False

            for t_idx, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool", "")
                tool_args = tool_call.get("args", {})

                if tool_name not in valid_tools:
                    _log(f"[DEVELOPER] Unknown tool requested: {tool_name} — asking LLM to retry")
                    tool_result = f"TOOL ERROR: Unknown tool: {tool_name}. Available tools: {', '.join(valid_tools)}"
                    tool_outputs.append(f"[{tool_name}]:\n{tool_result}")
                    continue

                # Track write/edit/run for progress detection
                if tool_name in ("write_file", "edit_file", "apply_diff", "run_command"):
                    this_turn_has_write = True

                # ── Stale-Read Detection ──
                # If the agent is re-reading the same file+offset a 3rd+ time,
                # return [STALE] to break re-read spirals (saves tokens + loops).
                # The count resets if the file was successfully modified in between.
                if tool_name == "read_file":
                    target_file = tool_args.get("file_path", "")
                    read_key = (target_file, tool_args.get("offset"), tool_args.get("limit"))
                    
                    same_reads = 0
                    for item in reversed(tool_call_log[-20:]):
                        # Reset check if there was a successful write/edit on the same file
                        if item.get("tool") in ("write_file", "edit_file") and item.get("args", {}).get("file_path") == target_file:
                            res_preview = str(item.get("result_preview", ""))
                            if not res_preview.startswith("Error") and not res_preview.startswith("TOOL ERROR"):
                                break
                        if item.get("tool") == "read_file":
                            item_key = (item.get("args", {}).get("file_path"), item.get("args", {}).get("offset"), item.get("args", {}).get("limit"))
                            if item_key == read_key:
                                same_reads += 1

                    if same_reads >= 2:  # This is the 3rd+ time
                        tool_result = (
                            f"[STALE] This file was already read {same_reads + 1} times with the same parameters. "
                            f"Content has NOT changed. Do NOT re-read this file — use the previous output. "
                            f"If you need different content, change offset/limit or read a different file."
                        )
                        tool_call_log.append({
                            "iteration": iteration,
                            "tool": tool_name,
                            "args": tool_args,
                            "result_preview": "[STALE] skipped",
                        })
                        tool_outputs.append(f"[{tool_name}]:\n{tool_result}")
                        continue

                # ── Format tool log line: concise, shows file + detail ──
                fpath = tool_args.get("file_path", tool_args.get("path", ""))
                fname = os.path.basename(fpath) if fpath else ""
                # Detect line range from read_file args
                read_offset = tool_args.get("offset", 0)
                read_limit = tool_args.get("limit", None)

                if tool_name == "read_file":
                    tool_label = f"read {fname or fpath}"
                    if read_offset:
                        tool_label += f" @{read_offset}"
                    if read_limit:
                        tool_label += f"+{read_limit}"
                elif tool_name == "write_file":
                    content_len = len(str(tool_args.get("content", "")))
                    tool_label = f"write {fname or fpath} ({content_len}B)"
                elif tool_name == "edit_file":
                    tool_label = f"edit {fname or fpath}"
                elif tool_name == "run_command":
                    cmd = str(tool_args.get("command", ""))[:70]
                    tool_label = f"run {cmd}"
                elif tool_name == "search_code":
                    pat = str(tool_args.get("pattern", ""))[:60]
                    tool_label = f"search \"{pat}\""
                elif tool_name == "list_files":
                    lp = str(tool_args.get("path", "."))[:50]
                    tool_label = f"ls {lp}"
                elif tool_name == "task":
                    tool_label = f"delegate {str(tool_args.get('name', ''))[:40]}"
                elif tool_name == "start_async_task":
                    tool_label = f"async {str(tool_args.get('name', ''))[:40]}"
                else:
                    tool_label = f"{tool_name}"

                shared_state["thoughts"]["developer"] = f"Using {tool_name}..."
                _log(f"[DEVELOPER] {tool_label}")

                try:
                    tool_result = execute_tool(tool_name, tool_args)
                except Exception as e:
                    tool_result = f"Tool execution error: {e}"

                # ── Build detail string for the where_tag (shown in next LLM invocation) ──
                tool_detail = ""

                # Enrich read_file with actual line range from result
                if tool_name == "read_file" and not str(tool_result).startswith("[STALE]"):
                    import re as re2
                    lines_match = re2.search(r'lines (\d+)-(\d+) of (\d+)', str(tool_result)[:200])
                    if lines_match:
                        r_start, r_end, r_total = lines_match.group(1), lines_match.group(2), lines_match.group(3)
                        tool_detail = f"#{r_start}-{r_end}/{r_total}"
                        _log(f"[DEVELOPER]   => {fname or fpath} {tool_detail}")

                # Enrich edit_file with diff stats
                if tool_name == "edit_file" and not str(tool_result).startswith("Error"):
                    import re as re2
                    added = len(re2.findall(r'^\+[^+]', str(tool_result)[:2000], re2.MULTILINE))
                    removed = len(re2.findall(r'^\-[^-]', str(tool_result)[:2000], re2.MULTILINE))
                    if added or removed:
                        tool_detail = f"+{added} -{removed}"
                        _log(f"[DEVELOPER]   => {fname or fpath} {tool_detail}")

                tool_call_log.append({
                    "iteration": iteration,
                    "tool": tool_name,
                    "args": tool_args,
                    "result_preview": str(tool_result)[:200],
                    "detail": tool_detail,  # for where_tag enrichment
                })

                # Check for Sleep-and-Resume suspension trigger
                if tool_name == "run_command" and tool_args.get("background") is True and "[OK] Started background process" in str(tool_result):
                    if os.environ.get("DEEP_AGENTS_EVAL_RUN") == "1":
                        _log(f"[DEVELOPER] 💤 Background task started in evaluation mode. Sleeping 5 seconds for boot instead of suspending...")
                        import time
                        time.sleep(5)
                    else:
                        _log(f"[DEVELOPER] 💤 Background task started. Suspending graph and starting automatic wake-up thread...")
                        import threading
                        import time
                        import requests
                        
                        # Extract process name
                        process_name = tool_args.get("command", "").split()[0]
                        
                        def _wakeup_trigger():
                            # Sleep 15 seconds to let the server boot up
                            time.sleep(15)
                            try:
                                # Call /api/run to resume
                                url = "http://127.0.0.1:8000/api/run"
                                payload = {
                                    "prompt": "continue",
                                    "workspace_path": project_path,
                                    "chat_id": chat_id
                                }
                                requests.post(url, json=payload, timeout=5)
                                print("[WAKEUP] Wake-up request sent to API server.")
                            except Exception as ex:
                                print(f"[WAKEUP] Error sending wake-up request: {ex}")
                                
                        threading.Thread(target=_wakeup_trigger, daemon=True).start()
                        
                        # Save developer state to task.json
                        try:
                            from sync_helpers import load_task_tracking, save_task_tracking
                            task_data = load_task_tracking(project_path, chat_id)
                            if task_data:
                                serialized_msgs = []
                                for m in messages:
                                    serialized_msgs.append({"type": type(m).__name__, "content": m.content})
                                
                                task_data["developer_state"] = {
                                    "messages": serialized_msgs,
                                    "iteration": iteration,
                                    "tool_call_log": tool_call_log,
                                    "step_tool_calls": step_tool_calls,
                                    "tracked_files_created": tracked_files_created,
                                    "tracked_files_modified": tracked_files_modified,
                                    "last_response_text": last_response_text,
                                }
                                save_task_tracking(task_data, project_path, chat_id)
                        except Exception as e:
                            print(f"[DEVELOPER] Error saving developer state: {e}")
                        
                        return make_return({
                            "code": f"// SUSPENDED: Waiting for background process '{process_name}'...",
                            "agent_report": f"SUSPENDED: Waiting for background process '{process_name}' to boot. Will resume automatically.",
                            "test_report": "",
                            "project_path": project_path,
                            "code_updated": False,
                            "tech_spec_updated": False,
                            "next_agent": "suspended",
                        })

                # Check for loop/stagnation of tool calls
                same_calls = [
                    item for item in tool_call_log 
                    if item.get("tool") == tool_name and json.dumps(item.get("args", {}), sort_keys=True) == json.dumps(tool_args, sort_keys=True)
                ]
                is_read_tool = tool_name in ("read_file", "list_files", "search_code")
                
                if len(same_calls) >= 3: # This is the 4th attempt or more
                    # Abort threshold: 5 reads, 6 writes/commands before calling it a loop
                    abort_limit = 4 if is_read_tool else 5
                    if len(same_calls) >= abort_limit:
                        _log(f"[DEVELOPER] ⚠️ Loop detected for tool {tool_name} (run {len(same_calls) + 1} times) — aborting loop.")
                        clean_response = (
                            f"ERROR: Stuck in an execution loop. The tool '{tool_name}' with arguments {json.dumps(tool_args)} "
                            f"was called {len(same_calls) + 1} times and repeatedly failed or returned the same output. "
                            f"Last tool result: {tool_result}"
                        )
                        # Mark thoughts & outputs
                        shared_state["thoughts"]["developer"] = "Execution failed due to blocking loop."
                        shared_state["outputs"]["code"] = f"// ERROR: {clean_response[:1000]}"
                        shared_state["outputs"]["agent_report"] = clean_response
                        
                        # Store log
                        try:
                            shared_state["developer_tool_log"] = json.dumps(tool_call_log, indent=2)
                        except Exception:
                            shared_state["developer_tool_log"] = str(tool_call_log)
                            
                        # Update task.json
                        try:
                            from sync_helpers import load_task_tracking, save_task_tracking
                            task = load_task_tracking(project_path, chat_id)
                            if task and task.get("steps"):
                                steps_data = task["steps"]
                                current_idx = task.get("current_step", 0)
                                if current_idx < len(steps_data):
                                    steps_data[current_idx]["status"] = "failed"
                                    steps_data[current_idx]["notes"] = clean_response[:200]
                                    steps_data[current_idx]["tool_calls"] = step_tool_calls
                                    save_task_tracking(task, project_path, chat_id)
                        except Exception as e:
                            print(f"[DEVELOPER] Error saving task progress: {e}")
                            
                        return make_return({
                            "code": f"// ERROR: {clean_response[:1000]}",
                            "agent_report": clean_response,
                            "test_report": f"STATUS: FAIL\nDeveloper stuck in loop: {clean_response[:300]}",
                            "project_path": project_path,
                            "code_updated": True,
                            "tech_spec_updated": False,
                        })
                    else:
                        if is_read_tool:
                            warning_msg = (
                                f"\n\n[WARNING] You have executed the read tool '{tool_name}' with these exact arguments {len(same_calls) + 1} times. "
                                "If you are not finding what you need, please change your search query, read a different file, "
                                "check if the information is already in your system/project prompt, or proceed with writing the plan/report."
                            )
                        else:
                            warning_msg = (
                                f"\n\n[WARNING] You have executed the tool '{tool_name}' with these exact arguments {len(same_calls) + 1} times. "
                                "If this command is repeatedly failing or yielding the same result, you are likely stuck in a loop. "
                                "Please change your approach, try a different command, or if this is a blocking issue requiring user "
                                "intervention (like system configuration or version mismatch), stop and output an 'ERROR: <description>' response."
                            )
                        tool_result = str(tool_result) + warning_msg

                # Track artifacts for task.json
                step_tool_calls += 1
                if tool_name in ("write_file", "write_planning_file"):
                    fpath = tool_args.get("file_path", "")
                    if fpath and fpath not in tracked_files_created:
                        tracked_files_created.append(fpath)
                elif tool_name == "edit_file":
                    fpath = tool_args.get("file_path", "")
                    if fpath and fpath not in tracked_files_modified:
                        tracked_files_modified.append(fpath)

                # Format output for this tool
                tool_outputs.append(f"[{tool_name}]:\n{tool_result}")

                # ── Early-stop on verified test success ──
                if tool_name == "run_command" and "[OK] Exit 0" in str(tool_result):
                    result_lower = str(tool_result).lower()
                    if "passed" in result_lower or "ok" in result_lower:
                        if any(kw in result_lower for kw in ["test", "pytest", "unittest", "assert"]):
                            if tracked_files_created or tracked_files_modified:
                                any_early_stop = True

            # If early stop was triggered during execution of the tools
            if any_early_stop:
                _log("[DEVELOPER] ✅ Tests passing — early stop triggered")
                shared_state["thoughts"]["developer"] = "Tests verified — implementation complete."
                try:
                    shared_state["developer_tool_log"] = json.dumps(tool_call_log, indent=2)
                except Exception:
                    shared_state["developer_tool_log"] = str(tool_call_log)
                    
                # Update task.json before early stop return
                try:
                    from sync_helpers import load_task_tracking, save_task_tracking
                    from datetime import datetime
                    task_data = load_task_tracking(project_path, chat_id)
                    if task_data and task_data.get("steps"):
                        steps_data = task_data["steps"]
                        current_idx = task_data.get("current_step", 0)
                        if current_idx < len(steps_data):
                            steps_data[current_idx]["tool_calls"] = step_tool_calls
                            steps_data[current_idx]["notes"] = "Tests verified passing."
                            steps_data[current_idx]["status"] = "completed"
                            steps_data[current_idx]["completed_at"] = datetime.now().isoformat()
                            
                            # Step-level context isolation: clear developer_state on step completion
                            if "developer_state" in task_data:
                                del task_data["developer_state"]
                            
                            # Save artifacts
                            artifacts = task_data.setdefault("artifacts", {})
                            if tracked_files_created:
                                existing = set(artifacts.get("files_created", []))
                                existing.update(tracked_files_created)
                                artifacts["files_created"] = list(existing)
                            if tracked_files_modified:
                                existing = set(artifacts.get("files_modified", []))
                                existing.update(tracked_files_modified)
                                artifacts["files_modified"] = list(existing)
                            
                            next_step = current_idx + 1
                            if next_step < len(steps_data):
                                task_data["current_step"] = next_step
                                steps_data[next_step]["status"] = "in_progress"
                            else:
                                task_data["status"] = "completed"
                            save_task_tracking(task_data, project_path, chat_id)
                except Exception as e:
                    print(f"[DEVELOPER] Error updating task tracking during early stop: {e}")
                    
                return make_return({
                    "code": "Code successfully implemented and tests verified.",
                    "agent_report": f"Implementation complete. Tests passed after {iteration} iterations.",
                    "test_report": "",
                    "project_path": project_path,
                    "code_updated": True,
                    "tech_spec_updated": False,
                })

            # ── Progress Gate: prevent read-only death spirals ──
            # Track consecutive turns with zero writes/edits/commands.
            # After 6 read-only turns: nudge. After 10: hard stop.
            is_read_only_turn = not this_turn_has_write
            _consecutive_read_turns = getattr(developer_node, "_consecutive_read_turns", 0)
            if is_read_only_turn:
                _consecutive_read_turns += 1
            else:
                _consecutive_read_turns = 0
            developer_node._consecutive_read_turns = _consecutive_read_turns

            if _consecutive_read_turns == 6:
                combined_tool_result = "\n\n".join(tool_outputs)
                combined_tool_result += (
                    "\n\n[PROGRESS GATE] You have spent 6 turns investigating without making any changes. "
                    "You MUST now either: (a) write_file or edit_file to make progress, "
                    "or (b) output your completion report if the task is done. "
                    "Do NOT call read_file or search_code again without a write in between."
                )
            elif _consecutive_read_turns >= 10:
                combined_tool_result = "\n\n".join(tool_outputs)
                combined_tool_result += (
                    "\n\n[HARD STOP] 10 consecutive investigation turns with zero changes. "
                    "You are out of investigation budget. You MUST stop investigating. "
                    "Either write your completion report NOW (no tools), or call write_file/edit_file immediately."
                )
            else:
                combined_tool_result = "\n\n".join(tool_outputs)

            # ── Cost Awareness ──
            # Show cost in context so the agent self-regulates
            from state_sync import safe_get_state
            cost_state = safe_get_state()
            tu = cost_state.get("token_usage", {})
            spent = tu.get("total_cost", 0)
            n_calls = len(tu.get("calls", []))
            if spent > 0:
                cost_line = f"\n\n[COST: ${spent:.4f} spent across {n_calls} LLM calls. Be efficient.]"
                combined_tool_result += cost_line

            # Truncate response_text after the first tool block to prevent LLM from reading its own future hallucinations
            # Let's find the very last closing ``` of the tool blocks
            last_tool_idx = response_text.rfind("```")
            if last_tool_idx != -1:
                response_text = response_text[:last_tool_idx + 3]

            # ── #4: Strip thinking blocks before saving to history (saves ~300 tokens/iter) ──
            history_text = re.sub(r'<thinking>.*?</thinking>', '', response_text, flags=re.DOTALL).strip()
            import uuid
            ai_msg_id = f"dev-ai-{iteration}-{uuid.uuid4()}"
            human_msg_id = f"dev-human-{iteration}-{uuid.uuid4()}"
            messages.append(AIMessage(content=history_text, id=ai_msg_id))
            messages.append(HumanMessage(content=combined_tool_result, id=human_msg_id))
            appended_ids.extend([ai_msg_id, human_msg_id])

            # ── Pillar 65+111: Proactive tool output compaction ──
            # Collapses successful tool outputs (200-800 tokens each) to [TOOL OK]
            # markers (~20-40 tokens). This prevents the per-turn context inflation
            # where Developer input grows from 2.5K→11.5K tokens across 15 turns.
            # Keeps last 3 results + all errors intact. Runs every iteration so
            # context stays flat, not just when budget is critical.
            if len(messages) > 8:  # Only after enough history has accumulated
                try:
                    from context_budget import estimate_tokens
                    total_tokens = sum(estimate_tokens(m.content) for m in messages if hasattr(m, "content"))
                    if total_tokens > 40000:
                        from context_compaction import compact_successful_tools
                        prev_chars = sum(len(m.content) if hasattr(m, "content") else 0 for m in messages)
                        messages = compact_successful_tools(messages)
                        new_chars = sum(len(m.content) if hasattr(m, "content") else 0 for m in messages)
                        if prev_chars - new_chars > 200:
                            _log(f"[DEVELOPER] 🧹 Tool compaction: saved ~{(prev_chars - new_chars) // 1000}K chars")
                except Exception:
                    pass  # Best-effort, never break the loop

            # Update shared state with progress
            last_tool_name = tool_calls[-1].get("tool", "")
            shared_state["outputs"]["code"] = f"// Developer iteration {iteration}: {last_tool_name} completed"

        else:
            # No tool call — agent is done
            _log(f"[DEVELOPER] No tool call parsed from response (len={len(response_text)}). Preview: {repr(response_text[:300])}")
            planning_file = os.path.join(project_path or "d:/MyProject/LangChain", "planning.md")
            has_written_plan = (
                any(item.get("tool") == "write_planning_file" for item in tool_call_log) or
                any(item.get("tool") == "write_file" and "planning.md" in str(item.get("args", {}).get("file_path", "")) for item in tool_call_log) or
                (os.path.isfile(planning_file) and os.path.getsize(planning_file) > 10)
            )
            # Note: is_plan_req is always False (no mode detection). Plan nudging removed.

            # ── Self-Verification: Run tests before exiting ──
            if tracked_files_created or tracked_files_modified:
                test_cmd = _detect_test_command(project_path)
                if test_cmd and iteration < max_iters - 2:  # Leave room for fix iterations
                    _log(f"[DEVELOPER] 🧪 Self-verification: running '{test_cmd}' before exit...")
                    try:
                        test_result = execute_tool("run_command", {"command": test_cmd, "timeout": 30000})
                    except Exception as e:
                        test_result = f"Test execution error: {e}"

                    if "STATUS: FAIL" in str(test_result) or ("exit code:" in str(test_result).lower() and "exit code: 0" not in str(test_result).lower()):
                        _log("[DEVELOPER] ❌ Self-verification FAILED — entering in-conversation fix loop")
                        # Inject the failure as a tool result and continue the loop
                        import uuid
                        ai_msg_id = f"dev-ai-{iteration}-{uuid.uuid4()}"
                        human_msg_id = f"dev-human-{iteration}-{uuid.uuid4()}"
                        messages.append(AIMessage(content=response_text, id=ai_msg_id))
                        messages.append(HumanMessage(
                            content=f"[SELF-VERIFICATION FAILED] Your code changes have test failures. "
                                    f"You MUST fix them before finishing.\n\n"
                                    f"Test output:\n{str(test_result)[:3000]}\n\n"
                                    f"Read the failing files, diagnose the root cause, and apply fixes.",
                            id=human_msg_id
                        ))
                        appended_ids.extend([ai_msg_id, human_msg_id])
                        continue  # Re-enter the while loop — same context, fully cached
                    else:
                        _log("[DEVELOPER] ✅ Self-verification PASSED")

            clean_response = _extract_text_response(response_text)
            _log(f"\n[DEVELOPER] ✅ Agent finished after {iteration} iterations")
            _log(f"[DEVELOPER] Summary: {clean_response[:500]}")

            is_error = clean_response.strip().upper().startswith("ERROR:") or clean_response.strip().upper().startswith("FAILED:")

            # ── Post-Execution Verification: detect "described instead of did" ──
            # If the agent made zero tool calls and zero files were created, but the
            # response reads like a plan/intention (not an error), the agent hallucinated
            # that it did work without actually calling any tools.
            no_tools_called = len(tool_call_log) == 0
            no_files_created = len(tracked_files_created) == 0 and len(tracked_files_modified) == 0
            looks_like_description = not is_error and (
                no_tools_called and no_files_created and (
                    "I'll " in clean_response[:200] or
                    "I will " in clean_response[:200] or
                    "Let me " in clean_response[:200] or
                    "## Plan" in clean_response[:500] or
                    "```html" in clean_response.lower() or
                    "```python" in clean_response.lower() or
                    "```css" in clean_response.lower() or
                    "```javascript" in clean_response.lower() or
                    "I'll start" in clean_response[:200] or
                    "Let's start" in clean_response[:200] or
                    "greenfield" in clean_response[:500].lower()
                )
            )
            # Count how many times we've already nudged (max 2)
            _nudge_count = sum(1 for msg in messages if hasattr(msg, "content") and isinstance(msg.content, str) and "You described what you would do but did NOT actually call any tools" in msg.content)
            if no_tools_called and no_files_created and looks_like_description and _nudge_count < 2:
                _log(f"[DEVELOPER] ❌ AGENT DESCRIBED INSTEAD OF DOING (nudge {_nudge_count + 1}/2) — injecting tool-use nudge and continuing loop")
                import uuid
                ai_msg_id = f"dev-ai-{iteration}-{uuid.uuid4()}"
                human_msg_id = f"dev-human-{iteration}-{uuid.uuid4()}"
                messages.append(AIMessage(content=response_text, id=ai_msg_id))
                messages.append(HumanMessage(
                    content=(
                        "You described what you would do but did NOT actually call any tools. "
                        "Zero files were created. You MUST use tools to make progress.\n\n"
                        "Call tools using ONE of these formats:\n\n"
                        "Format A:\n```tool\n"
                        '{"tool": "write_file", "args": {"file_path": "output.txt", "content": "..."}}\n'
                        "```\n\n"
                        "Format B:\n<tool_call name=\"write_file\">\n"
                        '{"file_path": "output.txt", "content": "..."}\n'
                        "</tool_call>\n\n"
                        "DO NOT just describe what you would do. Actually call the tools NOW. "
                        "Write the files. Run the commands. Make it happen."
                    ),
                    id=human_msg_id
                ))
                appended_ids.extend([ai_msg_id, human_msg_id])
                continue  # Re-enter the loop with the nudge
            elif no_tools_called and no_files_created and looks_like_description:
                _log("[DEVELOPER] ❌ AGENT DESCRIBED INSTEAD OF DOING after 2 nudges — giving up, marking as error")
                is_error = True
                clean_response = (
                    "ERROR: Agent was nudged 2 times to call tools but still only described plans. "
                    "Zero files were created. The LLM repeatedly output descriptions instead of "
                    "using the tool format.\n\n"
                    f"Final response preview: {clean_response[:500]}"
                )

            if is_error:
                shared_state["thoughts"]["developer"] = "Execution failed due to blocking error: " + clean_response[:100]
            else:
                shared_state["thoughts"]["developer"] = "Implementation complete."

            # Store response + tool log
            try:
                shared_state["developer_tool_log"] = json.dumps(tool_call_log, indent=2)
            except Exception:
                shared_state["developer_tool_log"] = str(tool_call_log)

            # Return the final response
            if is_error:
                shared_state["outputs"]["code"] = f"// ERROR: {clean_response[:1000]}"
            else:
                shared_state["outputs"]["code"] = "Code successfully implemented."
            shared_state["outputs"]["agent_report"] = clean_response[:5000] if clean_response else "Code implementation completed."

            # ── Update task.json: mark current step completed/failed, advance ──
            try:
                from sync_helpers import load_task_tracking, save_task_tracking
                from datetime import datetime
                task = load_task_tracking(project_path, chat_id)
                if task and task.get("steps"):
                    steps_data = task["steps"]
                    current_idx = task.get("current_step", 0)
                    if current_idx < len(steps_data):
                        steps_data[current_idx]["tool_calls"] = step_tool_calls
                        if clean_response:
                            steps_data[current_idx]["notes"] = clean_response[:200]
                            
                        if is_error:
                            steps_data[current_idx]["status"] = "failed"
                        else:
                            steps_data[current_idx]["status"] = "completed"
                            steps_data[current_idx]["completed_at"] = datetime.now().isoformat()
                            # Step-level context isolation: clear developer_state on step completion
                            if "developer_state" in task:
                                del task["developer_state"]
                            
                        # Save artifacts
                        artifacts = task.setdefault("artifacts", {})
                        if tracked_files_created:
                            existing = set(artifacts.get("files_created", []))
                            existing.update(tracked_files_created)
                            artifacts["files_created"] = list(existing)
                        if tracked_files_modified:
                            existing = set(artifacts.get("files_modified", []))
                            existing.update(tracked_files_modified)
                            artifacts["files_modified"] = list(existing)
                        
                        if not is_error:
                            next_step = current_idx + 1
                            if next_step < len(steps_data):
                                task["current_step"] = next_step
                                steps_data[next_step]["status"] = "in_progress"
                            else:
                                task["status"] = "completed"
                        save_task_tracking(task, project_path, chat_id)
            except Exception as e:
                print(f"[DEVELOPER] Error updating task tracking: {e}")
            # ── END ──

            # ── Pillar 63/75/96: Local code quality check on all tracked files ──
            lint_summary_parts: list[str] = []
            if not is_error:
                all_tracked = list(set(tracked_files_created + tracked_files_modified))
                py_files = [f for f in all_tracked if f.endswith(".py") and os.path.isfile(f)]
                if py_files:
                    try:
                        from dev_lint import lint_and_fix
                        for py_file in py_files:
                            try:
                                with open(py_file, "r", encoding="utf-8") as lf:
                                    original = lf.read()
                                lint_result = lint_and_fix(original, py_file)
                                total_fixes = len(lint_result["fast_fixes"]) + len(lint_result["lint_fixes"])
                                if total_fixes > 0:
                                    with open(py_file, "w", encoding="utf-8") as lf:
                                        lf.write(lint_result["code"])
                                    _log(f"[DEVELOPER] 🔧 dev_lint fixed {total_fixes} issue(s) in {os.path.basename(py_file)}: "
                                         f"{'; '.join(lint_result['fast_fixes'] + lint_result['lint_fixes'])}")
                                    lint_summary_parts.append(f"{py_file}: {total_fixes} fix(es)")
                                elif not lint_result["original_valid"] and lint_result["final_valid"]:
                                    _log(f"[DEVELOPER] ✅ dev_lint resolved syntax error in {os.path.basename(py_file)}")
                                    with open(py_file, "w", encoding="utf-8") as lf:
                                        lf.write(lint_result["code"])
                                    lint_summary_parts.append(f"{py_file}: syntax fixed")
                            except Exception as le:
                                _log(f"[DEVELOPER] ⚠️ dev_lint skipped {os.path.basename(py_file)}: {le}")
                        if lint_summary_parts:
                            _log(f"[DEVELOPER] 🎯 Local lint saved LLM correction turns on {len(lint_summary_parts)} file(s)")
                    except ImportError:
                        _log("[DEVELOPER] dev_lint module not available, skipping local code quality checks")

            if is_error:
                return make_return({
                    "code": f"// ERROR: {clean_response[:1000]}",
                    "agent_report": clean_response[:5000] if clean_response else "Failed.",
                    "test_report": f"STATUS: FAIL\nDeveloper reported error: {clean_response[:300]}",
                    "project_path": project_path,
                    "code_updated": True,
                    "tech_spec_updated": False,
                })
            else:
                agent_report_text = clean_response[:5000] if clean_response else "Completed."
                if lint_summary_parts:
                    agent_report_text += "\n\n🔧 Local lint fixes:\n" + "\n".join(f"- {s}" for s in lint_summary_parts)
                return make_return({
                    "code": "Code successfully implemented.",
                    "agent_report": agent_report_text,
                    "test_report": "",
                    "project_path": project_path,
                    "code_updated": True,
                    "tech_spec_updated": False,
                })

    # Max iterations reached
    _log(f"[DEVELOPER] ⚠️ Max iterations ({max_iters}) reached")
    shared_state["thoughts"]["developer"] = f"Reached maximum iterations ({max_iters})."

    # ── Goal Toggle Auto-Continue System ──
    if _is_auto_continue_enabled():
        _log("[DEVELOPER] 🚀 Auto-Continue enabled. Triggering automatic wake-up and suspending graph...")
        import threading
        import time
        import requests

        def _wakeup_trigger():
            # Wait 1 second and call /api/run to resume
            time.sleep(1)
            try:
                url = "http://127.0.0.1:8000/api/run"
                payload = {
                    "prompt": "continue",
                    "workspace_path": project_path,
                    "chat_id": chat_id
                }
                requests.post(url, json=payload, timeout=5)
                print("[WAKEUP] Auto-Continue wake-up request sent.")
            except Exception as ex:
                print(f"[WAKEUP] Auto-Continue wakeup error: {ex}")

        threading.Thread(target=_wakeup_trigger, daemon=True).start()

        # Save developer state to task.json
        try:
            from sync_helpers import load_task_tracking, save_task_tracking
            task_data = load_task_tracking(project_path, chat_id)
            if task_data:
                serialized_msgs = []
                for m in messages:
                    serialized_msgs.append({"type": type(m).__name__, "content": m.content})
                
                # Make sure status is set to in_progress so the Supervisor Bypass triggers on wakeup
                task_data["status"] = "in_progress"
                task_data["developer_state"] = {
                    "messages": serialized_msgs,
                    "iteration": iteration,
                    "tool_call_log": tool_call_log,
                    "step_tool_calls": step_tool_calls,
                    "tracked_files_created": tracked_files_created,
                    "tracked_files_modified": tracked_files_modified,
                    "last_response_text": last_response_text,
                }
                save_task_tracking(task_data, project_path, chat_id)
        except Exception as e:
            print(f"[DEVELOPER] Error saving state: {e}")

        # Return suspended response
        return make_return({
            "code": f"// SUSPENDED: Iteration cap {max_iters} reached. Auto-continuing...",
            "agent_report": f"SUSPENDED: Iteration limit {max_iters} reached. Auto-continuing task execution...",
            "test_report": "",
            "project_path": project_path,
            "code_updated": False,
            "tech_spec_updated": False,
            "next_agent": "suspended",
        })
    
    summary = last_response_text[:5000] if last_response_text else f"Developer ran {iteration} tool calls."
    if "```tool" in summary or '{"tool":' in summary:
        tool_idx = summary.find("```tool")
        if tool_idx == -1:
            tool_idx = summary.find('{"tool":')
        text_before = summary[:tool_idx].strip()
        text_before = re.sub(r'<thinking>.*?</thinking>', '', text_before, flags=re.DOTALL).strip()
        if len(text_before) > 50:
            summary = text_before
        else:
            summary = "Reached maximum iterations during execution."
            
    summary = (
        f"ATTENTION: I have reached my safety iteration limit of {max_iters} turns, but I am not finished yet. "
        f"I have successfully completed {iteration} turns. If you would like me to resume and continue "
        f"this work for another {max_iters} turns, please type 'continue' or 'go on'.\n\n"
        f"Here is what I accomplished so far:\n{summary}"
    )
    try:
        shared_state["developer_tool_log"] = json.dumps(tool_call_log, indent=2)
    except Exception:
        shared_state["developer_tool_log"] = str(tool_call_log)

    # ── Save partial task progress ──
    try:
        from sync_helpers import load_task_tracking, save_task_tracking
        task = load_task_tracking(project_path, chat_id)
        if task and task.get("steps"):
            steps_data = task["steps"]
            current_idx = task.get("current_step", 0)
            if current_idx < len(steps_data):
                steps_data[current_idx]["tool_calls"] = step_tool_calls
                steps_data[current_idx]["notes"] = f"Reached max iterations ({max_iters}) — will continue"
                # Save artifacts even on partial progress
                artifacts = task.setdefault("artifacts", {})
                if tracked_files_created:
                    existing = set(artifacts.get("files_created", []))
                    existing.update(tracked_files_created)
                    artifacts["files_created"] = list(existing)
                if tracked_files_modified:
                    existing = set(artifacts.get("files_modified", []))
                    existing.update(tracked_files_modified)
                    artifacts["files_modified"] = list(existing)
            save_task_tracking(task, project_path, chat_id)
    except Exception as e:
        print(f"[DEVELOPER] Error saving partial task progress: {e}")
    # ── END ──

    shared_state["outputs"]["code"] = summary
    shared_state["outputs"]["agent_report"] = "Code implementation reached max iterations."

    return make_return({
        "code": summary,
        "agent_report": summary,
        "test_report": "",
        "project_path": project_path,
        "code_updated": True,
        "tech_spec_updated": False,
    })
