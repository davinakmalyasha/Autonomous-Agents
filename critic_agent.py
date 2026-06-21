"""
Stage 3: LLM Critic — Reflexion Pattern.

Structured error diagnosis using deepseek-v4-pro with max thinking.
The Critic is a SEPARATE agent with a DIFFERENT model family from the generator.

RULES (from production Reflexion pattern):
  1. DIFFERENT MODEL: Generator = v4-flash, Critic = v4-pro (max thinking).
  2. STRUCTURED OUTPUT: Pydantic-enforced JSON schema — no free-text diagnosis.
  3. ACTIONABLE: Every finding includes exact file, line, severity, and fix code.
  4. FRESH CONTEXT: Critic reads the failing files directly — no shared bias.
  5. STATELESS: One call, one result. No conversation loop. No tool access needed.

The Critic does NOT fix code. It produces a diagnosis that the developer agent
uses to apply targeted, structured fixes.
"""

import os
import json
from typing import Optional, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic output schema — enforced via structured output / json_object mode
# ═══════════════════════════════════════════════════════════════════════════════

class CriticIssue(BaseModel):
    """A single diagnosed issue with exact file location and fix suggestion."""
    file: str = Field(description="Relative file path with the issue")
    line: int = Field(description="Line number (0 if not line-specific)")
    severity: Literal["critical", "high", "medium", "low"] = Field(
        description="Issue severity: critical=blocks all functionality, "
                    "high=breaks expected behavior, medium=code quality, "
                    "low=style/minor"
    )
    category: str = Field(
        description="Category: syntax, logic_error, missing_import, wrong_type, "
                    "missing_feature, test_failure, error_handling, security, "
                    "performance, style, dependency"
    )
    issue: str = Field(
        description="Clear, specific description of the problem. "
                    "Include the observed behavior and expected behavior."
    )
    fix: str = Field(
        description="Exact, actionable fix instruction. Be specific — include "
                    "function names, variable names, the exact code change needed."
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0, le=1.0,
        description="Confidence in this diagnosis (0.0-1.0). "
                    "0.95+ = certain, 0.7-0.95 = likely, <0.7 = speculative"
    )


