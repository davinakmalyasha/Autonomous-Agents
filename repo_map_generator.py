"""
Repository Map Generator — Compiles codebases into a token-efficient signature map.
Uses tree-sitter AST parsing for Python, PHP, TypeScript, and JavaScript.
Falls back to robust regex signature extraction for Dart and parse failures.
"""
import os
import sys
from typing import List, Tuple, Dict, Set, Optional

# Reconfigure console output encoding to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Try importing tree_sitter
try:
    import tree_sitter_languages as tsl
    from tree_sitter import Parser, Node
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


def _extract_ast_signature(node: 'Node', content_lines: List[str], lang: str) -> str:
    """Extract complete signature line(s) from a tree-sitter AST node."""
    start_row = node.start_point[0]
    end_row = start_row
    
    # Scan lines to find definition boundaries
    if lang in ("typescript", "tsx", "javascript", "php"):
        for r in range(start_row, len(content_lines)):
            line = content_lines[r]
            if '{' in line:
                end_row = r
                break
            end_row = r
    elif lang == "python":
        for r in range(start_row, len(content_lines)):
            line = content_lines[r]
            cleaned = line.split('#')[0].strip()
            if cleaned.endswith(':'):
                end_row = r
                break
            end_row = r
            
    sig_lines = content_lines[start_row:end_row + 1]
    
    # Strip brackets/bodies for C-like languages
    if lang in ("typescript", "tsx", "javascript", "php") and sig_lines:
        last_line = sig_lines[-1]
        brace_idx = last_line.find('{')
        if brace_idx != -1:
            sig_lines[-1] = last_line[:brace_idx].rstrip()
            
    # Strip trailing colon for Python
    if lang == "python" and sig_lines:
        last_line = sig_lines[-1]
        if last_line.rstrip().endswith(':'):
            sig_lines[-1] = last_line.rstrip()[:-1].rstrip()
            
    return " ".join(line.strip() for line in sig_lines)


def _extract_ast_signatures(content: str, lang: str) -> List[Tuple[str, int]]:
    """Extract signatures using tree-sitter AST parsing."""
    if not HAS_TREE_SITTER:
        raise ImportError("tree-sitter-languages is not installed.")
        
    parser = tsl.get_parser(lang)
    content_bytes = content.encode('utf-8')
    tree = parser.parse(content_bytes)
    content_lines = content.splitlines()
    
    signatures: List[Tuple[str, int]] = []
    
    def traverse(node: 'Node', depth: int = 0) -> None:
        node_type = node.type
        is_target = False
        
        if lang == "python":
            is_target = node_type in ("class_definition", "function_definition")
        elif lang in ("typescript", "tsx", "javascript"):
            is_target = node_type in ("class_declaration", "method_definition", "function_declaration")
        elif lang == "php":
            is_target = node_type in ("class_declaration", "method_declaration")
            
        if is_target:
            sig = _extract_ast_signature(node, content_lines, lang)
            signatures.append((sig, depth))
            for child in node.children:
                traverse(child, depth + 1)
        else:
            for child in node.children:
                traverse(child, depth)
                
    traverse(tree.root_node)
    return signatures


def _extract_regex_signatures(content: str, ext: str) -> List[Tuple[str, int]]:
    """Extract signatures using fallback regex matching (e.g. for Dart or broken code)."""
    signatures: List[Tuple[str, int]] = []
    lines = content.splitlines()
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("import ") or stripped.startswith("part "):
            continue
            
        indent = len(line) - len(line.lstrip())
        depth = indent // 4
        
        # Dart signature patterns
        if ext == ".dart":
            if stripped.startswith("class ") or " class " in stripped:
                signatures.append((stripped.split('{')[0].strip(), depth))
            elif '(' in stripped and ')' in stripped and ('{' in stripped or stripped.endswith(';')):
                if not any(k in stripped for k in ["if", "for", "while", "switch", "catch"]):
                    signatures.append((stripped.split('{')[0].strip(), depth))
                    
        # Python fallback patterns
        elif ext == ".py":
            if stripped.startswith("class ") or stripped.startswith("def ") or stripped.startswith("async def "):
                signatures.append((stripped.split(':')[0].strip(), depth))
                
        # PHP fallback patterns
        elif ext == ".php":
            if stripped.startswith("class ") or " class " in stripped:
                signatures.append((stripped.split('{')[0].strip(), depth))
            elif "function " in stripped:
                signatures.append((stripped.split('{')[0].strip(), depth))
                
        # JavaScript/TypeScript fallback patterns
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            if "class " in stripped or "interface " in stripped or "type " in stripped:
                signatures.append((stripped.split('{')[0].strip(), depth))
            elif "function " in stripped or "=>" in stripped or ("(" in stripped and ")" in stripped and "{" in stripped):
                if not any(k in stripped for k in ["if", "for", "while", "switch", "catch"]):
                    signatures.append((stripped.split('{')[0].strip(), depth))
                    
    return signatures


