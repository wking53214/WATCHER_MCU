"""A folder that exists and stands in for the governed one in tests that give `--out` for a record that does not
name its governed folder (the real fixtures predate that field). No test writes into it."""
from pathlib import Path

GOVERNED = Path(__file__).parent / "fixtures"
