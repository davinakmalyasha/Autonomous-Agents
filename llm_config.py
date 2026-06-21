"""
LLM Configuration — DeepSeek-only setup.
Orchestrator → deepseek-v4-pro (must follow ```tool format precisely).
Subagents → deepseek-v4-flash (fast, XML/DSML output parsed by multi-format parser).
Standard/Lightweight → deepseek-v4-flash.
"""


TASK_CATEGORIES = {
    "orchestrator": [
        {"provider": "deepseek", "model": "deepseek-v4-flash"},
        {"provider": "deepseek", "model": "deepseek-v4-pro"},
    ],
    "complex": [
        {"provider": "deepseek", "model": "deepseek-v4-flash"},
        {"provider": "deepseek", "model": "deepseek-v4-pro"},
    ],
    "fixing": [
        {"provider": "deepseek", "model": "deepseek-v4-pro"},
        {"provider": "deepseek", "model": "deepseek-v4-flash"},
    ],
    "critic": [
        {"provider": "deepseek", "model": "deepseek-v4-pro"},
        {"provider": "deepseek", "model": "deepseek-v4-flash"},
    ],
    "standard": [
        {"provider": "deepseek", "model": "deepseek-v4-flash"},
        {"provider": "deepseek", "model": "deepseek-v4-pro"},
    ],
    "lightweight": [
        {"provider": "deepseek", "model": "deepseek-v4-flash"},
    ],
}


def get_task_category(task_name: str) -> str:
    """Classifies a task or agent role into lightweight, standard, complex, or orchestrator."""
    name_lower = task_name.lower()
    # Orchestrator roles get pro-first (must follow ```tool format exactly)
    if any(k in name_lower for k in ["developer", "orchestrator"]):
        return "orchestrator"
    if "critic" in name_lower:
        return "critic"
    if "fixing" in name_lower:
        return "fixing"
    elif (
        name_lower in ["sa", "dev", "coder"]
        or name_lower.startswith("sa-")
        or name_lower.startswith("dev-")
        or any(k in name_lower for k in [
            "coder", "architect", "complex",
            "diagnostics", "review", "planner",
        ])
    ):
        return "complex"
    elif (
        name_lower in ["route", "router", "chat", "compact", "archivist"]
        or any(k in name_lower for k in ["summary", "summarize", "compact", "lite"])
    ):
        return "lightweight"
    return "standard"
