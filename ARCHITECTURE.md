"""Tests for forge-standards documents (ARCHITECTURE, INTERFACES, DECISIONS, CONVENTIONS)."""

import re
from pathlib import Path

import pytest

# Resolve project root by walking up from this file to find pyproject.toml
PROJECT_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()
)

FORGE_DOCS = {
    "ARCHITECTURE.md": PROJECT_ROOT / "ARCHITECTURE.md",
    "INTERFACES.md": PROJECT_ROOT / "INTERFACES.md",
    "DECISIONS.md": PROJECT_ROOT / "DECISIONS.md",
    "CONVENTIONS.md": PROJECT_ROOT / "CONVENTIONS.md",
}


def _read_doc(name: str) -> str:
    path = FORGE_DOCS[name]
    assert path.exists(), f"{name} does not exist at {path}"
    content = path.read_text(encoding="utf-8")
    return content


def _read_lines(name: str) -> list[str]:
    return _read_doc(name).splitlines()


# ── Existence and non-emptiness ──────────────────────────────────────────


class TestDocExistence:
    def test_architecture_md_exists_and_is_nonempty(self):
        content = _read_doc("ARCHITECTURE.md")
        assert len(content.strip()) > 0, "ARCHITECTURE.md is empty"

    def test_interfaces_md_exists_and_is_nonempty(self):
        content = _read_doc("INTERFACES.md")
        assert len(content.strip()) > 0, "INTERFACES.md is empty"

    def test_decisions_md_exists_and_is_nonempty(self):
        content = _read_doc("DECISIONS.md")
        assert len(content.strip()) > 0, "DECISIONS.md is empty"

    def test_conventions_md_exists_and_is_nonempty(self):
        content = _read_doc("CONVENTIONS.md")
        assert len(content.strip()) > 0, "CONVENTIONS.md is empty"


# ── Required sections ────────────────────────────────────────────────────


