"""Tests for the pipeline required-input validation helper."""

from __future__ import annotations

import json

import pytest

from pipeline import load_required_json


def test_missing_file_exits_with_actionable_message(tmp_path):
    missing_path = tmp_path / "enriched_attendees.json"

    with pytest.raises(SystemExit) as exit_info:
        load_required_json(missing_path, hint="run `dosido-seed` for test data")

    message = str(exit_info.value)
    assert "enriched_attendees.json" in message
    assert "not found" in message
    assert "dosido-seed" in message


def test_invalid_json_exits_with_actionable_message(tmp_path):
    malformed_path = tmp_path / "matrix.json"
    malformed_path.write_text("{not valid json")

    with pytest.raises(SystemExit) as exit_info:
        load_required_json(malformed_path, hint="run `dosido-score`")

    message = str(exit_info.value)
    assert "matrix.json" in message
    assert "not valid JSON" in message
    assert "dosido-score" in message


def test_valid_json_returns_parsed_data(tmp_path):
    valid_path = tmp_path / "attendees.json"
    attendees = [{"id": "abc", "name": "Ada"}]
    valid_path.write_text(json.dumps(attendees))

    assert load_required_json(valid_path, hint="unused") == attendees
