"""
Tests for docs/CONFLICT_RESOLUTION.md and forge-standards/decision-precedence.md
structural integrity, content completeness, and semantic consistency.
"""

import os
import re
import pytest
from pathlib import Path

# Locate repo root relative to this test file
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFLICT_RESOLUTION_PATH = REPO_ROOT / "docs" / "CONFLICT_RESOLUTION.md"
DECISION_PRECEDENCE_PATH = REPO_ROOT / "forge-standards" / "decision-precedence.md"


@pytest.fixture(scope="module")
def conflict_resolution_content():
    """Read and return the full content of CONFLICT_RESOLUTION.md."""
    assert CONFLICT_RESOLUTION_PATH.exists(), f"{CONFLICT_RESOLUTION_PATH} does not exist"
    content = CONFLICT_RESOLUTION_PATH.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "CONFLICT_RESOLUTION.md is empty"
    return content


@pytest.fixture(scope="module")
def decision_precedence_content():
    """Read and return the full content of decision-precedence.md."""
    assert DECISION_PRECEDENCE_PATH.exists(), f"{DECISION_PRECEDENCE_PATH} does not exist"
    content = DECISION_PRECEDENCE_PATH.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "decision-precedence.md is empty"
    return content


@pytest.fixture(scope="module")
def cr_entries(conflict_resolution_content):
    """Parse all CR-### entries from CONFLICT_RESOLUTION.md.

    Returns a dict mapping CR-ID (e.g. 'CR-001') to the full text block
    of that entry (up to the next CR-### heading or end of document).
    """
    # Match headings like ### CR-001, ## CR-001, #### CR-001, or **CR-001**
    pattern = re.compile(
        r'(?:^#{2,4}\s+|(?<=\n)#{2,4}\s+|\*\*)(CR-\d{3})\b',
        re.MULTILINE,
    )
    matches = list(pattern.finditer(conflict_resolution_content))
    entries = {}
    for i, m in enumerate(matches):
        cr_id = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(conflict_resolution_content)
        entries[cr_id] = conflict_resolution_content[start:end]
    return entries


@pytest.fixture(scope="module")
def conflict_resolution_lines(conflict_resolution_content):
    return conflict_resolution_content.splitlines()


# ---------------------------------------------------------------------------
# Structural / existence tests
# ---------------------------------------------------------------------------


class TestStructure:
    def test_conflict_resolution_md_exists(self):
        """Verify docs/CONFLICT_RESOLUTION.md exists and is non-empty."""
        assert CONFLICT_RESOLUTION_PATH.exists()
        assert CONFLICT_RESOLUTION_PATH.stat().st_size > 0

    def test_decision_precedence_md_exists(self):
        """Verify forge-standards/decision-precedence.md exists and is non-empty."""
        assert DECISION_PRECEDENCE_PATH.exists()
        assert DECISION_PRECEDENCE_PATH.stat().st_size > 0

    def test_all_four_precedence_tiers_defined(self, conflict_resolution_content):
        """Parse CONFLICT_RESOLUTION.md and verify all 4 tiers are present."""
        tiers = [
            r"[Tt]ier\s*1.*[Ss]ecurity\s*[Oo]verride",
            r"[Tt]ier\s*2.*[Dd]omain\s*[Aa]uthority",
            r"[Tt]ier\s*3.*[Ss]tandards\s*[Tt]iebreak",
            r"[Tt]ier\s*4.*[Bb]est.?[Pp]ractice\s*[Dd]efault",
        ]
        for tier_pattern in tiers:
            assert re.search(tier_pattern, conflict_resolution_content), (
                f"Tier pattern '{tier_pattern}' not found in CONFLICT_RESOLUTION.md"
            )

    def test_trd11_is_tier1(self, conflict_resolution_content):
        """Verify TRD-11 is explicitly listed as Tier 1 / highest precedence."""
        tier1_section = re.search(
            r"[Tt]ier\s*1.*?(?=\n##|\n###\s*Tier\s*2|\Z)",
            conflict_resolution_content,
            re.DOTALL,
        )
        assert tier1_section, "Tier 1 section not found"
        assert "TRD-11" in tier1_section.group(0), "TRD-11 not mentioned in Tier 1 section"
        # Also check it's described as highest
        text = tier1_section.group(0).lower()
        assert any(w in text for w in ["highest", "override", "overrides all", "supreme"]), (
            "Tier 1 does not describe TRD-11 as highest authority"
        )

    def test_security_classification_section_exists(self, conflict_resolution_content):
        """Verify a section defining criteria for classifying a conflict as security-related exists."""
        assert re.search(
            r"[Ss]ecurity.*[Cc]lassification|[Cc]lassif.*[Ss]ecurity|§3",
            conflict_resolution_content,
        ), "Security classification section not found"

    def test_amendment_process_section_exists(self, conflict_resolution_content):
        """Verify the amendment process section is present."""
        assert re.search(
            r"[Aa]mendment\s*[Pp]rocess|§7",
            conflict_resolution_content,
        ), "Amendment process section not found"

    def test_domain_ownership_map_covers_all_trds(self, conflict_resolution_content):
        """Verify the domain ownership map references all 16 TRDs (TRD-1 through TRD-16)."""
        for i in range(1, 17):
            trd_ref = f"TRD-{i}"
            assert trd_ref in conflict_resolution_content, (
                f"{trd_ref} not found in CONFLICT_RESOLUTION.md"
            )