class TestArchitectureSections:
    REQUIRED_SECTIONS = [
        "Two-Process Architecture",
        "Swift Shell",
        "Python Backend",
        "Inter-Process Communication",
        "Security Boundaries",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_architecture_md_contains_required_sections(self, section: str):
        content = _read_doc("ARCHITECTURE.md")
        # Case-insensitive search for the section heading (allow flexible heading level)
        pattern = re.compile(rf"^#+\s*{re.escape(section)}", re.IGNORECASE | re.MULTILINE)
        assert pattern.search(content), (
            f"ARCHITECTURE.md is missing required section: '{section}'"
        )


class TestInterfacesSections:
    REQUIRED_SECTIONS = [
        "IPC Protocol",
        "GitHub API Surface",
        "LLM Provider Abstraction",
        "CI Runner Contract",
        "Keychain and Secrets Interface",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_interfaces_md_contains_required_interface_sections(self, section: str):
        content = _read_doc("INTERFACES.md")
        pattern = re.compile(rf"^#+\s*{re.escape(section)}", re.IGNORECASE | re.MULTILINE)
        assert pattern.search(content), (
            f"INTERFACES.md is missing required section: '{section}'"
        )


class TestDecisionsMd:
    def test_decisions_md_contains_adr_001(self):
        content = _read_doc("DECISIONS.md")
        assert re.search(r"ADR[- ]?001", content, re.IGNORECASE), (
            "DECISIONS.md does not contain ADR-001"
        )

    @pytest.mark.parametrize("field", ["status", "context", "decision", "consequences"])
    def test_decisions_md_adr_001_has_required_fields(self, field: str):
        content = _read_doc("DECISIONS.md")
        # The field should appear (case-insensitive) as a heading or bold label
        pattern = re.compile(
            rf"(^#+\s*{re.escape(field)}|\*\*{re.escape(field)}\*\*|^{re.escape(field)}\s*:)",
            re.IGNORECASE | re.MULTILINE,
        )
        assert pattern.search(content), (
            f"DECISIONS.md ADR-001 is missing required field: '{field}'"
        )


class TestConventionsSections:
    REQUIRED_SECTIONS = [
        "Python Conventions",
        "Swift Conventions",
        "File Layout",
        "Commit Messages",
        "Branch Naming",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_conventions_md_contains_required_sections(self, section: str):
        content = _read_doc("CONVENTIONS.md")
        pattern = re.compile(rf"^#+\s*{re.escape(section)}", re.IGNORECASE | re.MULTILINE)
        assert pattern.search(content), (
            f"CONVENTIONS.md is missing required section: '{section}'"
        )


# ── H1 titles ────────────────────────────────────────────────────────────


class TestH1Titles:
    @pytest.mark.parametrize("doc_name", list(FORGE_DOCS.keys()))
    def test_all_forge_docs_have_h1_title(self, doc_name: str):
        content = _read_doc(doc_name)
        h1_pattern = re.compile(r"^#\s+\S", re.MULTILINE)
        assert h1_pattern.search(content), (
            f"{doc_name} does not have an H1 (# Title) heading"
        )


# ── TODO without issue link ──────────────────────────────────────────────


class TestTodoLinks:
    @pytest.mark.parametrize("doc_name", list(FORGE_DOCS.keys()))
    def test_no_forge_doc_contains_todo_without_issue_link(self, doc_name: str):
        content = _read_doc(doc_name)
        # Find all TODO occurrences
        todo_pattern = re.compile(r"TODO", re.IGNORECASE)
        for match in todo_pattern.finditer(content):
            # Check that within 200 chars after TODO there is a link or issue ref
            context = content[match.start() : match.start() + 200]
            has_link = re.search(r"https?://|#\d+|\[.*?\]\(.*?\)", context)
            assert has_link, (
                f"{doc_name} contains a TODO without an issue link near position {match.start()}: "
                f"'{context[:80]}...'"
            )


# ── Negative cases ───────────────────────────────────────────────────────


class TestNegativeCases:
    def test_architecture_md_does_not_contain_runnable_code_blocks(self):
        """No ```python or ```swift blocks with executable logic."""
        content = _read_doc("ARCHITECTURE.md")
        # Find all fenced code blocks with python or swift language tags
        code_block_pattern = re.compile(
            r"```(?:python|swift)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE
        )
        for match in code_block_pattern.finditer(content):
            block = match.group(1).strip()
            # Executable logic indicators: function definitions, class definitions,
            # import statements, actual code that could run
            executable_patterns = [
                r"^\s*def\s+\w+\s*\(",
                r"^\s*class\s+\w+",
                r"^\s*import\s+\w+",
                r"^\s*from\s+\w+\s+import",
                r"^\s*func\s+\w+\s*\(",
                r"^\s*@main",
                r"if\s+__name__\s*==",
            ]
            for ep in executable_patterns:
                assert not re.search(ep, block, re.MULTILINE), (
                    f"ARCHITECTURE.md contains executable code in a fenced block: "
                    f"matched pattern '{ep}' in block starting with: '{block[:80]}...'"
                )

    @pytest.mark.parametrize("doc_name", list(FORGE_DOCS.keys()))
    def test_no_forge_doc_exceeds_reasonable_length(self, doc_name: str):
        lines = _read_lines(doc_name)
        assert len(lines) <= 500, (
            f"{doc_name} has {len(lines)} lines, exceeding the 500-line limit for focused content"
        )

    @pytest.mark.parametrize("doc_name", list(FORGE_DOCS.keys()))
    def test_no_broken_internal_links(self, doc_name: str):
        """Any markdown links to other forge-standards docs resolve to existing files."""
        content = _read_doc(doc_name)
        # Find markdown links: [text](target)
        link_pattern = re.compile(r"\[.*?\]\((.*?)\)")
        for match in link_pattern.finditer(content):
            target = match.group(1).strip()
            # Skip external URLs and anchors
            if target.startswith("http://") or target.startswith("https://"):
                continue
            if target.startswith("#"):
                continue
            # Strip anchors from file paths
            file_target = target.split("#")[0]
            if not file_target:
                continue
            # Only check links to markdown files that look like internal docs
            resolved = PROJECT_ROOT / file_target
            assert resolved.exists(), (
                f"{doc_name} contains a broken internal link: '{target}' "
                f"(resolved to {resolved})"
            )


class TestTerminologyConsistency:
    """Key subsystem terms used consistently across all documents."""

    # Define canonical terms and their incorrect variants
    TERM_CHECKS = [
        # (canonical_pattern, anti_patterns_description, anti_pattern_regex)
        (
            "Swift [Ss]hell",
            "Should use 'Swift shell' or 'Swift Shell', not 'SwiftShell' or 'swift-shell'",
            [r"\bSwiftShell\b", r"\bswift-shell\b"],
        ),
        (
            "Python [Bb]ackend",
            "Should use 'Python backend' or 'Python Backend', not 'PythonBackend' or 'python-backend'",
            [r"\bPythonBackend\b", r"\bpython-backend\b"],
        ),
    ]

    @pytest.mark.parametrize("doc_name", list(FORGE_DOCS.keys()))
    def test_terminology_consistency_across_documents(self, doc_name: str):
        content = _read_doc(doc_name)
        for canonical, description, anti_patterns in self.TERM_CHECKS:
            for anti in anti_patterns:
                matches = re.findall(anti, content)
                assert not matches, (
                    f"{doc_name} uses inconsistent terminology: found '{matches[0]}'. "
                    f"{description}"
                )


# ── Security cases ───────────────────────────────────────────────────────


class TestSecurityGuidance:
    DANGEROUS_PATTERNS = [
        r"commit.*(?:api[_\s-]?key|token|secret|credential|password)",
        r"(?:api[_\s-]?key|token|secret|credential|password).*(?:in|to|into)\s+(?:source|repo|git|code)",
        r"store.*(?:secret|token|key|credential|password).*(?:in|inside)\s+(?:source|repo|code|git)",
        r"hardcod(?:e|ed|ing)\s+(?:secret|token|key|credential|password)",
        r"check\s*(?:in|into)\s+(?:secret|token|key|credential|password)",
    ]

    @pytest.mark.parametrize("doc_name", list(FORGE_DOCS.keys()))
    def test_no_document_instructs_storing_secrets_in_source_control(self, doc_name: str):
        content = _read_doc(doc_name).lower()
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            # If there's a match, check if it's in a "don't do this" context
            for match in matches:
                # Find the surrounding context
                idx = content.find(match)
                context_start = max(0, idx - 100)
                context = content[context_start : idx + len(match) + 100]
                # Acceptable if preceded by negation words
                negation_nearby = re.search(
                    r"(?:never|don'?t|do\s+not|must\s+not|avoid|prohibited|forbid|warning|danger|⚠️)",
                    context,
                    re.IGNORECASE,
                )
                assert negation_nearby, (
                    f"{doc_name} appears to instruct storing secrets in source control "
                    f"without proper negation. Found: '...{context.strip()}...'"
                )
