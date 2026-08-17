"""Language detection and patterns for Code Sherpa."""
import re
from dataclasses import dataclass

# File extension to language mapping
EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".sql": "sql",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".txt": "text",
}

# Languages supported by tree-sitter
TREE_SITTER_LANGUAGES = {
    "python", "javascript", "typescript", "go", "java", "rust", "c", "cpp", "ruby"
}

# Files to skip during parsing
SKIP_PATTERNS = {
    "__pycache__", "node_modules", ".git", ".svn", ".hg",
    "venv", "env", ".env", ".venv", "dist", "build",
    ".idea", ".vscode", ".vs", "__MACOSX", ".DS_Store",
    "vendor", "target", "bin", "obj", ".tox", ".pytest_cache",
    ".mypy_cache", "coverage", ".coverage", "htmlcov",
    "egg-info", ".eggs", "*.pyc", "*.pyo", "*.so", "*.dll",
    "*.exe", "*.o", "*.a", "*.lib", "*.dylib",
}

# Max file size to parse (1MB)
MAX_FILE_SIZE = 1_000_000

# Key project files for "map" query
KEY_FILE_PATTERNS = {
    "build_config": [
        "pyproject.toml", "setup.py", "setup.cfg", "package.json",
        "Cargo.toml", "go.mod", "go.sum", "pom.xml", "build.gradle",
        "build.gradle.kts", "Makefile", "CMakeLists.txt", "meson.build",
        "requirements.txt", "Pipfile", "poetry.lock", "yarn.lock",
        "package-lock.json", "Gemfile", "composer.json",
    ],
    "container": [
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        ".dockerignore", "kubernetes.yml", "k8s.yml",
    ],
    "documentation": [
        "README.md", "README.rst", "README.txt", "README",
        "CHANGELOG.md", "CHANGELOG", "CHANGES.md", "CHANGES",
        "CONTRIBUTING.md", "CONTRIBUTING", "LICENSE", "LICENSE.md",
        "CODE_OF_CONDUCT.md", "SECURITY.md",
    ],
    "entry_points": [
        "main.py", "app.py", "index.py", "server.py", "cli.py",
        "main.go", "main.rs", "Main.java",
        "index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts",
        "main.c", "main.cpp",
    ],
    "config": [
        ".env", ".env.example", "config.py", "settings.py",
        "config.js", "config.ts", "config.yaml", "config.yml",
        "config.json", ".eslintrc", ".prettierrc", "tsconfig.json",
        "jest.config.js", "webpack.config.js", "vite.config.js",
    ],
    "ci_cd": [
        ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile",
        ".travis.yml", ".circleci", "azure-pipelines.yml",
    ],
}

# Import patterns for dependency extraction
IMPORT_PATTERNS = {
    "python": [
        re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
        re.compile(r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE),
    ],
    "javascript": [
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
        re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
    ],
    "typescript": [
        re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
        re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.MULTILINE),
    ],
    "go": [
        re.compile(r'import\s+"([^"]+)"', re.MULTILINE),
        re.compile(r'^\s+"([^"]+)"\s*$', re.MULTILINE),
    ],
    "java": [
        re.compile(r"^\s*import\s+([\w.]+);", re.MULTILINE),
    ],
    "rust": [
        re.compile(r"^\s*use\s+([\w:]+)", re.MULTILINE),
        re.compile(r"^\s*extern\s+crate\s+(\w+)", re.MULTILINE),
    ],
    "ruby": [
        re.compile(r"""^\s*require\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"""^\s*require_relative\s+['"]([^'"]+)['"]""", re.MULTILINE),
    ],
    "php": [
        re.compile(r"""^\s*(?:require|include)(?:_once)?\s+['"]([^'"]+)['"]""", re.MULTILINE),
        re.compile(r"^\s*use\s+([\w\\]+)", re.MULTILINE),
    ],
}

# Fallback import pattern for unsupported languages
GENERIC_IMPORT_PATTERN = re.compile(
    r"^\s*(?:import|require|include|use|from)\s+['\"]?([^\s'\"();]+)",
    re.MULTILINE
)

# Class inheritance patterns
INHERITANCE_PATTERNS = {
    "python": re.compile(r"class\s+\w+\s*\(([^)]+)\)"),
    "javascript": re.compile(r"class\s+\w+\s+extends\s+(\w+)"),
    "typescript": re.compile(r"class\s+\w+\s+extends\s+(\w+)"),
    "java": re.compile(r"class\s+\w+\s+extends\s+(\w+)"),
    "go": None,  # Go uses composition, not inheritance
    "rust": None,  # Rust uses traits
    "ruby": re.compile(r"class\s+\w+\s*<\s*(\w+)"),
    "php": re.compile(r"class\s+\w+\s+extends\s+(\w+)"),
    "cpp": re.compile(r"class\s+\w+\s*:\s*(?:public|private|protected)\s+(\w+)"),
}


def detect_language(file_path: str) -> str | None:
    """Detect programming language from file extension."""
    import os
    _, ext = os.path.splitext(file_path)
    return EXTENSION_MAP.get(ext.lower())


def should_skip(path: str) -> bool:
    """Check if a path should be skipped during parsing."""
    import os
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        if part in SKIP_PATTERNS:
            return True
        # Check glob patterns
        for pattern in SKIP_PATTERNS:
            if "*" in pattern:
                import fnmatch
                if fnmatch.fnmatch(part, pattern):
                    return True
    return False


def extract_imports(content: str, language: str) -> list[str]:
    """Extract import/dependency references from code."""
    patterns = IMPORT_PATTERNS.get(language, [GENERIC_IMPORT_PATTERN])
    if not isinstance(patterns, list):
        patterns = [patterns]
    
    imports = []
    for pattern in patterns:
        for match in pattern.finditer(content):
            imports.append(match.group(1))
    return imports
