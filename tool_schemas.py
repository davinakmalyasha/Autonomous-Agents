"""
Native Function Calling Tool Schemas — DeepSeek API compatible.

Each tool is a JSON Schema function definition passed via the `tools` API
parameter. The model returns structured tool_calls — no text parsing needed.

Schema style: verbose descriptions with usage patterns, parameter constraints,
and examples. Optimized for model compliance even on flash variants.
"""


def get_native_tools() -> list[dict]:
    """Return all tools as DeepSeek-native function definitions."""
    return [
        # ── File Reading ──
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": (
                    "Read a file from disk. Returns the file content with line numbers "
                    "in the format: [FILE] path (lines 1-50 of 350). "
                    "Use this to inspect existing code before editing it. "
                    "For files larger than 300 lines, ALWAYS use the offset and limit "
                    "parameters to read only the section you need — never read an entire "
                    "large file at once. "
                    "If you need to find a specific function or class, use search_code "
                    "first to locate the line number, then use read_file with offset to "
                    "read just that section. "
                    "IMPORTANT: Do not re-read the same file section more than twice. "
                    "Re-reading wastes time and tokens. Trust the first read."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute or relative path to the file. Use forward slashes (e.g. 'src/app.py').",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Line number to start reading from (1-based). Default: 1. Use this to skip to the relevant section of large files.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of lines to read. Default: 2000 for small files, auto-capped at 300 for files over 400 lines. For large files, set limit to 50-100 to read manageable chunks.",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        # ── File Writing ──
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": (
                    "Create a new file or completely overwrite an existing file. "
                    "This is the PRIMARY tool for creating new files. Directories are "
                    "created automatically if they do not exist. "
                    "Use this tool for: creating any new file, replacing an existing "
                    "file entirely, or making changes that span more than 5 lines of a "
                    "file (rewrite the whole file instead of using edit_file for large "
                    "diffs). "
                    "TRUST: Once write_file returns success, the file EXISTS on disk "
                    "with exactly the content you provided. You do NOT need to read_file "
                    "to verify. Move immediately to the next step. "
                    "Use forward slashes in file_path on all platforms."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path where the file should be written. Use forward slashes. Directories are created if they don't exist.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The complete file contents as a single string. Include all code, imports, and documentation. Do not use placeholders, TODO comments, or stubs.",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
        },
        # ── File Editing ──
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": (
                    "Edit a file using single-block exact search/replace OR multi-block SEARCH/REPLACE diff blocks. "
                    "BEST FOR: targeted edits. For extremely large or complete file rewrites, use write_file instead. "
                    "You must provide EITHER (old_string + new_string) for a single replacement, OR (diff) containing Aider-style "
                    "SEARCH/REPLACE blocks for single or multiple non-contiguous changes. "
                    "Aider-style SEARCH/REPLACE block format:\n"
                    "<<<<<<< SEARCH\n"
                    "<exact text to replace>\n"
                    "=======\n"
                    "<new text to insert>\n"
                    ">>>>>>> REPLACE\n\n"
                    "CRITICAL: All search targets must match the file content EXACTLY — copy the target lines character-for-character."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to edit. Must be an existing file.",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "The exact text to find and replace. Copy this directly from read_file output.",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "The replacement text to insert.",
                        },
                        "diff": {
                            "type": "string",
                            "description": "SEARCH/REPLACE blocks or unified diff to apply to the file. Allows editing multiple separate parts of a file in one turn.",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        # ── Shell Execution ──
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": (
                    "Execute a shell command and return stdout, stderr, and exit code. "
                    "Use for: running tests (pytest, npm test, go test), installing "
                    "packages (pip install), git operations (add, commit, status), "
                    "starting development servers, and running scripts. "
                    "The command runs in a bash shell. Use && to chain commands. "
                    "VENV: The virtual environment is auto-prepended to PATH. Do not "
                    "activate it manually. "
                    "FAILURE PROTOCOL: If a command fails (non-zero exit code), read "
                    "the error message carefully. Try at most ONE alternative (e.g. "
                    "'python3' instead of 'python', or 'pip3' instead of 'pip'). "
                    "If the alternative also fails, build the code anyway and note the "
                    "limitation. NEVER cycle through 3+ variations of the same command. "
                    "NEVER use 'cmd /c', 'powershell -Command', or 'echo' as "
                    "workarounds — the shell is bash, not Windows CMD. "
                    "TRUST: If exit code is 0, the command succeeded. If test output "
                    "contains 'passed' or 'OK', the tests passed. Do not re-run to "
                    "double-check. "
                    "For long-running servers, set background=true to run the process "
                    "in the background without blocking."
                ),                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute. Can use && for chaining, | for piping, > for redirection. Example: 'python -m pytest test_file.py -x -q'",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Maximum execution time in milliseconds. Default: 30000 (30 seconds). Increase for long-running operations like package installation.",
                        },
                        "background": {
                            "type": "boolean",
                            "description": "If true, run the command in the background and return immediately. Use for servers and long-running processes.",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        # ── Code Search ──
        {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": (
                    "Search files using regex pattern matching. Returns matching file "
                    "paths with line numbers and content snippets. "
                    "Use for: finding where a function or class is defined, locating "
                    "error messages in code, finding specific patterns (e.g., 'import os', "
                    "'def test_', 'class.*Repository'). "
                    "IMPORTANT: Be specific with patterns. Searching for generic terms "
                    "like 'error', 'function', or 'def' will return hundreds of irrelevant "
                    "matches. Search for the exact function name, class name, or a "
                    "distinctive string from an error message. "
                    "Never search the same pattern twice. If results are not useful, "
                    "either narrow the pattern (add more context like 'def test_user') "
                    "or broaden it (remove anchors like '^')."
                ),                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for. Be specific and distinctive. Examples: 'def authenticate', 'import jwt', 'class UserRepository', 'darkModeToggle'.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory or file path to search within. Default: the project working directory.",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
        # ── Directory Listing ──
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": (
                    "List files and directories in a given path. "
                    "USE THIS ON YOUR FIRST RESPONSE TO EVERY TASK to understand the "
                    "workspace structure. "
                    "Call once per task. The directory listing does not change during "
                    "your execution — do not re-list the same directory."
                ),                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path to list. Default: the project working directory.",
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "If true, recursively list all subdirectories. Default: false.",
                        },
                    },
                    "required": [],
                },
            },
        },
        # ── Semantic Search ──
        {
            "type": "function",
            "function": {
                "name": "search_codebase",
                "description": (
                    "Semantic code search by natural language meaning or intent. "
                    "Use when regex search_code fails or when you need to find code "
                    "related to a concept rather than an exact pattern. "
                    "Example queries: 'authentication middleware', 'database connection "
                    "pool', 'error handling for file uploads', 'payment processing logic'. "
                    "Call once per query. Not a substitute for reading files — use the "
                    "results to identify which files to read_file next."
                ),                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language description of the code you are looking for. Be specific about the concept, feature, or behavior.",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return. Default: 10. Increase to 20 for broader searches.",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        # ── Python Signature Extraction ──
        {
            "type": "function",
            "function": {
                "name": "view_signatures",
                "description": (
                    "Extract function, class, and method signatures with docstrings "
                    "from a Python file. Returns a structured outline of the file's API "
                    "surface without reading the full file. "
                    "Use this to quickly understand a Python file's structure before "
                    "deciding which specific functions to read in detail. "
                    "Call once per file. After reviewing signatures, use read_file with "
                    "offset to read only the functions you need."
                ),                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to a Python file (.py).",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        # ── Planning File ──
        {
            "type": "function",
            "function": {
                "name": "write_planning_file",
                "description": (
                    "Write a structured planning document (planning.md) for complex "
                    "multi-step tasks that benefit from upfront design. "
                    "Write the plan ONCE, then immediately start executing it. Do not "
                    "iterate on the plan — use the implementation results to guide you."
                ),                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path for the planning file. Typically 'planning.md' in the project root.",
                        },
                        "goal": {
                            "type": "string",
                            "description": "One-sentence description of what the plan aims to accomplish.",
                        },
                        "analysis": {
                            "type": "string",
                            "description": "Summary of codebase analysis findings relevant to the plan.",
                        },
                        "proposed_changes": {
                            "type": "string",
                            "description": "List of all planned file changes, additions, and deletions.",
                        },
                        "steps": {
                            "type": "string",
                            "description": "Ordered step-by-step implementation checklist with verification criteria for each step.",
                        },
                    },
                    "required": ["file_path", "goal", "analysis", "proposed_changes", "steps"],
                },
            },
        },
        # ── Memory / History Tools ──
        {
            "type": "function",
            "function": {
                "name": "search_past_conversations",
                "description": (
                    "Search past conversation history and checkpoints for how similar "
                    "tasks, errors, or patterns were resolved previously. "
                    "Use when you encounter an error that might have been solved before."
                ),                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language description of what you are searching for in past conversations.",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "compact_conversation",
                "description": (
                    "Manually request compaction of the conversation history to free "
                    "context tokens. Use when the context window is running low and "
                    "auto-compaction has not triggered yet. "
                    "After compaction, earlier conversation turns are summarized and "
                    "removed, freeing space for new tool outputs."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_conversation_history",
                "description": (
                    "Read an archived compacted conversation log from the "
                    "/conversation_history/ directory. Use to recover context from "
                    "previous sessions or after aggressive compaction."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the archived conversation log file.",
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
    ]
