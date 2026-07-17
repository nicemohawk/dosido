"""Tests for the backfill worker's API response parsing guard."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.backfill_worker import extract_score_result


def make_response(blocks: list) -> SimpleNamespace:
    return SimpleNamespace(content=blocks)


class TestExtractScoreResult:
    def test_plain_json(self):
        response = make_response(
            [SimpleNamespace(text='{"score": 80, "rationale": "r", "spark": "s"}')]
        )
        assert extract_score_result(response)["score"] == 80

    def test_markdown_fenced_json(self):
        response = make_response([SimpleNamespace(text='```json\n{"score": 72}\n```')])
        assert extract_score_result(response)["score"] == 72

    def test_empty_content_raises(self):
        with pytest.raises(ValueError):
            extract_score_result(make_response([]))

    def test_textless_content_raises(self):
        with pytest.raises(ValueError):
            extract_score_result(make_response([SimpleNamespace(type="tool_use")]))