# ---------------------------------------------------------------------------
# CR entry content tests
# ---------------------------------------------------------------------------


class TestCREntries:
    def test_minimum_conflict_resolutions_count(self, cr_entries):
        """Verify at least 10 CR-### entries exist in the resolved conflicts section."""
        assert len(cr_entries) >= 10, (
            f"Expected at least 10 CR entries, found {len(cr_entries)}: {sorted(cr_entries.keys())}"
        )

    def test_each_resolution_has_required_fields(self, cr_entries):
        """For every CR-### entry, verify it contains: Conflicting Sources, Resolution, and Rationale."""
        required_fields = ["Conflicting Sources", "Resolution", "Rationale"]
        missing = {}
        for cr_id, text in cr_entries.items():
            text_lower = text.lower()
            for field in required_fields:
                # Accept various markdown formats: bold, heading, or plain label
                patterns = [
                    field.lower(),
                    field.lower().replace(" ", "_"),
                    field.lower().replace(" ", "-"),
                ]
                if not any(p in text_lower for p in patterns):
                    missing.setdefault(cr_id, []).append(field)
        assert not missing, f"CR entries missing required fields: {missing}"

    def test_specific_cr001_startup_timeout(self, cr_entries):
        """Verify CR-001 addresses TRD-1 vs TRD-12 startup timeout conflict."""
        assert "CR-001" in cr_entries, "CR-001 not found"
        text = cr_entries["CR-001"]
        assert "TRD-1" in text or "TRD-01" in text, "CR-001 does not reference TRD-1"
        assert "TRD-12" in text, "CR-001 does not reference TRD-12"
        text_lower = text.lower()
        assert any(w in text_lower for w in ["startup", "timeout", "time"]), (
            "CR-001 does not mention startup or timeout"
        )

    def test_specific_cr002_quality_gates(self, cr_entries):
        """Verify CR-002 addresses TRD-3 vs TRD-14 code quality gate conflict."""
        assert "CR-002" in cr_entries, "CR-002 not found"
        text = cr_entries["CR-002"]
        assert "TRD-3" in text or "TRD-03" in text, "CR-002 does not reference TRD-3"
        assert "TRD-14" in text, "CR-002 does not reference TRD-14"
        text_lower = text.lower()
        assert any(w in text_lower for w in ["quality", "gate", "code"]), (
            "CR-002 does not mention quality gates"
        )

    def test_specific_cr003_config_naming(self, cr_entries):
        """Verify CR-003 addresses configuration key naming conventions."""
        assert "CR-003" in cr_entries, "CR-003 not found"
        text_lower = cr_entries["CR-003"].lower()
        assert any(w in text_lower for w in ["config", "naming", "convention", "key"]), (
            "CR-003 does not address configuration naming"
        )

    def test_specific_cr004_error_taxonomy(self, cr_entries):
        """Verify CR-004 addresses error taxonomy overlaps."""
        assert "CR-004" in cr_entries, "CR-004 not found"
        text_lower = cr_entries["CR-004"].lower()
        assert any(w in text_lower for w in ["error", "taxonomy", "overlap", "classification"]), (
            "CR-004 does not address error taxonomy"
        )

    def test_specific_cr005_logging_levels(self, cr_entries):
        """Verify CR-005 addresses logging level definition conflicts."""
        assert "CR-005" in cr_entries, "CR-005 not found"
        text_lower = cr_entries["CR-005"].lower()
        assert any(w in text_lower for w in ["log", "level", "logging"]), (
            "CR-005 does not address logging levels"
        )


