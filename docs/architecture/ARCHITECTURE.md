"""Tests for foundation standards documents."""

import re
from pathlib import Path

import pytest

# Resolve project root by walking up from this file until we find pyproject.toml
PROJECT_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()
)

DOCS_DIR = PROJECT_ROOT / "docs" / "architecture"

EXPECTED_DOCS = {
    "ARCHITECTURE.md",
    "INTERFACES.md",
    "CONVENTIONS.md",
    "SOURCE_OF_TRUTH.md",
    "VERSIONING.md",
}


def read_doc(name: str) -> str:
    """Read a document from the architecture docs directory."""
    path = DOCS_DIR / name
    assert path.exists(), f"{name} does not exist at {path}"
    content = path.read_text(encoding="utf-8")
    return content


def all_doc_contents():
    """Yield (name, content) for each expected doc that exists."""
    for name in EXPECTED_DOCS:
        path = DOCS_DIR / name
        if path.exists():
            yield name, path.read_text(encoding="utf-8")


# ─── Existence and non-empty tests ───────────────────────────────────────────


class TestDocExistence:
    def test_architecture_md_exists_and_is_nonempty(self):
        content = read_doc("ARCHITECTURE.md")
        assert len(content.strip()) > 0, "ARCHITECTURE.md is empty"

    def test_interfaces_md_exists_and_is_nonempty(self):
        content = read_doc("INTERFACES.md")
        assert len(content.strip()) > 0, "INTERFACES.md is empty"

    def test_conventions_md_exists_and_is_nonempty(self):
        content = read_doc("CONVENTIONS.md")
        assert len(content.strip()) > 0, "CONVENTIONS.md is empty"

    def test_source_of_truth_md_exists_and_is_nonempty(self):
        content = read_doc("SOURCE_OF_TRUTH.md")
        assert len(content.strip()) > 0, "SOURCE_OF_TRUTH.md is empty"

    def test_versioning_md_exists_and_is_nonempty(self):
        content = read_doc("VERSIONING.md")
        assert len(content.strip()) > 0, "VERSIONING.md is empty"


# ─── Changelog section in all docs ──────────────────────────────────────────


class TestChangelogSection:
    @pytest.mark.parametrize("doc_name", sorted(EXPECTED_DOCS))
    def test_all_docs_contain_changelog_section(self, doc_name):
        content = read_doc(doc_name)
        # Look for a heading containing "changelog" (case-insensitive)
        assert re.search(
            r"^#{1,6}\s+.*changelog.*$", content, re.IGNORECASE | re.MULTILINE
        ), f"{doc_name} missing a Changelog section heading"


# ─── ARCHITECTURE.md specific content ────────────────────────────────────────


class TestArchitectureContent:
    def test_architecture_contains_two_process_model_section(self):
        content = read_doc("ARCHITECTURE.md")
        assert re.search(
            r"two.process|2.process", content, re.IGNORECASE
        ), "ARCHITECTURE.md should describe the two-process model"

    def test_architecture_contains_swift_shell_and_python_backend_ownership(self):
        content = read_doc("ARCHITECTURE.md")
        content_lower = content.lower()
        assert "swift" in content_lower, "ARCHITECTURE.md should mention Swift shell"
        assert "python" in content_lower, "ARCHITECTURE.md should mention Python backend"


# ─── INTERFACES.md specific content ─────────────────────────────────────────


class TestInterfacesContent:
    def test_interfaces_contains_envelope_schema_section(self):
        content = read_doc("INTERFACES.md")
        assert re.search(
            r"envelope.*schema|schema.*envelope", content, re.IGNORECASE
        ), "INTERFACES.md should contain an envelope schema section"

    def test_interfaces_defines_required_envelope_fields(self):
        content = read_doc("INTERFACES.md")
        required_fields = [
            "version",
            "message_type",
            "message_id",
            "timestamp",
            "direction",
            "payload",
            "error",
        ]
        content_lower = content.lower()
        for field in required_fields:
            assert (
                field in content_lower
            ), f"INTERFACES.md missing required envelope field: {field}"