class CriticDiagnosis(BaseModel):
    """Complete structured diagnosis from the Critic."""
    status: Literal["FIX_REQUIRED", "MINOR_ISSUES", "READY"] = Field(
        description="FIX_REQUIRED = blocker issues must be resolved. "
                    "MINOR_ISSUES = ship with caveats. "
                    "READY = all clear."
    )
    summary: str = Field(
        description="1-3 sentence summary of the diagnosis: what went wrong, "
                    "root cause, and overall assessment."
    )
    issues: list[CriticIssue] = Field(
        default_factory=list,
        description="List of diagnosed issues, ordered by severity then confidence."
    )
    root_cause: str = Field(
        default="",
        description="If multiple issues share a common root cause, describe it here. "
                    "Examples: 'missing import at top of file', "
                    "'incorrect assumption about API response shape', "
                    "'forgot to install dependency'"
    )
    files_to_read: list[str] = Field(
        default_factory=list,
        description="Files the developer should read before applying fixes, "
                    "if different from the issue files."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Critic System Prompt
# ═══════════════════════════════════════════════════════════════════════════════

CRITIC_SYSTEM_PROMPT = """You are a **Senior Code Critic** — an expert debugger specializing in diagnosing test failures and code issues produced by AI code generators.

## Your Role
You receive code that was just written by a developer agent along with test failures and deterministic check results. Your job is to produce a **structured, actionable diagnosis** that the developer agent can use to apply exact fixes.

## How You Work

1. **Read the failure signals first**: test output, tracebacks, lint findings, Stage 2 cascade results. These are the ground truth — your diagnosis starts here.

2. **Then read the code**: Focus on the specific files and lines implicated by the failures. Don't review the entire codebase — target your analysis to the failure signals.

3. **Identify the ROOT CAUSE**, not just symptoms. If 5 tests fail because of one missing import, report ONE issue with the import as root cause, not 5 separate issues.

4. **Rate your confidence honestly**:
   - 0.95+ = You can point to the exact line and the exact fix is unambiguous
   - 0.70-0.95 = You're confident about the area but the fix might need adjustment
   - <0.70 = You have a hypothesis worth checking but the developer should verify

## Diagnosis Rules

### CRITICAL severity (blocks all functionality)
- Syntax errors that prevent import/execution
- Missing files that were supposed to be created
- Missing required imports (the code literally cannot run)
- Wrong function signatures that cause immediate crashes

### HIGH severity (breaks expected behavior)
- Logic errors that cause test failures
- Incorrect API usage (wrong method, wrong parameters)
- Missing features (code doesn't implement what was asked)
- Type mismatches that cause runtime errors

### MEDIUM severity (code quality, edge cases)
- Missing error handling for known failure modes
- Stub/placeholder implementations
- Unresolved TODOs or FIXMEs
- Missing edge case coverage
- Bare except clauses

### LOW severity (style, minor improvements)
- Naming conventions
- Minor refactoring opportunities
- Documentation gaps

## Output Format
You MUST output valid JSON matching the diagnosis schema. Every issue must include:
- Exact file path (relative to project root)
- Line number (0 if not line-specific)
- Severity
- Category
- Specific, actionable description
- Exact fix instruction

## KEY PRINCIPLE
A developer agent should be able to read your diagnosis and apply every fix in order WITHOUT needing to re-read the files or re-analyze the error. Your diagnosis IS the complete fix plan."""


# ═══════════════════════════════════════════════════════════════════════════════
# Diagnosis builder (prompt construction)
# ═══════════════════════════════════════════════════════════════════════════════

def build_critic_prompt(
    project_path: str,
    tracked_files: list[str],
    test_output: str,
    stage2_summary: str = "",
    stage2_findings: str = "",
) -> str:
    """
    Build the critic's prompt: code context + failure signals + Stage 2 findings.

    The prompt is structured so the critic reads failure signals first (ground truth),
    then relevant code (evidence), then produces diagnosis.
    """
    parts = []

    parts.append("## TASK\nDiagnose the test failure(s) and code issues. "
                  "Produce a structured JSON diagnosis with exact file:line fixes.")

    # ── Section 1: Failure Signals (ground truth) ──
    parts.append("\n## FAILURE SIGNALS (GROUND TRUTH)\n")

    if test_output:
        # Truncate extremely long test output
        cleaned = test_output[:4000]
        if len(test_output) > 4000:
            cleaned += f"\n... (truncated, {len(test_output)} total chars)"
        parts.append(f"### Test Output\n```\n{cleaned}\n```")

    if stage2_summary:
        parts.append(f"\n### Deterministic Check Summary\n{stage2_summary}")

    if stage2_findings:
        parts.append(f"\n### Deterministic Check Findings\n{stage2_findings}")

    # ── Section 2: Relevant Code (read the files) ──
    parts.append("\n## RELEVANT CODE (FILES WRITTEN OR MODIFIED)\n")

    for fpath in tracked_files:
        if not os.path.isfile(fpath):
            parts.append(f"\n### {fpath}\n[MISSING — file not created]")
            continue

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()
            # Truncate per file — critic needs key context, not the full 8000 lines
            if len(code) > 3000:
                code = code[:1500] + "\n\n... (truncated middle) ...\n\n" + code[-1500:]
            ext = os.path.splitext(fpath)[1]
            parts.append(f"\n### {fpath}\n```{ext.lstrip('.') or 'text'}\n{code}\n```")
        except Exception as e:
            parts.append(f"\n### {fpath}\n[ERROR reading file: {e}]")

    # ── Section 3: Reminder ──
    parts.append(
        "\n## INSTRUCTIONS\n"
        "1. Start with the failure signals — what exactly is failing?\n"
        "2. Cross-reference with the code — which file(s) and line(s) are responsible?\n"
        "3. Identify the ROOT CAUSE — one root cause can explain many test failures.\n"
        "4. Produce your JSON diagnosis. Every issue must be specific and actionable.\n"
        "5. Be honest about confidence. If you're not sure, say so and suggest verification."
    )

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# Invoke the Critic
# ═══════════════════════════════════════════════════════════════════════════════

def invoke_critic(
    project_path: str,
    tracked_files: list[str],
    test_output: str,
    stage2_summary: str = "",
    stage2_findings: str = "",
) -> CriticDiagnosis:
    """
    Invoke Stage 3 LLM Critic using deepseek-v4-pro with max thinking.

    This is a SEPARATE LLM call — isolated context, different model family,
    no conversation history contamination from the developer loop.

    Returns a validated CriticDiagnosis Pydantic model.
    """
    from llm import _get_deepseek_client, trim_prompt
    from llm_stats import TokenUsageTracker, update_token_stats
    from langchain_core.messages import SystemMessage, HumanMessage

    prompt = build_critic_prompt(
        project_path, tracked_files, test_output, stage2_summary, stage2_findings
    )

    sys_msg = trim_prompt(CRITIC_SYSTEM_PROMPT) + (
        f"\n\nCRITICAL: You MUST respond with a single JSON object matching "
        f"this schema:\n{CriticDiagnosis.model_json_schema()}\n"
        "No markdown, no explanation outside the JSON, just the raw JSON object."
    )

    user_msg = trim_prompt(prompt)

    # Use v4-pro with max thinking — different model family from generator (v4-flash)
    llm = _get_deepseek_client(
        model="deepseek-v4-pro",
        temp=0.1,  # Low temp for structured analysis
        role="Critic",
        response_format={"type": "json_object"},
        reasoning_effort="max",
    )

    tracker = TokenUsageTracker()
    messages = [
        SystemMessage(content=sys_msg),
        HumanMessage(content=user_msg),
    ]

    res = llm.invoke(messages, config={"callbacks": [tracker]})

    # Extract text
    raw_text = ""
    if hasattr(res, "content"):
        from llm import _extract_text
        raw_text = _extract_text(res.content)

    # Parse JSON → Pydantic
    import re as _re
    json_match = _re.search(r'\{.*\}', raw_text, _re.DOTALL)
    if json_match:
        raw_text = json_match.group(0)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        # Fallback: return a synthesized diagnosis
        return CriticDiagnosis(
            status="FIX_REQUIRED",
            summary=f"Critic JSON parsing failed: {e}. Raw response was: {raw_text[:500]}",
            issues=[CriticIssue(
                file="unknown",
                line=0,
                severity="high",
                category="syntax",
                issue=f"Critic output was not valid JSON: {e}",
                fix="Manual review required — the Critic produced invalid output.",
                confidence=0.5,
            )],
            root_cause="Critic model produced invalid JSON output.",
        )

    # Track token usage
    reasoning = res.additional_kwargs.get("reasoning_content") if hasattr(res, "additional_kwargs") else None
    where_tag = f"Critic: diagnose {len(tracked_files)} files"
    update_token_stats(
        "Critic", "deepseek-v4-pro",
        tracker.input_tokens, tracker.output_tokens,
        tracker.cache_hit_tokens, where_tag,
    )

    # Log reasoning if available
    if reasoning:
        try:
            from state_sync import shared_state
            if shared_state and "live_terminal_log" in shared_state:
                shared_state["live_terminal_log"] += f"\n[CRITIC THOUGHTS] >> {reasoning[:600]}\n"
        except Exception:
            pass

    try:
        return CriticDiagnosis.model_validate(data)
    except Exception:
        return CriticDiagnosis(
            status="FIX_REQUIRED",
            summary=f"Critic output did not match schema. Raw: {raw_text[:300]}",
            issues=[CriticIssue(
                file="unknown",
                line=0,
                severity="high",
                category="syntax",
                issue="Critic produced valid JSON but wrong structure.",
                fix="Check the raw diagnosis: " + raw_text[:300],
                confidence=0.4,
            )],
            root_cause="Critic model output structure mismatch.",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Format diagnosis for developer agent (human-readable)
# ═══════════════════════════════════════════════════════════════════════════════

def format_diagnosis_for_developer(diagnosis: CriticDiagnosis) -> str:
    """Convert a CriticDiagnosis into a message the developer agent can execute."""
    lines = [
        "[STAGE 3 — LLM CRITIC DIAGNOSIS]",
        "",
        f"Status: {diagnosis.status}",
        f"Summary: {diagnosis.summary}",
    ]

    if diagnosis.root_cause:
        lines.append(f"Root Cause: {diagnosis.root_cause}")

    if diagnosis.files_to_read:
        lines.append(f"Files to read before fixing: {', '.join(diagnosis.files_to_read)}")

    lines.append("")
    lines.append("## Issues to Fix (apply in order):")

    for i, issue in enumerate(diagnosis.issues, start=1):
        lines.append(f"\n### Issue {i}: [{issue.severity.upper()}] {issue.file}:{issue.line or '?'}")
        lines.append(f"**Category**: {issue.category} | **Confidence**: {issue.confidence:.0%}")
        lines.append(f"**Problem**: {issue.issue}")
        lines.append(f"**Fix**: {issue.fix}")

    if diagnosis.status == "FIX_REQUIRED":
        lines.append(
            "\n\n## ACTION REQUIRED\n"
            "Apply the fixes above IN ORDER. Start with critical issues (these "
            "unblock everything else), then high, then medium. After applying all "
            "critical and high fixes, re-run the tests immediately. Do NOT guess — "
            "each fix instruction is specific and verified."
        )
    elif diagnosis.status == "MINOR_ISSUES":
        lines.append(
            "\n\n## ACTION (Optional)\n"
            "Issues are minor. Apply if you have remaining turns, otherwise ship."
        )

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Static System Template — frozen for DeepSeek KV cache hits (98% discount)
# ═══════════════════════════════════════════════════════════════════════════════

_CRITIC_SYSTEM_TEMPLATE = """\
You are a Senior Code Critic. You diagnose test failures and code issues with structured, actionable output.

## YOUR ROLE
You receive code that was just written along with test failures. Your job is to produce a structured diagnosis with exact file paths, line numbers, severity levels, and fix instructions.

## HOW YOU WORK

1. Read the failure signals first: test output, tracebacks, lint findings. These are ground truth.
2. Then read the code — focus on the specific files and lines implicated by the failures.
3. Identify the ROOT CAUSE, not just symptoms. If 5 tests fail because of one missing import, report ONE issue.
4. Rate your confidence honestly:
   - 0.95+ = You can point to the exact line and the fix is unambiguous.
   - 0.70-0.95 = Confident about the area but fix might need adjustment.
   - <0.70 = A hypothesis worth checking — tell the developer to verify.

## SEVERITY LEVELS

- **CRITICAL**: Syntax errors, missing files, missing required imports — code cannot run.
- **HIGH**: Logic errors, incorrect API usage, missing features — breaks expected behavior.
- **MEDIUM**: Missing error handling, stubs, unresolved TODOs, edge cases.
- **LOW**: Naming conventions, minor refactoring, documentation gaps.

## TOOLS
- read_file(file_path, offset?, limit?) — Read code files.
- search_code(pattern, path?, glob?) — Search for patterns.
- list_files(path?, pattern?) — Explore project structure.

## TOOL FORMAT
```tool
{"tool": "tool_name", "args": {"param": "value"}}
```

## OUTPUT FORMAT
You MUST output a structured diagnosis. Every issue includes:
- `file`: Exact relative file path
- `line`: Line number (0 if not line-specific)
- `severity`: critical | high | medium | low
- `category`: syntax | logic_error | missing_import | wrong_type | missing_feature | test_failure | error_handling | security | performance | style | dependency
- `issue`: Clear, specific description of the problem
- `fix`: Exact, actionable fix instruction
- `confidence`: 0.0-1.0

## RULES
- Start from failure signals. They are ground truth.
- One root cause can explain many test failures — don't duplicate.
- Every finding must be specific and actionable. A developer should be able to apply every fix in order without re-reading the files.
- Be honest about confidence. If uncertain, flag it.
- Never modify code. You diagnose, not fix.

## OUTPUT
Return your structured diagnosis. If the code is clean, say so explicitly.
"""
