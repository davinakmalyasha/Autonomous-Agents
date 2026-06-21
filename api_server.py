"""
FastAPI server — Bridges the React frontend with the LangGraph multi-agent pipeline.
Replaces the Gradio dashboard with SSE streaming endpoints.
"""
import os
import asyncio
import json
import threading
import time
import queue
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from sync_manager import run_and_sync_graph
from state_sync import shared_state, safe_get_state, safe_update_state, safe_serialize_state, state_lock
import workspace_manager as wm

load_dotenv()

# Init default workspace on startup
wm.init_default_workspace()

app = FastAPI(title="Deep Agents API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    prompt: str
    model: str = "Automatic Fallback"
    temperature: float = 0.7
    workspace_path: str = ""
    chat_id: str = ""

class ChatRequest(BaseModel):
    prompt: str


# ── SSE Helpers ─────────────────────────────────────────────────────────────

def _format_sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/state")
async def get_state():
    """Return the current shared state as JSON."""
    return JSONResponse(content=json.loads(safe_serialize_state()))


def _save_chat_token_usage(workspace_path: str, chat_id: str):
    if not chat_id or not workspace_path:
        return
    try:
        chat = wm.get_chat(workspace_path, chat_id, include_traces=False, include_usage=True)
        if chat:
            run_stats = safe_get_state().get("token_usage", {})
            chat_stats = chat.get("token_usage") or {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cache_hit_tokens": 0,
                "total_cache_miss_tokens": 0,
                "total_cost": 0.0,
                "calls": []
            }
            if "total_cache_hit_tokens" not in chat_stats:
                chat_stats["total_cache_hit_tokens"] = 0
            if "total_cache_miss_tokens" not in chat_stats:
                chat_stats["total_cache_miss_tokens"] = 0
            chat_stats["total_input_tokens"] += run_stats.get("total_input_tokens", 0)
            chat_stats["total_output_tokens"] += run_stats.get("total_output_tokens", 0)
            chat_stats["total_cache_hit_tokens"] += run_stats.get("total_cache_hit_tokens", 0)
            chat_stats["total_cache_miss_tokens"] += run_stats.get("total_cache_miss_tokens", 0)
            chat_stats["total_cost"] += run_stats.get("total_cost", 0.0)
            chat_stats["calls"] = chat_stats.get("calls", []) + run_stats.get("calls", [])
            chat["token_usage"] = chat_stats
            wm.save_chat(workspace_path, chat_id, chat)
    except Exception as e:
        print(f"Error saving token stats for chat {chat_id}: {e}")


# ── Simple chat keywords (costs nothing, no LLM call needed) ──
_CHAT_KEYWORDS = {"hello", "hi", "hey", "thanks", "thank you", "good morning",
                  "good afternoon", "how are you", "what's up", "bye", "goodbye"}

def _is_obvious_chat(text: str) -> bool:
    """Quick keyword check — true if it's clearly just a greeting/thanks, not a task."""
    t = text.lower().strip().rstrip(".!?").split()
    if len(t) > 6:
        return False  # too long to be just a greeting
    return any(kw in text.lower() for kw in _CHAT_KEYWORDS) and not any(
        kw in text.lower() for kw in ["build", "create", "make", "write", "code",
                                       "fix", "implement", "add", "change", "modify",
                                       "delete", "remove", "refactor", "deploy", "run", "test"])


@app.post("/api/run")
async def run_pipeline(req: RunRequest, request: Request):
    """Run the agentic pipeline with SSE streaming of state updates.
    No Jarvis Router — goes directly to the main agent."""
    from chat_memory_manager import add_chat_message, resolve_request_text

    # Clear previous failed models and reset current run token usage
    safe_update_state({
        "selected_model": req.model,
        "selected_temp": req.temperature,
        "failed_models": [],
        "token_usage": {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cache_hit_tokens": 0,
            "total_cache_miss_tokens": 0,
            "total_cost": 0.0,
            "calls": [],
        }
    })

    add_chat_message("user", req.prompt, workspace_path=req.workspace_path, chat_id=req.chat_id)
    resolved = resolve_request_text(req.prompt, workspace_path=req.workspace_path, chat_id=req.chat_id)

    # Quick chat check — no LLM call needed for greetings
    if _is_obvious_chat(req.prompt):
        _save_chat_token_usage(req.workspace_path, req.chat_id)
        safe_update_state({
            "active_node": "agent",
            "next_agent": "",
            "completed_nodes": [],
            "thoughts": {"agent": "Ready and waiting for instructions."},
            "client_request": resolved,
            "outputs": {
                "requirements": "", "tech_spec": "", "code": "",
                "test_report": "", "devops_config": "", "analytics_report": "",
                "gherkin": "", "mermaid": "",
            },
            "deep_agents_log": [],
            "live_terminal_log": f"👤 User: {req.prompt}\n\n🤖 Assistant: Hi! Ready to help. What do you need?\n",
        })

        async def chat_stream() -> AsyncGenerator[str, None]:
            if await request.is_disconnected():
                return
            yield _format_sse("state", json.loads(safe_serialize_state()))
            yield _format_sse("done", {"status": "complete"})

        return StreamingResponse(chat_stream(), media_type="text/event-stream")

    # Go directly to the main agent
    async def build_stream() -> AsyncGenerator[str, None]:
        """Stream state updates from the LangGraph pipeline via SSE.
        Yields graph-level events AND periodic intermediate snapshots during
        Developer tool-using loops so the frontend shows thoughts in real-time."""
        done = False
        had_error = False
        last_log_len = 0
        cancel_event = threading.Event()

        def run_in_thread():
            nonlocal done, had_error
            try:
                for state_snapshot in run_and_sync_graph(resolved, workspace_path=req.workspace_path, chat_id=req.chat_id, cancel_event=cancel_event):
                    q.put(state_snapshot)
                q.put(None)  # signal completion
            except Exception as e:
                had_error = True
                q.put({"error": str(e)})
                q.put(None)
            finally:
                done = True

        q: queue.Queue = queue.Queue()
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

        last_ver = 0
        while not done or not q.empty():
            if await request.is_disconnected():
                cancel_event.set()  # Signal the graph thread to stop
                break
            try:
                item = q.get(timeout=0.05)
                if item is None:
                    break
                if isinstance(item, dict):
                    yield _format_sse("state", item)
                    last_ver = item.get("state_version", 0)
            except queue.Empty:
                if not done:
                    snap = json.loads(safe_serialize_state())
                    cur_ver = snap.get("state_version", 0)
                    if cur_ver > last_ver:
                        last_ver = cur_ver
                        snap["_intermediate"] = True
                        yield _format_sse("state", snap)
                await asyncio.sleep(0.05)

        # Save token usage for the chat
        _save_chat_token_usage(req.workspace_path, req.chat_id)

        # Final state
        yield _format_sse("state", json.loads(safe_serialize_state()))
        yield _format_sse("done", {"status": "error" if had_error else "complete"})

    return StreamingResponse(build_stream(), media_type="text/event-stream")


@app.post("/api/session/reset")
async def reset_session():
    """Reset the shared state for a new session."""
    empty_outputs = {
        "requirements": "", "tech_spec": "", "code": "",
        "test_report": "", "devops_config": "", "analytics_report": "",
        "gherkin": "", "mermaid": "",
    }
    safe_update_state({
        "active_node": "",
        "next_agent": "",
        "completed_nodes": [],
        "thoughts": {
            "supervisor": "", "developer": "",
        },
        "client_request": "",
        "outputs": empty_outputs,
        "project_path": "",
        "agents_plan": "",
        "deep_agents_log": [],
        "live_terminal_log": "🧹 Session reset. Ready for a new request.\n",
        "token_usage": {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cache_hit_tokens": 0,
            "total_cache_miss_tokens": 0,
            "total_cost": 0.0,
            "calls": [],
        },
    })
    return JSONResponse(content={"status": "ok"})


@app.get("/api/history")
async def get_history():
    """Return recent prompt history."""
    try:
        from chat_memory_manager import load_chat_memory
        mem = load_chat_memory()
        messages = mem.get("current_day_messages", [])
        user_prompts = [m["text"] for m in messages if m.get("sender") == "user"]
        seen = set()
        user_prompts = [x for x in user_prompts if not (x in seen or seen.add(x))]
        return JSONResponse(content={"prompts": user_prompts[:10] if user_prompts else ["No recent prompts"]})
    except Exception:
        return JSONResponse(content={"prompts": ["No recent prompts"]})


@app.get("/api/models")
async def get_models():
    """Return available model list."""
    return JSONResponse(content={
        "models": [
            {"id": "Automatic Fallback", "name": "Automatic Fallback", "provider": "auto"},
            {"id": "deepseek/deepseek-v4-flash-20260423:free", "name": "DeepSeek V4 Flash (Free)", "provider": "openrouter"},
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "provider": "openrouter"},
            {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "provider": "openrouter"},
            {"id": "openrouter/owl-alpha", "name": "Owl Alpha (OpenRouter)", "provider": "openrouter"},
            {"id": "qwen/qwen3-coder-480b-a35b-07-25:free", "name": "Qwen Coder 480B (Free)", "provider": "openrouter"},
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "Nemotron Ultra 550B (Free)", "provider": "openrouter"},
            {"id": "google/gemma-4-31b-it:free", "name": "Gemma 4 31B (Free)", "provider": "openrouter"},
            {"id": "openai/gpt-oss-120b:free", "name": "GPT-OSS 120B (Free)", "provider": "openrouter"},
            {"id": "openai/gpt-oss-20b:free", "name": "GPT-OSS 20B (Free)", "provider": "openrouter"},
            {"id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "name": "Nemotron Nano 30B (Free)", "provider": "openrouter"},
            {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B (Groq)", "provider": "groq"},
            {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B (Groq)", "provider": "groq"},
            {"id": "gemini/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini"},
            {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "gemini"},
            {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "gemini"},
        ]
    })


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Deep Agents API v2.0"}


# ═══════════════════════════════════════════════════════════════════════════════
# Workspace & Chat API
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/workspaces")
async def get_workspaces():
    return JSONResponse(content={"workspaces": wm.list_workspaces()})


@app.post("/api/workspaces")
async def create_workspace(req: Request):
    body = await req.json()
    path = body.get("path", "").strip()
    name = body.get("name", "").strip()
    if not path:
        return JSONResponse(content={"error": "Path required"}, status_code=400)
    try:
        ws = wm.add_workspace(path, name)
        return JSONResponse(content=ws)
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.delete("/api/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    ok = wm.remove_workspace(workspace_id)
    return JSONResponse(content={"status": "ok" if ok else "not found"})


@app.get("/api/workspaces/{workspace_id}/chats")
async def get_chats(workspace_id: str):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    chats = wm.list_chats(ws["path"])
    return JSONResponse(content={"chats": chats})


@app.post("/api/workspaces/{workspace_id}/chats")
async def create_chat_endpoint(workspace_id: str, req: Request):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    body = await req.json()
    title = body.get("title", "")
    model = body.get("model", "Automatic Fallback")
    chat = wm.create_chat(ws["path"], title, model)
    return JSONResponse(content=chat)


@app.get("/api/workspaces/{workspace_id}/chats/{chat_id}")
async def get_chat_endpoint(workspace_id: str, chat_id: str):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    chat = wm.get_chat(ws["path"], chat_id)
    if not chat:
        return JSONResponse(content={"error": "Chat not found"}, status_code=404)
    return JSONResponse(content=chat)


@app.delete("/api/workspaces/{workspace_id}/chats/{chat_id}")
async def delete_chat_endpoint(workspace_id: str, chat_id: str):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    ok = wm.delete_chat(ws["path"], chat_id)
    return JSONResponse(content={"status": "ok" if ok else "not found"})


@app.post("/api/workspaces/{workspace_id}/chats/{chat_id}/messages")
async def add_message_endpoint(workspace_id: str, chat_id: str, req: Request):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    body = await req.json()
    role = body.get("role", "user")
    content = body.get("content", "")
    meta = body.get("metadata")
    msg = wm.add_message(ws["path"], chat_id, role, content, meta)
    if not msg:
        return JSONResponse(content={"error": "Chat not found"}, status_code=404)
    return JSONResponse(content=msg)


@app.put("/api/workspaces/{workspace_id}/chats/{chat_id}/title")
async def update_chat_title(workspace_id: str, chat_id: str, req: Request):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    body = await req.json()
    title = body.get("title", "")
    ok = wm.update_chat_title(ws["path"], chat_id, title)
    return JSONResponse(content={"status": "ok" if ok else "not found"})


# ═══════════════════════════════════════════════════════════════════════════════
# Settings & Rules API
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/settings/profile")
async def get_profile():
    profile_path = r"d:\MyProject\LangChain\.deep_agents\user_profile.json"
    default_profile = {
        "user_info": {"name": "Davin Akmal Yasha"},
        "global_rules": []
    }
    if os.path.isfile(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception:
            pass
    return JSONResponse(content=default_profile)

@app.post("/api/settings/profile")
async def save_profile(req: Request):
    profile_path = r"d:\MyProject\LangChain\.deep_agents\user_profile.json"
    body = await req.json()
    try:
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/workspaces/{workspace_id}/rules")
async def get_workspace_rules(workspace_id: str):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    rules_path = os.path.join(ws["path"], ".deep_agents", "rules.json")
    default_rules = {
        "stack": {},
        "workspace_rules": []
    }
    if os.path.isfile(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception:
            pass
    return JSONResponse(content=default_rules)

@app.post("/api/workspaces/{workspace_id}/rules")
async def save_workspace_rules(workspace_id: str, req: Request):
    ws = wm.get_workspace(workspace_id)
    if not ws:
        return JSONResponse(content={"error": "Workspace not found"}, status_code=404)
    rules_path = os.path.join(ws["path"], ".deep_agents", "rules.json")
    body = await req.json()
    try:
        os.makedirs(os.path.dirname(rules_path), exist_ok=True)
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


def start_consolidation_daemon():
    """Starts a periodic background daemon thread for memory consolidation."""
    import time
    from memory_consolidation_daemon import consolidate_memories
    
    def daemon_loop():
        print("[DAEMON] Background memory consolidation daemon started.")
        while True:
            try:
                consolidate_memories()
            except Exception as e:
                print(f"[DAEMON] Memory consolidation failed: {e}")
            # Run every 6 hours
            time.sleep(21600)
            
    threading.Thread(target=daemon_loop, daemon=True).start()


# ── Startup ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import sys
    
    reload_mode = "--reload" in sys.argv
    
    # Start Telegram bot in background
    try:
        from bot import bot
        threading.Thread(target=bot.infinity_polling, daemon=True).start()
        print("[API] Telegram bot started in background.")
    except Exception as e:
        print(f"[API] Failed to start Telegram bot: {e}")
        
    # Start Memory Consolidation Daemon in background
    try:
        start_consolidation_daemon()
    except Exception as e:
        print(f"[API] Failed to start memory consolidation daemon: {e}")
        
    if reload_mode:
        uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=True)
    else:
        print("[API] Running in production mode (reload disabled).")
        uvicorn.run(app, host="127.0.0.1", port=8000)