# ─── CONVENTIONS.md specific content ─────────────────────────────────────────


class TestConventionsContent:
    def test_conventions_contains_branch_naming_section(self):
        content = read_doc("CONVENTIONS.md")
        assert re.search(
            r"branch.naming|naming.*branch", content, re.IGNORECASE
        ), "CONVENTIONS.md should have a branch naming section"

    def test_conventions_defines_crafted_agent_build_slug_pattern(self):
        content = read_doc("CONVENTIONS.md")
        # Should define a pattern like crafted-agent-build/<slug> or similar
        assert re.search(
            r"crafted.agent.build", content, re.IGNORECASE
        ), "CONVENTIONS.md should define crafted-agent-build slug pattern"


# ─── SOURCE_OF_TRUTH.md specific content ────────────────────────────────────


class TestSourceOfTruthContent:
    def test_source_of_truth_contains_document_hierarchy_section(self):
        content = read_doc("SOURCE_OF_TRUTH.md")
        assert re.search(
            r"hierarchy|precedence|authority", content, re.IGNORECASE
        ), "SOURCE_OF_TRUTH.md should describe document hierarchy"

    def test_source_of_truth_defines_precedence_with_trds_authoritative(self):
        content = read_doc("SOURCE_OF_TRUTH.md")
        content_lower = content.lower()
        assert "trd" in content_lower, "SOURCE_OF_TRUTH.md should reference TRDs"
        # TRDs should be described as authoritative
        assert re.search(
            r"trd.*authoritat|authoritat.*trd", content_lower
        ), "SOURCE_OF_TRUTH.md should establish TRDs as authoritative"


# ─── VERSIONING.md specific content ─────────────────────────────────────────


class TestVersioningContent:
    def test_versioning_contains_semver_rules_section(self):
        content = read_doc("VERSIONING.md")
        assert re.search(
            r"semver|semantic.version", content, re.IGNORECASE
        ), "VERSIONING.md should contain semver rules"

    def test_versioning_contains_propagation_targets_section(self):
        content = read_doc("VERSIONING.md")
        assert re.search(
            r"propagat", content, re.IGNORECASE
        ), "VERSIONING.md should describe propagation targets"


# ─── Cross-document link integrity ──────────────────────────────────────────


class TestCrossDocLinks:
    def test_no_broken_relative_links_between_docs(self):
        """All relative markdown links within the docs should resolve to existing files."""
        md_link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
        broken_links = []

        for name in EXPECTED_DOCS:
            path = DOCS_DIR / name
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            for match in md_link_pattern.finditer(content):
                link_text, link_target = match.group(1), match.group(2)
                # Skip external URLs, anchors-only, and mailto
                if link_target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                # Strip any anchor from the link
                file_part = link_target.split("#")[0]
                if not file_part:
                    continue
                resolved = (DOCS_DIR / file_part).resolve()
                if not resolved.exists():
                    broken_links.append(f"{name}: [{link_text}]({link_target})")

        assert (
            not broken_links
        ), f"Broken relative links found:\n" + "\n".join(broken_links)


# ─── H1 title as first line ─────────────────────────────────────────────────


class TestDocStructure:
    @pytest.mark.parametrize("doc_name", sorted(EXPECTED_DOCS))
    def test_all_docs_use_h1_title_as_first_line(self, doc_name):
        content = read_doc(doc_name)
        first_line = content.strip().split("\n")[0].strip()
        assert first_line.startswith(
            "# "
        ), f"{doc_name} first line should be an H1 heading, got: {first_line!r}"


# ─── Negative cases ─────────────────────────────────────────────────────────


