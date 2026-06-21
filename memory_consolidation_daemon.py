import os
import json
import sqlite3
import gzip
from memory_io import load_memory, save_memory
from llm import invoke_with_fallback
from pydantic import BaseModel, Field

class ConsolidatedMemory(BaseModel):
    lessons_learned: list[str] = Field(default_factory=list, description="New coding/debugging lessons learned or pitfalls to avoid.")
    past_requests: list[str] = Field(default_factory=list, description="Client feature requests completed in this iteration.")
    new_technologies: list[str] = Field(default_factory=list, description="Specific frameworks, tools, or libraries used.")

def consolidate_memories():
    db_path = r"d:\MyProject\LangChain\.deep_agents\checkpoints.db"
    if not os.path.isfile(db_path):
        print("No checkpoints database found.")
        return
        
    print("Starting background memory consolidation...")
    
    # 1. Fetch recent checkpoints
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT type, checkpoint, metadata FROM checkpoints LIMIT 50")
        rows = cur.fetchall()
    except Exception as e:
        print(f"Error fetching checkpoints: {e}")
        return
    finally:
        try:
            conn.close()
        except Exception:
            pass
    
    conversations = []
    for type_col, checkpoint_blob, metadata_blob in rows:
        is_gzip = "+gzip" in type_col
        metadata_str = ""
        if metadata_blob:
            try:
                if is_gzip:
                    metadata_str = gzip.decompress(metadata_blob).decode("utf-8", errors="replace")
                else:
                    metadata_str = metadata_blob.decode("utf-8", errors="replace")
            except Exception:
                pass
        if metadata_str:
            conversations.append(metadata_str)
            
    if not conversations:
        print("No recent conversation history found.")
        return
        
    # 2. Invoke LLM to consolidate memories
    sys_inst = (
        "You are the Background Memory Consolidation Agent. Audit the recent conversation histories "
        "and extract new lessons learned, completed requests, and new technologies introduced."
    )
    prompt = "Recent Conversations:\n" + "\n---\n".join(conversations[:20])
    
    try:
        res: ConsolidatedMemory = invoke_with_fallback(
            role="MemoryConsolidation",
            sys_inst=sys_inst,
            prompt=prompt,
            schema=ConsolidatedMemory,
            temp=0.1
        )
    except Exception as e:
        print(f"Memory consolidation LLM call failed: {e}")
        return
        
    # 3. Load current memory, merge, and save
    current_mem = load_memory()
    
    # Merge lessons learned
    lessons = current_mem.setdefault("lessons_learned", [])
    for lesson in res.lessons_learned:
        if lesson not in lessons:
            lessons.append(lesson)
            
    # Merge past requests
    requests = current_mem.setdefault("past_requests", [])
    for req in res.past_requests:
        if req not in requests:
            requests.append(req)
            
    # Merge technologies
    it = current_mem.setdefault("it_department", {})
    techs = it.setdefault("technologies", [])
    for tech in res.new_technologies:
        if tech not in techs:
            techs.append(tech)
            
    save_memory(current_mem)
    
    # 4. Generate Markdown and save to /memories/AGENTS.md
    from tools import write_file
    
    markdown_content = "# Agent Memories and Guidelines\n\n"
    
    markdown_content += "## Lessons Learned\n"
    if lessons:
        for lesson in lessons:
            markdown_content += f"- {lesson}\n"
    else:
        markdown_content += "- No lessons recorded yet.\n"
        
    markdown_content += "\n## Past Completed Requests\n"
    if requests:
        for req in requests:
            markdown_content += f"- {req}\n"
    else:
        markdown_content += "- No completed requests recorded yet.\n"
        
    markdown_content += "\n## Technologies and Libraries Used\n"
    if techs:
        for tech in techs:
            markdown_content += f"- {tech}\n"
    else:
        markdown_content += "- No technologies recorded yet.\n"
        
    try:
        write_file("/memories/AGENTS.md", markdown_content)
        print("Consolidated memories written to /memories/AGENTS.md.")
    except Exception as e:
        print(f"Error writing /memories/AGENTS.md: {e}")
        
    print("Background memory consolidation complete. Memories saved.")

if __name__ == "__main__":
    consolidate_memories()
