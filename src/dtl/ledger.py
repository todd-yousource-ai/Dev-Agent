#!/usr/bin/env python3
"""
Create or update a descriptive GitHub README based on documents in a local doc repository.

Security assumptions:
- Operates only on a local filesystem path explicitly provided by the caller.
- Refuses to follow symlinks while scanning repository content to reduce path traversal risk.
- Treats all source documents as untrusted input and performs only plain-text parsing.
- Limits file size and file count processed to bound memory and runtime.

Failure behavior:
- Raises ValueError for invalid inputs or unsafe paths.
- Raises FileNotFoundError when the repository or documents directory is missing.
- Raises RuntimeError when insufficient source material exists to generate a README.
- Writes README atomically via temp-file replacement to avoid partial corruption.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


MAX_FILES = 500
MAX_FILE_BYTES = 512 * 1024
ALLOWED_SUFFIXES = {".md", ".txt", ".rst"}


@dataclass(frozen=True)
class DocSection:
    """
    Parsed document fragment used for README synthesis.

    Security assumptions:
    - title and body originate from untrusted local files and must be treated as data only.
    - path is normalized and must remain within the provided repository root.

    Failure behavior:
    - Instances are immutable; invalid construction should be prevented by caller validation.
    """

    source_id: str
    section_title: str
    body: str
    path: Path


def _safe_resolve(path: Path) -> Path:
    """
    Resolve a path without allowing missing-path ambiguity.

    Security assumptions:
    - Caller provides a local filesystem path.
    - Returned path is canonicalized for containment checks.

    Failure behavior:
    - Raises FileNotFoundError if the path does not exist.
    - Propagates OSError for underlying filesystem failures.
    """
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return path.resolve(strict=True)


def _ensure_within(root: Path, candidate: Path) -> None:
    """
    Enforce that candidate is contained within root.

    Security assumptions:
    - Both paths are resolved absolute paths.

    Failure behavior:
    - Raises ValueError if candidate escapes root.
    """
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Unsafe path outside repository root: {candidate}") from exc


def _iter_doc_files(repo_root: Path) -> List[Path]:
    """
    Enumerate documentation-like files under the repository root.

    Security assumptions:
    - Refuses symlinked files and directories to reduce traversal risk.
    - Limits total scanned files and accepted file sizes.

    Failure behavior:
    - Raises RuntimeError if too many files are encountered.
    - Raises FileNotFoundError if no documentation files are found.
    """
    results: List[Path] = []
    seen = 0

    for current_root, dirnames, filenames in os.walk(repo_root, topdown=True, followlinks=False):
        root_path = Path(current_root)

        filtered_dirs = []
        for d in dirnames:
            p = root_path / d
            if p.is_symlink():
                continue
            if d.startswith(".git"):
                continue
            if d in {"node_modules", "dist", "build", "__pycache__", ".venv", "venv"}:
                continue
            filtered_dirs.append(d)
        dirnames[:] = filtered_dirs

        for name in filenames:
            seen += 1
            if seen > MAX_FILES * 20:
                raise RuntimeError("Repository scan aborted: excessive file count")
            p = root_path / name
            if p.is_symlink():
                continue
            if p.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            rel = p.relative_to(repo_root)
            rel_parts_lower = {part.lower() for part in rel.parts}
            if ".git" in rel_parts_lower:
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            results.append(p)
            if len(results) >= MAX_FILES:
                break
        if len(results) >= MAX_FILES:
            break

    if not results:
        raise FileNotFoundError("No documentation files found in repository")
    return sorted(results)


def _read_text(path: Path) -> str:
    """
    Read a small text file safely.

    Security assumptions:
    - File size has already been bounded by caller.
    - Content is treated as untrusted text.

    Failure behavior:
    - Returns best-effort UTF-8 decoded content with replacement on decode errors.
    - Propagates OSError for unreadable files.
    """
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"File too large: {path}")
    return data.decode("utf-8", errors="replace")


def _extract_sections(path: Path, text: str) -> List[DocSection]:
    """
    Parse lightweight markdown-like sections from a document.

    Security assumptions:
    - Input text is untrusted and parsed only via simple regex/tokenization.
    - No code execution or external rendering occurs.

    Failure behavior:
    - Returns at least one fallback section if text contains non-empty content.
    """
    lines = text.splitlines()
    sections: List[DocSection] = []

    source_id = path.stem
    current_title: Optional[str] = None
    current_body: List[str] = []

    heading_re = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")

    for line in lines:
        m = heading_re.match(line)
        if m:
            if current_title is not None:
                body = "\n".join(current_body).strip()
                if body:
                    sections.append(
                        DocSection(
                            source_id=source_id,
                            section_title=current_title,
                            body=body,
                            path=path,
                        )
                    )
            current_title = m.group(2).strip()
            current_body = []
        else:
            if current_title is not None:
                current_body.append(line)

    if current_title is not None:
        body = "\n".join(current_body).strip()
        if body:
            sections.append(
                DocSection(
                    source_id=source_id,
                    section_title=current_title,
                    body=body,
                    path=path,
                )
            )

    if not sections:
        cleaned = text.strip()
        if cleaned:
            first_para = cleaned.split("\n\n", 1)[0].strip()
            sections.append(
                DocSection(
                    source_id=source_id,
                    section_title=path.stem.replace("_", " ").replace("-", " ").title(),
                    body=first_para,
                    path=path,
                )
            )
    return sections


def _first_meaningful_sentence(text: str, limit: int = 260) -> str:
    """
    Extract a concise summary sentence from untrusted text.

    Security assumptions:
    - Performs plain string cleanup only.
    - Output remains inert markdown text.

    Failure behavior:
    - Returns a truncated cleaned snippet if sentence boundaries are absent.
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"`{1,3}.*?`{1,3}", "", cleaned)
    cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    sentence = parts[0].strip() if parts else cleaned
    if len(sentence) > limit:
        sentence = sentence[: limit - 3].rstrip() + "..."
    return sentence