class TestNegativeCases:
    @pytest.mark.parametrize("doc_name", sorted(EXPECTED_DOCS))
    def test_no_document_exceeds_reasonable_size_limit_50kb(self, doc_name):
        path = DOCS_DIR / doc_name
        if not path.exists():
            pytest.skip(f"{doc_name} does not exist")
        size = path.stat().st_size
        max_size = 50 * 1024  # 50 KB
        assert (
            size <= max_size
        ), f"{doc_name} is {size} bytes, exceeding 50KB limit"

    @pytest.mark.parametrize("doc_name", sorted(EXPECTED_DOCS))
    def test_no_document_contains_placeholder_todo_markers(self, doc_name):
        content = read_doc(doc_name)
        placeholder_patterns = [
            r"\bTODO\b",
            r"\bFIXME\b",
            r"\bTBD\b",
            r"\bPLACEHOLDER\b",
        ]
        for pattern in placeholder_patterns:
            matches = re.findall(pattern, content)
            assert (
                not matches
            ), f"{doc_name} contains placeholder marker: {pattern} ({len(matches)} occurrence(s))"

    @pytest.mark.parametrize("doc_name", sorted(EXPECTED_DOCS))
    def test_no_document_contains_bare_urls_without_context(self, doc_name):
        content = read_doc(doc_name)
        # Find bare URLs that are NOT inside markdown link syntax [text](url)
        # or inside angle brackets <url> or inside code blocks
        lines = content.split("\n")
        in_code_block = False
        bare_urls = []
        for line_no, line in enumerate(lines, 1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            # Find all URLs in the line
            url_matches = list(re.finditer(r"https?://\S+", line))
            for m in url_matches:
                start = m.start()
                # Check if preceded by ]( -- markdown link
                prefix = line[:start]
                if prefix.endswith("]("):
                    continue
                # Check if inside angle brackets
                if start > 0 and line[start - 1] == "<":
                    continue
                # Check if inside inline code
                backtick_count = prefix.count("`")
                if backtick_count % 2 == 1:
                    continue
                bare_urls.append(f"  line {line_no}: {m.group()}")

        assert not bare_urls, (
            f"{doc_name} contains bare URLs (should use markdown link syntax):\n"
            + "\n".join(bare_urls)
        )

    def test_source_of_truth_precedence_does_not_contradict_trd_authority(self):
        """Verify TRDs in forge-docs/ are not subordinated to any other document class for product behavior."""
        content = read_doc("SOURCE_OF_TRUTH.md")
        content_lower = content.lower()
        # TRDs should be authoritative for product behavior
        assert "trd" in content_lower, "SOURCE_OF_TRUTH.md must reference TRDs"
        # Ensure TRDs are not described as subordinate
        subordination_patterns = [
            r"trd.*(?:subordinate|overridden by|superseded by|less authoritative)",
            r"(?:override|supersede|take precedence over).*trd",
        ]
        for pattern in subordination_patterns:
            match = re.search(pattern, content_lower)
            assert (
                match is None
            ), f"SOURCE_OF_TRUTH.md appears to subordinate TRDs: {match.group()!r}"


# ─── Security cases ─────────────────────────────────────────────────────────


class TestSecurityCases:
    SECRET_PATTERNS = [
        # API keys with common prefixes
        (r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", "API key"),
        # Generic tokens
        (r"(?:token|secret|password|passwd|pwd)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}", "token/secret/password"),
        # AWS keys
        (r"AKIA[0-9A-Z]{16}", "AWS access key"),
        # Private key material
        (r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----", "private key"),
        # GitHub tokens
        (r"gh[pousr]_[A-Za-z0-9_]{36,}", "GitHub token"),
        # Generic bearer tokens
        (r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", "Bearer token"),
        # Base64-encoded secrets that are suspiciously long (potential credentials)
        (r"(?:secret|key|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9+/]{40,}={0,2}", "base64 secret"),
    ]

    @pytest.mark.parametrize("doc_name", sorted(EXPECTED_DOCS))
    def test_no_document_contains_secrets_or_tokens(self, doc_name):
        content = read_doc(doc_name)
        found_secrets = []
        for pattern, description in self.SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Filter out obvious examples/documentation references
                real_matches = [
                    m
                    for m in matches
                    if not any(
                        ex in m.lower()
                        for ex in ["example", "your_", "xxx", "placeholder", "<"]
                    )
                ]
                if real_matches:
                    found_secrets.append(
                        f"  {description}: {len(real_matches)} match(es)"
                    )

        assert not found_secrets, (
            f"{doc_name} appears to contain secrets:\n" + "\n".join(found_secrets)
        )
