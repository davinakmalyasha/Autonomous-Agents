import os

WORKSPACE_DIR = r"D:\MyProject"

def safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except Exception:
        pass

def transcribe_voice(bot, msg) -> str:
    """Downloads and transcribes a voice message."""
    import voice_services
    try:
        file_info = bot.get_file(msg.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)
        audio_path = os.path.join(WORKSPACE_DIR, f"voice_{msg.message_id}.ogg")
        with open(audio_path, "wb") as f:
            f.write(downloaded)
        text = voice_services.transcribe_audio(audio_path)
        safe_remove(audio_path)
        return text
    except Exception as e:
        return f"Error transcribing: {e}"

