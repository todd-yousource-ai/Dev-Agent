"""
Root conftest.py for Crafted Dev Agent test suite.

Repository-level pytest configuration file that enables test discovery
from the repository root. Inserts src/ into sys.path at pytest startup
so test files can resolve imports from the src/ layout without requiring
PYTHONPATH to be set.

Security assumptions:
    - This file performs no network access, no environment mutation beyond
      sys.path, and loads no secrets.
    - Side-effect free apart from the deterministic sys.path insert below.
    - Safe to import even when no src/ directory exists -- the path insert
      is a no-op in that case (Python silently ignores non-existent
      sys.path entries during import resolution).

Failure behavior:
    - No exceptions are raised. If src/ does not exist the path is still
      added to sys.path; Python import machinery handles missing paths
      gracefully by skipping them during module search.

Fixtures will be added in later PRs as test code is introduced.
"""
import sys
from pathlib import Path

# Insert src/ at position 0 so it takes precedence over any installed
# package with the same name (avoids importing the wrong 'forge' package).
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))