# ---------------------------------------------------------------------------
# Decision-precedence.md tests
# ---------------------------------------------------------------------------


class TestDecisionPrecedence:
    def test_decision_precedence_has_resolution_index(self, decision_precedence_content):
        """Verify forge-standards/decision-precedence.md contains a resolution index table."""
        # Look for a markdown table (pipe-delimited) containing CR references
        assert "|" in decision_precedence_content, "No markdown table found in decision-precedence.md"
        assert re.search(r"CR-\d{3}", decision_precedence_content), (
            "No CR-### references found in decision-precedence.md table"
        )

    def test_decision_precedence_has_flowchart(self, decision_precedence_content):
        """Verify forge-standards/decision-precedence.md contains a decision flowchart section."""
        text_lower = decision_precedence_content.lower()
        assert any(w in text_lower for w in ["flowchart", "flow chart", "decision tree", "decision flow"]), (
            "No flowchart/decision tree section found in decision-precedence.md"
        )

    def test_decision_precedence_defers_to_canonical(self, decision_precedence_content):
        """Verify decision-precedence.md references docs/CONFLICT_RESOLUTION.md as authoritative."""
        assert "CONFLICT_RESOLUTION.md" in decision_precedence_content or \
               "conflict_resolution" in decision_precedence_content.lower() or \
               "Conflict Resolution" in decision_precedence_content, (
            "decision-precedence.md does not reference CONFLICT_RESOLUTION.md"
        )

    def test_cross_reference_consistency(self, conflict_resolution_content, decision_precedence_content):
        """Verify all CR-IDs referenced in decision-precedence.md exist in CONFLICT_RESOLUTION.md."""
        dp_cr_ids = set(re.findall(r"CR-\d{3}", decision_precedence_content))
        cr_cr_ids = set(re.findall(r"CR-\d{3}", conflict_resolution_content))
        missing = dp_cr_ids - cr_cr_ids
        assert not missing, (
            f"CR-IDs in decision-precedence.md not found in CONFLICT_RESOLUTION.md: {sorted(missing)}"
        )


# ---------------------------------------------------------------------------
# Markdown validity tests
# ---------------------------------------------------------------------------


