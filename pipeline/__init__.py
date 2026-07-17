"""Pre-event data pipeline: ingest, enrich, score, load."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_required_json(path: str | Path, *, hint: str) -> Any:
    """Load a required pipeline input file, exiting with an actionable message on failure.

    Args:
        path: Path to the JSON input file.
        hint: Actionable next step (e.g. the command that produces the file),
            included in the error message when the file is missing or malformed.
    """
    file_path = Path(path)
    if not file_path.exists():
        sys.exit(f"Error: {file_path} not found — {hint}")
    try:
        with file_path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as error:
        sys.exit(f"Error: {file_path} is not valid JSON ({error}) — fix or delete it, then {hint}")
