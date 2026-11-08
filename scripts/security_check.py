#!/usr/bin/env python3
"""Small, dependency-free repository policy check, not a vulnerability scanner.

Checks project-owned source only. It deliberately does not execute scanned files.
Findings contain rule names and line numbers, never matched credential values.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

MAX_FILE_BYTES = 2_000_000
IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'build', 'dist', '.ruff_cache', '.pytest_cache', '.mypy_cache', 'node_modules'}
TEXT_SUFFIXES = {'.py', '.md', '.toml', '.yml', '.yaml', '.json', '.txt', '.html', '.css', '.csv'}
SECRET_PATTERNS = (
    ('private-key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
    ('github-token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})\b')),
    ('aws-access-key', re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('provider-key', re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,255}\b')),
)
# The runtime is intentionally offline and cannot execute generated code.
BANNED_IMPORTS = {'subprocess', 'pickle', 'dill', 'shelve', 'requests', 'httpx', 'socket', 'urllib.request', 'http.client'}
BANNED_CALLS = {'eval', 'exec', 'compile', '__import__', 'os.system', 'os.popen', 'builtins.eval', 'builtins.exec', 'builtins.compile', 'builtins.__import__'}


def _qualified(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified(node.value)
        return f'{prefix}.{node.attr}' if prefix else ''
    return ''


def inspect_python(text: str) -> list[tuple[int, str]]:
    """Return simple static violations; this is not general data-flow analysis."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [(exc.lineno or 1, 'invalid-python')]
    findings = []
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
                if any(alias.name == mod or alias.name.startswith(mod + '.') for mod in BANNED_IMPORTS):
                    findings.append((node.lineno, 'offline-runtime-import'))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = f'{node.module}.{alias.name}'
                aliases[alias.asname or alias.name] = name
                if any(name == mod or name.startswith(mod + '.') for mod in BANNED_IMPORTS):
                    findings.append((node.lineno, 'offline-runtime-import'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _qualified(node.func)
            head, separator, tail = name.partition('.')
            resolved = aliases.get(head, head) + (separator + tail if separator else '')
            if name in BANNED_CALLS or resolved in BANNED_CALLS:
                findings.append((node.lineno, 'dynamic-code-execution'))
    return sorted(set(findings))


def inspect_workflow(text: str) -> list[tuple[int, str]]:
    """Validate narrow workflow conventions without evaluating YAML tags."""
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        code = line.split('#', 1)[0]
        if re.search(r'\b(?:pull_request_target|workflow_run)\b', code):
            findings.append((number, 'privileged-workflow-trigger'))
        match = re.match(r'^\s*(?:-\s*)?uses:\s*[\"\']?([^\s\"\']+)', code)
        if match and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}', match.group(1)):
            findings.append((number, 'unpinned-action'))
        if re.search(r'\b(?:write-all|self-hosted)\b', code):
            findings.append((number, 'privileged-workflow-setting'))
        if re.search(r'^\s*(?:contents|actions|id-token|packages|pull-requests|security-events):\s*write\b', code):
            findings.append((number, 'write-token-permission'))
        if re.search(r'persist-credentials:\s*true\b', code):
            findings.append((number, 'persisted-checkout-credential'))
    if not re.search(r'(?m)^permissions:\s*\n\s+contents:\s*read\s*$', text):
        findings.append((1, 'explicit-readonly-permissions-required'))
    return sorted(set(findings))


def inspect_text(text: str) -> list[tuple[int, str]]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for rule, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append((number, rule))
    return findings


def scan(root: Path) -> list[str]:
    """Scan repository text and runtime Python; do not follow symlinks."""
    root = root.resolve()
    findings = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in IGNORE_DIRS or part.endswith('.egg-info') for part in relative.parts):
            continue
        if path.is_symlink():
            findings.append(f'{relative}:1: symlink-requires-review')
            continue
        if not path.is_file():
            continue
        if path.name == '.env' or path.name.startswith('.env.') and path.name != '.env.example':
            findings.append(f'{relative}:1: environment-file')
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {'Dockerfile', 'Makefile', 'LICENSE', '.gitignore'}:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            findings.append(f'{relative}:1: text-file-too-large')
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            findings.append(f'{relative}:1: unreadable-text-file')
            continue
        found = inspect_text(content)
        if relative.parts[0] == 'src' and path.suffix == '.py':
            found += inspect_python(content)
        if relative.parts[:2] == ('.github', 'workflows') and path.suffix in {'.yml', '.yaml'}:
            found += inspect_workflow(content)
        findings.extend(f'{relative}:{line}: {rule}' for line, rule in sorted(set(found)))
    return findings


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        print('Repository directory does not exist.', file=sys.stderr)
        return 2
    findings = scan(root)
    for finding in findings:
        print(finding)
    print(f'Repository policy check: {len(findings)} finding(s). This is not a complete security audit.')
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