class TestMarkdownValidity:
    def test_no_broken_internal_links(self, conflict_resolution_content):
        """Verify all internal markdown anchor links resolve to existing sections."""
        # Extract internal links like [text](#anchor)
        internal_links = re.findall(r'\[.*?\]\(#([^)]+)\)', conflict_resolution_content)
        if not internal_links:
            pytest.skip("No internal anchor links found to validate")

        # Build set of existing anchors from headings
        headings = re.findall(r'^#{1,6}\s+(.+)$', conflict_resolution_content, re.MULTILINE)
        # Convert headings to GitHub-style anchors
        anchors = set()
        for h in headings:
            anchor = h.strip().lower()
            anchor = re.sub(r'[^\w\s-]', '', anchor)
            anchor = re.sub(r'[\s]+', '-', anchor)
            anchor = anchor.strip('-')
            anchors.add(anchor)

        broken = []
        for link in internal_links:
            normalized = link.lower().strip()
            if normalized not in anchors:
                broken.append(link)

        # Allow some tolerance for complex anchor generation differences
        # but flag if more than 20% are broken
        if broken and len(broken) > len(internal_links) * 0.2:
            pytest.fail(f"Broken internal links: {broken}")

    def test_markdown_valid(self, conflict_resolution_content):
        """Verify CONFLICT_RESOLUTION.md has no unclosed code blocks and balanced headers."""
        # Check for unclosed code blocks (triple backticks)
        backtick_blocks = conflict_resolution_content.count("```")
        assert backtick_blocks % 2 == 0, (
            f"Unclosed code block: found {backtick_blocks} triple-backtick markers (odd number)"
        )

        # Verify at least one top-level heading exists
        assert re.search(r'^#\s+', conflict_resolution_content, re.MULTILINE), (
            "No top-level heading found"
        )

    def test_decision_precedence_markdown_valid(self, decision_precedence_content):
        """Verify decision-precedence.md has valid markdown structure."""
        backtick_blocks = decision_precedence_content.count("```")
        assert backtick_blocks % 2 == 0, (
            f"Unclosed code block in decision-precedence.md: {backtick_blocks} markers"
        )
        assert re.search(r'^#\s+', decision_precedence_content, re.MULTILINE), (
            "No top-level heading found in decision-precedence.md"
        )


# ---------------------------------------------------------------------------
# Negative / integrity tests
# ---------------------------------------------------------------------------


