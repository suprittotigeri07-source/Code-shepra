"""Code chunking pipeline for Code Sherpa.

Parses source files into semantic chunks (functions, classes, modules)
using tree-sitter for AST-based parsing with regex fallback.
"""
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from parser.languages import (
    TREE_SITTER_LANGUAGES,
    MAX_FILE_SIZE,
    detect_language,
    should_skip,
)

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """A semantic unit of code extracted from a source file."""
    file_path: str
    chunk_type: str  # "function", "class", "module", "method"
    chunk_name: str
    language: str
    start_line: int
    end_line: int
    content: str
    file_hash: str = ""


@dataclass
class ParseResult:
    """Result of parsing a codebase."""
    chunks: list[CodeChunk] = field(default_factory=list)
    files_processed: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    errors: list[str] = field(default_factory=list)


# Tree-sitter node types that represent functions/methods/classes
TS_FUNCTION_TYPES = {
    "python": ["function_definition", "decorated_definition"],
    "javascript": ["function_declaration", "arrow_function", "method_definition",
                    "function_expression", "generator_function_declaration"],
    "typescript": ["function_declaration", "arrow_function", "method_definition",
                    "function_expression", "generator_function_declaration"],
    "go": ["function_declaration", "method_declaration"],
    "java": ["method_declaration", "constructor_declaration"],
    "rust": ["function_item", "impl_item"],
    "c": ["function_definition"],
    "cpp": ["function_definition", "template_declaration"],
    "ruby": ["method", "singleton_method"],
}

TS_CLASS_TYPES = {
    "python": ["class_definition"],
    "javascript": ["class_declaration"],
    "typescript": ["class_declaration", "interface_declaration"],
    "go": ["type_declaration"],
    "java": ["class_declaration", "interface_declaration", "enum_declaration"],
    "rust": ["struct_item", "enum_item", "trait_item"],
    "c": ["struct_specifier"],
    "cpp": ["class_specifier", "struct_specifier"],
    "ruby": ["class", "module"],
}


def _get_tree_sitter_language(lang_name: str):
    """Load a tree-sitter language parser."""
    try:
        if lang_name == "python":
            import tree_sitter_python as tsp
            return tsp.language()
        elif lang_name == "javascript":
            import tree_sitter_javascript as tsjs
            return tsjs.language()
        elif lang_name == "typescript":
            import tree_sitter_typescript as tsts
            return tsts.language_typescript()
        elif lang_name == "go":
            import tree_sitter_go as tsgo
            return tsgo.language()
        elif lang_name == "java":
            import tree_sitter_java as tsjava
            return tsjava.language()
        elif lang_name == "rust":
            import tree_sitter_rust as tsrust
            return tsrust.language()
        elif lang_name == "c":
            import tree_sitter_c as tsc
            return tsc.language()
        elif lang_name == "cpp":
            import tree_sitter_cpp as tscpp
            return tscpp.language()
        elif lang_name == "ruby":
            import tree_sitter_ruby as tsruby
            return tsruby.language()
    except ImportError:
        return None
    return None


def _extract_node_name(node, language: str) -> str:
    """Extract the name/identifier from an AST node."""
    # Look for identifier child
    for child in node.children:
        if child.type == "identifier":
            return child.text.decode("utf-8") if isinstance(child.text, bytes) else child.text
        if child.type == "name":
            return child.text.decode("utf-8") if isinstance(child.text, bytes) else child.text
        # Python decorated_definition: get the inner function/class
        if child.type in ("function_definition", "class_definition"):
            return _extract_node_name(child, language)
    return "<anonymous>"


def _chunk_with_tree_sitter(content: str, language: str, file_path: str, file_hash: str) -> list[CodeChunk]:
    """Parse code into chunks using tree-sitter AST."""
    import tree_sitter
    
    lang_obj = _get_tree_sitter_language(language)
    if lang_obj is None:
        return []
    
    parser = tree_sitter.Parser(tree_sitter.Language(lang_obj))
    content_bytes = content.encode("utf-8")
    tree = parser.parse(content_bytes)
    
    chunks = []
    function_types = set(TS_FUNCTION_TYPES.get(language, []))
    class_types = set(TS_CLASS_TYPES.get(language, []))
    
    # Track which line ranges are covered by extracted chunks
    covered_ranges = []
    
    def walk_tree(node, depth=0):
        node_type = node.type
        
        if node_type in function_types:
            name = _extract_node_name(node, language)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            chunk_content = content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            
            chunk_type = "method" if depth > 0 else "function"
            chunks.append(CodeChunk(
                file_path=file_path,
                chunk_type=chunk_type,
                chunk_name=name,
                language=language,
                start_line=start_line,
                end_line=end_line,
                content=chunk_content,
                file_hash=file_hash,
            ))
            covered_ranges.append((start_line, end_line))
            return  # Don't recurse into function body
            
        elif node_type in class_types:
            name = _extract_node_name(node, language)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            chunk_content = content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            
            chunks.append(CodeChunk(
                file_path=file_path,
                chunk_type="class",
                chunk_name=name,
                language=language,
                start_line=start_line,
                end_line=end_line,
                content=chunk_content,
                file_hash=file_hash,
            ))
            covered_ranges.append((start_line, end_line))
            
            # Also extract methods inside the class
            for child in node.children:
                walk_tree(child, depth + 1)
            return
        
        # Recurse into children
        for child in node.children:
            walk_tree(child, depth)
    
    walk_tree(tree.root_node)
    
    # If no chunks were extracted, treat entire file as a module chunk
    if not chunks:
        lines = content.split("\n")
        chunks.append(CodeChunk(
            file_path=file_path,
            chunk_type="module",
            chunk_name=os.path.basename(file_path),
            language=language,
            start_line=1,
            end_line=len(lines),
            content=content,
            file_hash=file_hash,
        ))
    
    return chunks