def _choose_project_title(repo_root: Path, sections: Sequence[DocSection]) -> str:
    """
    Determine a human-readable project title.

    Security assumptions:
    - Uses repository name and document headings as untrusted text only.

    Failure behavior:
    - Falls back to repository directory name when no better title is available.
    """
    for sec in sections:
        title = sec.section_title.lower()
        if "purpose and scope" in title:
            sentence = _first_meaningful_sentence(sec.body, 120)
            if sentence:
                m = re.search(r"\bfor\s+the\s+([A-Z][A-Za-z0-9 \-]+)", sentence)
                if m:
                    return m.group(1).strip()
    return repo_root.name.replace("_", " ").replace("-", " ").title()


def _select_overview(sections: Sequence[DocSection]) -> str:
    """
    Build an overview paragraph from the strongest matching sections.

    Security assumptions:
    - Uses static keyword matching only.
    - Produces inert markdown text.

    Failure behavior:
    - Returns a generic overview if no suitable sections are found.
    """
    preferred = []
    keywords = (
        "purpose and scope",
        "repository bootstrap",
        "repository operations",
        "github commit",
        "architecture",
    )
    for sec in sections:
        title_l = sec.section_title.lower()
        if any(k in title_l for k in keywords):
            s = _first_meaningful_sentence(sec.body)
            if s:
                preferred.append(s)
    if preferred:
        overview = " ".join(dict.fromkeys(preferred))
        return overview[:800].rstrip()
    return (
        "This repository contains project documentation and technical requirements. "
        "The README was generated from the available source documents to provide a clearer "
        "entry point for contributors and stakeholders."
    )


def _collect_capabilities(sections: Sequence[DocSection]) -> List[str]:
    """
    Infer key capabilities or repository concerns from source sections.

    Security assumptions:
    - Heuristic extraction from untrusted text; no external data sources.

    Failure behavior:
    - Returns a non-empty default list when specific capabilities are not found.
    """
    bullets: List[str] = []
    keyword_map = [
        ("authentication", "Authentication support for GitHub access, including PAT and GitHub App installation-token flows."),
        ("githubtool", "A single GitHub integration surface through which repository operations are expected to flow."),
        ("commit", "File commit and repository update workflows for automated changes."),
        ("repository operations", "Repository lifecycle and operational patterns for interacting with project contents."),
        ("mock github", "Mock GitHub behavior for local and test validation."),
        ("secrets", "Required secret and credential handling considerations for CI and automation."),
        ("multi-agent", "Coordination artifacts that enable work sharing across multiple agents or contributors."),
        ("journal", "Persistent journal or trace artifacts stored alongside pull requests or repository files."),
        ("ci", "Continuous integration and runner-related requirements tied to repository workflows."),
    ]
    haystack = "\n".join(
        f"{s.source_id}\n{s.section_title}\n{s.body}" for s in sections
    ).lower()

    for key, bullet in keyword_map:
        if key in haystack:
            bullets.append(bullet)

    if not bullets:
        bullets = [
            "Technical requirement documents that describe repository behavior and integration expectations.",
            "Documentation intended to support implementation, operations, and contributor onboarding.",
        ]
    return list(dict.fromkeys(bullets))[:8]