def get_file_signatures(file_path: str, ext: str, is_hot: bool) -> List[Tuple[str, int]]:
    """Get signatures for a file using tree-sitter AST, falling back to regex."""
    if not os.path.isfile(file_path):
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return []
        
    lang_map = {
        ".py": "python",
        ".php": "php",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "javascript",
    }
    
    signatures: List[Tuple[str, int]] = []
    
    # AST-First query
    if ext in lang_map and HAS_TREE_SITTER:
        try:
            signatures = _extract_ast_signatures(content, lang_map[ext])
        except Exception:
            # Fallback to regex on parser exception/corruption
            signatures = _extract_regex_signatures(content, ext)
    else:
        # Dart or non-tree-sitter extensions go straight to regex
        signatures = _extract_regex_signatures(content, ext)
        
    # Apply dynamic depth compression if the file is NOT hot
    if not is_hot:
        # Keep only class declarations and top-level definitions (depth == 0)
        signatures = [(sig, depth) for sig, depth in signatures if depth == 0 or "class " in sig]
        
    return signatures


class RepoMapGenerator:
    """Orchestrates Repository Map compilation for the workspace."""
    
    def __init__(self, project_path: str, hot_files: Optional[List[str]] = None) -> None:
        self.project_path = os.path.normpath(os.path.abspath(project_path))
        self.hot_files = set()
        if hot_files:
            for f in hot_files:
                self.hot_files.add(os.path.normpath(f).lower())
                
    def _is_hot_file(self, rel_path: str) -> bool:
        abs_path = os.path.normpath(os.path.join(self.project_path, rel_path)).lower()
        return abs_path in self.hot_files or rel_path.lower() in self.hot_files

    def generate_map(self) -> str:
        """Walk the directory, extract signatures, and format the final map."""
        ignored_dirs = {
            "node_modules", "vendor", ".git", "venv", ".venv", "__pycache__",
            ".deep_agents", ".claude", "dist", "build", ".pytest_cache",
            ".vscode", ".idea", "storage", "public", "venv312", "scratch",
            ".antigravity"
        }
        
        supported_exts = {".py", ".php", ".ts", ".tsx", ".js", ".jsx", ".dart"}
        
        map_lines: List[str] = []
        file_count = 0
        
        # 1. Walk directory and group file paths
        files_to_process: List[str] = []
        try:
            for root, dirs, files in os.walk(self.project_path):
                dirs[:] = [d for d in dirs if d not in ignored_dirs]
                for file in files:
                    _, ext = os.path.splitext(file)
                    if ext.lower() in supported_exts:
                        rel_path = os.path.relpath(os.path.join(root, file), self.project_path).replace("\\", "/")
                        files_to_process.append(rel_path)
        except Exception as e:
            return f"Error walking directory: {e}"
            
        # Limit total parsed files to avoid context explosions on large repositories
        # (The Dynamic Depth Map naturally bounds size, but we keep a hard limit of 150 files)
        files_to_process = sorted(files_to_process, key=lambda f: (not self._is_hot_file(f), f))
        
        for rel_path in files_to_process[:150]:
            _, ext = os.path.splitext(rel_path)
            abs_path = os.path.join(self.project_path, rel_path)
            is_hot = self._is_hot_file(rel_path)
            
            signatures = get_file_signatures(abs_path, ext.lower(), is_hot)
            if not signatures:
                continue
                
            map_lines.append(f"{rel_path}:")
            for sig, depth in signatures:
                indent = "  " * depth
                map_lines.append(f"{indent}│ {sig}")
            map_lines.append("")
            file_count += 1
            
        if not map_lines:
            return "(No classes or functions found in workspace files)"
            
        return "\n".join(map_lines).strip()