# Regex-based fallback patterns for languages without tree-sitter support
REGEX_PATTERNS = {
    "python": [
        (re.compile(r"^(class\s+\w+.*?(?=\nclass\s|\ndef\s|\Z))", re.MULTILINE | re.DOTALL), "class"),
        (re.compile(r"^(def\s+\w+.*?(?=\ndef\s|\nclass\s|\Z))", re.MULTILINE | re.DOTALL), "function"),
    ],
    "javascript": [
        (re.compile(r"^((?:export\s+)?(?:async\s+)?function\s+\w+.*?^\})", re.MULTILINE | re.DOTALL), "function"),
        (re.compile(r"^((?:export\s+)?class\s+\w+.*?^\})", re.MULTILINE | re.DOTALL), "class"),
    ],
    "default": [
        (re.compile(r"^(\w[\w\s]*\w\s*\([^)]*\)\s*\{.*?^\})", re.MULTILINE | re.DOTALL), "function"),
    ],
}


def _chunk_with_regex(content: str, language: str, file_path: str, file_hash: str) -> list[CodeChunk]:
    """Fallback: parse code into chunks using regex patterns."""
    chunks = []
    patterns = REGEX_PATTERNS.get(language, REGEX_PATTERNS["default"])
    lines = content.split("\n")
    
    for pattern, chunk_type in patterns:
        for match in pattern.finditer(content):
            chunk_content = match.group(1)
            start_offset = match.start()
            end_offset = match.end()
            
            start_line = content[:start_offset].count("\n") + 1
            end_line = content[:end_offset].count("\n") + 1
            
            # Extract name (first word after keyword)
            name_match = re.search(r"(?:class|def|function|func)\s+(\w+)", chunk_content)
            name = name_match.group(1) if name_match else "<anonymous>"
            
            chunks.append(CodeChunk(
                file_path=file_path,
                chunk_type=chunk_type,
                chunk_name=name,
                language=language,
                start_line=start_line,
                end_line=end_line,
                content=chunk_content,
                file_hash=file_hash,
            ))
    
    # If no chunks found, treat as module
    if not chunks:
        chunks.append(CodeChunk(
            file_path=file_path,
            chunk_type="module",
            chunk_name=os.path.basename(file_path),
            language=language,
            start_line=1,
            end_line=len(lines),
            content=content,
            file_hash=file_hash,
        ))
    
    return chunks


def compute_file_hash(content: str) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def parse_codebase(
    root_path: str,
    progress_callback: Callable[[str, int, int, int], None] | None = None,
) -> ParseResult:
    """Parse a codebase directory into semantic code chunks.
    
    Args:
        root_path: Path to the root of the codebase
        progress_callback: Optional callback(status_msg, files_processed, chunks_created, failures)
    
    Returns:
        ParseResult with chunks and statistics
    """
    result = ParseResult()
    root = Path(root_path).resolve()
    
    if not root.exists():
        result.errors.append(f"Path does not exist: {root_path}")
        return result
    
    # Collect all source files
    source_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip directories
        dirnames[:] = [d for d in dirnames if not should_skip(d)]
        
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root).replace("\\", "/")
            
            if should_skip(rel_path):
                continue
            
            language = detect_language(filename)
            if language is None:
                continue
            
            # Skip binary/large files
            try:
                file_size = os.path.getsize(filepath)
                if file_size > MAX_FILE_SIZE:
                    result.files_skipped += 1
                    continue
                if file_size == 0:
                    result.files_skipped += 1
                    continue
            except OSError:
                result.files_skipped += 1
                continue
            
            source_files.append((filepath, rel_path, language))
    
    total_files = len(source_files)
    logger.info(f"Found {total_files} source files to parse in {root_path}")
    
    for i, (filepath, rel_path, language) in enumerate(source_files):
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            
            file_hash = compute_file_hash(content)
            
            # Try tree-sitter first, then regex fallback
            if language in TREE_SITTER_LANGUAGES:
                try:
                    chunks = _chunk_with_tree_sitter(content, language, rel_path, file_hash)
                except Exception as e:
                    logger.warning(f"Tree-sitter parse failed for {rel_path}: {e}")
                    chunks = _chunk_with_regex(content, language, rel_path, file_hash)
            else:
                chunks = _chunk_with_regex(content, language, rel_path, file_hash)
            
            result.chunks.extend(chunks)
            result.files_processed += 1
            
            if progress_callback and (i % 10 == 0 or i == total_files - 1):
                progress_callback(
                    f"Parsing: {rel_path}",
                    result.files_processed,
                    len(result.chunks),
                    result.files_failed,
                )
                
        except Exception as e:
            error_msg = f"Failed to parse {rel_path}: {str(e)}"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            result.files_failed += 1
    
    logger.info(
        f"Parsing complete: {result.files_processed} files, "
        f"{len(result.chunks)} chunks, {result.files_failed} failures"
    )
    return result
