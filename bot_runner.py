import os
import time
import threading
from state_sync import shared_state, safe_get_state
from sync_manager import run_and_sync_graph

WORKSPACE_DIR = r"D:\MyProject"

def format_telegram_status(s: dict) -> str:
    """Formats shared_state into a human-readable Telegram status message using subordinate persona."""
    txt = f"Running: \"{s['client_request']}\"\n\n"
    for node in s["completed_nodes"]:
        txt += f"✅ {node.upper()} Specialist: Task Completed\n"

    if s["active_node"] == "supervisor":
        nxt = s["next_agent"]
        if nxt == "finish":
            txt += "Done. All tasks completed.\n"
        else:
            txt += f"Routing to {nxt.upper()} agent...\n"
    elif s["active_node"]:
        txt += f"⏳ {s['active_node'].upper()} Specialist: In Progress...\n"

    if s.get("project_path"):
        txt += f"\n📁 Project Directory: `{s['project_path']}`\n"

    if s.get("live_terminal_log"):
        lines = s["live_terminal_log"].split("\n")[-8:]
        snippet = "\n".join(lines).strip()
        if snippet:
            txt += f"\n💻 Live Console:\n```\n{snippet}\n```"

    return txt

def send_deliverables(bot, chat_id: int, msg_id: int, req: str) -> None:
    """Sends all generated Word docs and project info via Telegram."""
    import voice_services
    doc_files = [
        "1_Requirements.docx",
        "2_TechnicalSpec.docx",
        "Analytics_Report.docx",
    ]
    for doc_name in doc_files:
        doc_path = os.path.join(WORKSPACE_DIR, doc_name)
        if os.path.exists(doc_path):
            try:
                with open(doc_path, "rb") as f:
                    bot.send_document(chat_id, f)
            except Exception as e:
                print(f"Error sending {doc_name}: {e}")

    project_path = shared_state.get("project_path", "")
    if project_path and os.path.isdir(project_path):
        bot.send_message(
            chat_id,
            f"📁 *Project successfully established:*\n`{project_path}`\n\n"
            f"All source code is prepared for your review in the directory above.",
            parse_mode="Markdown",
        )

    summary = f"Workflow successfully executed: {req}."
    tts_path = os.path.join(WORKSPACE_DIR, f"reply_{msg_id}.mp3")
    voice_services.generate_tts_sync(summary, tts_path)
    if os.path.exists(tts_path):
        with open(tts_path, "rb") as f:
            bot.send_voice(chat_id, f, caption="🎙️ Summary")
        try:
            os.remove(tts_path)
        except Exception:
            pass

def handle_build_request(bot, req: str, chat_id: int, status_msg) -> None:
    """Runs the full agentic pipeline and sends live status updates."""
    if status_msg is None:
        status_msg = bot.send_message(chat_id, "⏳ Starting the execution pipeline...")

    is_running = True
    def runner() -> None:
        nonlocal is_running
        try:
            for _ in run_and_sync_graph(req, workspace_path=WORKSPACE_DIR):
                pass
        finally:
            is_running = False

    threading.Thread(target=runner, daemon=True).start()

    last_text = ""
    while is_running:
        txt = format_telegram_status(safe_get_state())
        if txt != last_text:
            try:
                bot.edit_message_text(txt, chat_id, status_msg.message_id)
                last_text = txt
            except Exception:
                pass
        time.sleep(2)

    # Final status update
    txt = format_telegram_status(safe_get_state())
    if txt != last_text:
        try:
            bot.edit_message_text(txt, chat_id, status_msg.message_id)
        except Exception:
            pass

    bot.send_message(chat_id, "🎉 Commands fully executed. Delivering assets now.")
    send_deliverables(bot, chat_id, status_msg.message_id, req)