def _collect_document_index(repo_root: Path, files: Sequence[Path], sections: Sequence[DocSection]) -> List[Tuple[str, str, str]]:
    """
    Build a document index for the README.

    Security assumptions:
    - Paths are rendered relative to the repository root only after containment validation.

    Failure behavior:
    - Skips files that cannot be represented safely relative to root.
    """
    by_file_summary = {}
    for sec in sections:
        rel = sec.path.relative_to(repo_root).as_posix()
        by_file_summary.setdefault(rel, _first_meaningful_sentence(sec.body, 180))

    index: List[Tuple[str, str, str]] = []
    for path in files:
        rel_path = path.relative_to(repo_root).as_posix()
        title = path.stem.replace("_", " ").replace("-", " ").title()
        summary = by_file_summary.get(rel_path, "")
        index.append((title, rel_path, summary))
    return index[:20]


def _render_readme(repo_root: Path, sections: Sequence[DocSection], files: Sequence[Path]) -> str:
    """
    Render the final README markdown.

    Security assumptions:
    - Output is plain markdown composed from sanitized text snippets.
    - No HTML injection protections are guaranteed beyond simple text normalization.

    Failure behavior:
    - Raises RuntimeError if there is insufficient content to create a meaningful README.
    """
    if not sections:
        raise RuntimeError("Insufficient document content to generate README")

    title = _choose_project_title(repo_root, sections)
    overview = _select_overview(sections)
    capabilities = _collect_capabilities(sections)
    index = _collect_document_index(repo_root, files, sections)

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(overview)
    lines.append("")
    lines.append("## What this repository contains")
    lines.append("")
    for bullet in capabilities:
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("## Documentation map")
    lines.append("")
    for doc_title, rel_path, summary in index:
        if summary:
            lines.append(f"- **{doc_title}** (`{rel_path}`): {summary}")
        else:
            lines.append(f"- **{doc_title}** (`{rel_path}`)")
    lines.append("")
    lines.append("## How to use this repository")
    lines.append("")
    lines.append("- Start with the high-level purpose and scope documents to understand the intended system behavior.")
    lines.append("- Review repository and commit workflow requirements before making automated or manual changes.")
    lines.append("- Use CI, secrets, and testing documents to validate environment expectations and safe execution paths.")
    lines.append("")
    lines.append("## Contributing")
    lines.append("")
    lines.append("- Keep documentation changes aligned with the technical requirements already captured in this repository.")
    lines.append("- Prefer updating source requirement documents first, then refresh this README so summaries remain accurate.")
    lines.append("- Validate that repository operations, authentication assumptions, and testing guidance remain consistent.")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("This README is intended to provide a descriptive entry point generated from the documentation currently present in the repository.")
    lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    """
    Atomically write content to a target file.

    Security assumptions:
    - Target directory is trusted and writable by the current process.
    - Atomic replace semantics depend on local filesystem guarantees.

    Failure behavior:
    - Raises OSError on write or replace failure.
    - Avoids partial file content by writing to a temporary file first.
    """
    parent = path.parent
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=parent, delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name
    os.replace(temp_name, path)


def generate_readme(repo_root: Path, output_path: Optional[Path] = None) -> Path:
    """
    Generate a descriptive README for a documentation repository.

    Security assumptions:
    - repo_root must be a local directory under caller control.
    - Only documentation-like files are scanned; symlinks are excluded.
    - Output defaults to README.md in the repository root.

    Failure behavior:
    - Raises FileNotFoundError, ValueError, RuntimeError, or OSError on invalid input or IO failure.
    - Returns the written README path on success.
    """
    repo_root = _safe_resolve(repo_root)
    if not repo_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo_root}")

    files = _iter_doc_files(repo_root)
    sections: List[DocSection] = []
    for path in files:
        resolved = _safe_resolve(path)
        _ensure_within(repo_root, resolved)
        text = _read_text(resolved)
        sections.extend(_extract_sections(resolved, text))

    if not sections:
        raise RuntimeError("No usable document sections found for README generation")

    target = output_path or (repo_root / "README.md")
    target_parent = target.parent if target.is_absolute() else repo_root
    if target.is_absolute():
        target_parent = _safe_resolve(target.parent)
        _ensure_within(repo_root, target_parent)
    else:
        target = repo_root / target
        _ensure_within(repo_root, target.resolve(strict=False))

    content = _render_readme(repo_root, sections, files)
    _atomic_write(target, content)
    return target


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    CLI entrypoint.

    Security assumptions:
    - Arguments are untrusted and validated before filesystem access.
    - Writes only within the target repository root.

    Failure behavior:
    - Returns non-zero exit code on any validation or generation failure.
    - Prints minimal error details to stderr.
    """
    parser = argparse.ArgumentParser(description="Generate a descriptive README from repository docs.")
    parser.add_argument("repo_root", help="Path to the documentation repository")
    parser.add_argument("--output", help="Optional output path relative to the repository root", default=None)
    args = parser.parse_args(argv)

    try:
        repo_root = Path(args.repo_root)
        output = Path(args.output) if args.output else None
        written = generate_readme(repo_root, output)
        sys.stdout.write(str(written) + "\n")
        return 0
    except Exception as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())