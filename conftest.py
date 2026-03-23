"""
conftest.py — Repository-level pytest configuration.

Inserts src/ into sys.path at pytest startup so test files can resolve
imports from the src/ layout without requiring PYTHONPATH to be set.

This file is intentional and should not be removed. It is the canonical
fix for ModuleNotFoundError on src-layout Python projects.
"""
import sys
from pathlib import Path

# Insert src/ at position 0 so it takes precedence over any installed
# package with the same name (avoids importing the wrong 'forge' package).
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
