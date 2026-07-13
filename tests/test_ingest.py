"""Tests for registration CSV ingest normalizers and seed-data alignment fields."""

from __future__ import annotations

import csv

import pytest

from app.models import Ambition, Attendee, DecisionStyle, Edge, EquityPhilosophy, Runway
from pipeline.ingest import (
    ingest_csv,
    normalize_ambition,
    normalize_commitment,
    normalize_decision_style,
    normalize_edge,
    normalize_equity_philosophy,
    normalize_idea_flexibility,
    normalize_runway,
)
from scripts.seed_test_data import generate_attendees


class TestNormalizeCommitment:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Full-time now", "full-time"),
            ("full time", "full-time"),
            ("Full-time within 3 months if I find the right person", "full-time-soon"),
            ("would go full-time soon", "full-time-soon"),
            ("Part-time / nights and weekends", "part-time"),
            ("Exploring", "exploring"),
            ("", "exploring"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_commitment(raw) == expected


class TestNormalizeRunway:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Less than 3 months", "under-3-months"),
            ("under 3 months", "under-3-months"),
            ("3-12 months", "3-12-months"),
            ("3 to 12", "3-12-months"),
            ("12+ months", "12-plus-months"),
            ("More than 12 months", "12-plus-months"),
            ("Prefer not to say", "undisclosed"),
            ("", "undisclosed"),
            ("no idea", "undisclosed"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_runway(raw) == expected
        assert Runway(normalize_runway(raw))


class TestNormalizeAmbition:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Bootstrap", "bootstrap"),
            ("lifestyle business", "bootstrap"),
            ("Go big or go home", "venture-scale"),
            ("Venture-scale", "venture-scale"),
            ("IPO someday", "venture-scale"),
            ("Somewhere in the middle", "moderate"),
            ("moderate growth", "moderate"),
            ("", "undecided"),
            ("who knows", "undecided"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_ambition(raw) == expected
        assert Ambition(normalize_ambition(raw))


class TestNormalizeEquityPhilosophy:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Equal split, period", "equal"),
            ("Roughly equal with vesting", "near-equal-vesting"),
            ("Split should reflect contribution", "contribution-based"),
            ("contribution-based", "contribution-based"),
            ("No strong view yet", "no-strong-view"),
            ("", "no-strong-view"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_equity_philosophy(raw) == expected
        assert EquityPhilosophy(normalize_equity_philosophy(raw))


class TestNormalizeEdge:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Technical depth", "technical"),
            ("Domain expertise", "domain"),
            ("industry knowledge", "domain"),
            ("Network and distribution", "network"),
            ("", "unknown"),
            ("charm", "unknown"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_edge(raw) == expected
        assert Edge(normalize_edge(raw))


class TestNormalizeIdeaFlexibility:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Committed to my idea", "committed"),
            ("I'd drop it for a better one", "flexible"),
            ("flexible", "flexible"),
            ("", "n/a"),
            ("joining someone else", "n/a"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_idea_flexibility(raw) == expected


class TestNormalizeDecisionStyle:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Debate it out loud", "debate"),
            ("Write up both positions, then decide", "write-then-decide"),
            ("Defer to whoever owns that area", "defer-to-owner"),
            ("Run a test and let the data decide", "data-driven"),
            ("", "unknown"),
        ],
    )
    def test_normalizes(self, raw, expected):
        assert normalize_decision_style(raw) == expected
        assert DecisionStyle(normalize_decision_style(raw))


def _write_csv(path, headers, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


class TestIngestCsv:
    def test_new_columns_are_normalized(self, tmp_path):
        csv_path = tmp_path / "luma.csv"
        _write_csv(
            csv_path,
            [
                "Name",
                "Email",
                "Commitment",
                "Runway",
                "Scale Ambition",
                "Equity Split Philosophy",
                "Your Edge",
                "Idea Flexibility",
                "Decision Style",
                "Proof Link 1 Description",
                "Hardest Thing",
            ],
            [
                [
                    "Ada L.",
                    "ada@example.com",
                    "Full-time within 3 months if I find the right person",
                    "less than 3 months",
                    "go big",
                    "equal split, period",
                    "technical",
                    "would drop it",
                    "write a memo",
                    "Built the first compiler",
                    "Programming before computers existed",
                ]
            ],
        )

        records = ingest_csv(str(csv_path), output_path=str(tmp_path / "out.json"))

        assert len(records) == 1
        record = records[0]
        assert record["commitment"] == "full-time-soon"
        assert record["runway"] == "under-3-months"
        assert record["ambition"] == "venture-scale"
        assert record["equity_philosophy"] == "equal"
        assert record["edge"] == "technical"
        assert record["idea_flexibility"] == "flexible"
        assert record["decision_style"] == "write-then-decide"
        assert record["proof_summary_1"] == "Built the first compiler"
        assert record["hardest_thing"] == "Programming before computers existed"
        assert Attendee(**record)

    def test_missing_columns_fall_back_to_model_defaults(self, tmp_path):
        csv_path = tmp_path / "luma.csv"
        _write_csv(csv_path, ["Name", "Email"], [["Grace H.", "grace@example.com"]])

        records = ingest_csv(str(csv_path), output_path=str(tmp_path / "out.json"))

        attendee = Attendee(**records[0])
        assert attendee.runway == Runway.UNDISCLOSED
        assert attendee.ambition == Ambition.UNDECIDED
        assert attendee.equity_philosophy == EquityPhilosophy.NO_STRONG_VIEW
        assert attendee.edge == Edge.UNKNOWN
        assert attendee.decision_style == DecisionStyle.UNKNOWN
        assert attendee.hardest_thing == ""


class TestSeedDataAlignmentFields:
    def test_curated_attendees_carry_alignment_fields(self):
        attendees = generate_attendees(60)

        for record in attendees:
            attendee = Attendee(**record)
            assert attendee.runway in Runway
            assert attendee.ambition in Ambition
            assert attendee.equity_philosophy in EquityPhilosophy
            assert attendee.edge != Edge.UNKNOWN
            assert attendee.decision_style != DecisionStyle.UNKNOWN
            assert attendee.hardest_thing