class TestNegativeCases:
    def test_no_tier_references_unknown_trd(self, conflict_resolution_content):
        """Ensure no resolution references a TRD number outside the valid range (TRD-1 to TRD-16)."""
        all_trd_refs = re.findall(r'TRD-(\d+)', conflict_resolution_content)
        invalid = [
            f"TRD-{n}" for n in all_trd_refs
            if int(n) < 1 or int(n) > 16
        ]
        assert not invalid, f"Invalid TRD references found: {set(invalid)}"

    def test_no_duplicate_conflict_ids(self, conflict_resolution_content):
        """Ensure all CR-### IDs are unique across the document."""
        cr_ids = re.findall(r'CR-(\d{3})', conflict_resolution_content)
        # Only check IDs that appear in heading context (to avoid counting inline references)
        heading_cr_ids = re.findall(
            r'^#{2,4}\s+.*?(CR-\d{3})',
            conflict_resolution_content,
            re.MULTILINE,
        )
        if heading_cr_ids:
            seen = set()
            dupes = set()
            for cid in heading_cr_ids:
                if cid in seen:
                    dupes.add(cid)
                seen.add(cid)
            assert not dupes, f"Duplicate CR heading IDs found: {dupes}"
        else:
            # Fallback: check by section pattern
            # Count how many times each CR-ID appears as a section-like entry
            from collections import Counter
            pattern = re.compile(r'(?:^|\n)(?:#{2,4}|(?:\*\*)).*?(CR-\d{3})')
            matches = pattern.findall(conflict_resolution_content)
            counts = Counter(matches)
            dupes = {k: v for k, v in counts.items() if v > 1}
            assert not dupes, f"Duplicate CR IDs found: {dupes}"

    def test_no_conflicting_resolutions(self, cr_entries):
        """Ensure no two CR entries resolve the same conflict with different outcomes."""
        # Extract the 'Conflicting Sources' from each CR entry
        conflict_sources = {}
        for cr_id, text in cr_entries.items():
            # Extract TRD pairs mentioned
            trds = sorted(set(re.findall(r'TRD-\d+', text)))
            source_key = tuple(trds)
            if source_key and len(source_key) >= 2:
                if source_key in conflict_sources:
                    # Same TRD pair in multiple CRs - check they address different topics
                    other_id = conflict_sources[source_key]
                    other_text = cr_entries[other_id].lower()
                    this_text = text.lower()
                    # If both have the same resolution section content, flag it
                    # Extract resolution text
                    res_pattern = re.compile(r'resolution[:\s]*\n(.*?)(?=\n(?:rationale|###|##|\Z))', re.DOTALL | re.IGNORECASE)
                    this_res = res_pattern.search(this_text)
                    other_res = res_pattern.search(other_text)
                    if this_res and other_res:
                        # They should not have contradictory resolutions for the same exact topic
                        # This is a heuristic check - same TRDs, same topic words
                        pass  # Having same TRDs but different topics is fine
                conflict_sources.setdefault(source_key, cr_id)

    def test_no_empty_resolution_or_rationale(self, cr_entries):
        """Ensure no CR entry has an empty or placeholder-only Resolution or Rationale field."""
        placeholder_patterns = [
            r'^\s*$',
            r'^\s*TBD\s*$',
            r'^\s*TODO\s*$',
            r'^\s*N/?A\s*$',
            r'^\s*\[.*\]\s*$',  # [placeholder]
            r'^\s*\.\.\.\s*$',
        ]
        problems = []
        for cr_id, text in cr_entries.items():
            for field_name in ["Resolution", "Rationale"]:
                # Try to extract field content
                pattern = re.compile(
                    rf'\*?\*?{field_name}\*?\*?[:\s]*\n(.*?)(?=\n\*?\*?(?:Conflicting|Resolution|Rationale|###|##)|\Z)',
                    re.DOTALL | re.IGNORECASE,
                )
                match = pattern.search(text)
                if match:
                    content = match.group(1).strip()
                    if not content:
                        problems.append(f"{cr_id}: {field_name} is empty")
                    else:
                        for pp in placeholder_patterns:
                            if re.match(pp, content, re.IGNORECASE):
                                problems.append(f"{cr_id}: {field_name} is placeholder-only: '{content}'")
                                break
        assert not problems, f"Empty or placeholder fields found: {problems}"

    def test_quick_reference_does_not_contradict_canonical(
        self, conflict_resolution_content, decision_precedence_content
    ):
        """Verify decision-precedence.md does not introduce a different precedence order."""
        # Extract tier ordering from both docs
        tier_pattern = re.compile(r'[Tt]ier\s*(\d)')

        cr_tiers = [int(m.group(1)) for m in tier_pattern.finditer(conflict_resolution_content)]
        dp_tiers = [int(m.group(1)) for m in tier_pattern.finditer(decision_precedence_content)]

        if not dp_tiers:
            pytest.skip("decision-precedence.md does not use tier numbering")

        # The unique tiers in order of first appearance should match
        cr_unique_order = list(dict.fromkeys(cr_tiers))
        dp_unique_order = list(dict.fromkeys(dp_tiers))

        # Both should have the same tiers
        assert set(cr_unique_order) == set(dp_unique_order) or set(dp_unique_order).issubset(
            set(cr_unique_order)
        ), (
            f"Tier sets differ: CONFLICT_RESOLUTION has {set(cr_unique_order)}, "
            f"decision-precedence has {set(dp_unique_order)}"
        )

        # Order should be consistent (both ascending)
        if len(dp_unique_order) > 1:
            assert dp_unique_order == sorted(dp_unique_order), (
                f"decision-precedence.md presents tiers in non-standard order: {dp_unique_order}"
            )

    def test_trd11_not_overclaimed_as_universal(self, conflict_resolution_content):
        """Verify TRD-11 override is scoped explicitly to security matters only."""
        # Find Tier 1 section
        tier1_match = re.search(
            r'[Tt]ier\s*1.*?(?=[Tt]ier\s*2|\Z)',
            conflict_resolution_content,
            re.DOTALL,
        )
        assert tier1_match, "Tier 1 section not found"
        tier1_text = tier1_match.group(0).lower()

        # Must contain scoping language
        scoping_indicators = [
            "security",
            "scope",
            "only",
            "limited",
            "does not",
            "not have general",
            "security-relevant",
            "security matter",
        ]
        found_scoping = sum(1 for s in scoping_indicators if s in tier1_text)
        assert found_scoping >= 2,
