"""Unit tests for the outlook engine — pure math, no DB, no LLM.

Tests cover all edge cases specified in docs/10-vitality-formula.md §5:

  Capped-ceiling multiplicative model:
    Outlook(h) = current + (ceiling − current) × adherence × streak_mult × horizon_factor(h)
    ceiling = 95.0
    horizon_factor = {3: 0.25, 6: 0.50, 12: 0.70}
    streak_mult(s) = 1 − exp(−s / 30)

  Edge cases:
  - streak_days ≤ 0                        → flat at current_score
  - protocol_adherence == 0.0              → flat at current_score
  - current_score == 100                   → all horizons return 100 (gap=0, above ceiling)
  - current_score > CEILING (e.g. 97)      → gap clamped to 0 → flat at current_score
  - Monotonicity: longer streak             → higher or equal projected score
  - Monotonicity: higher adherence          → higher or equal projected score
  - Horizon ordering: h=3 ≤ h=6 ≤ h=12    → later horizons capture more of the gap
  - Rebecca worked example                  → matches doc §6.8 golden values
  - Very long streak at ceiling approaches CEILING=95, not 100
"""

from __future__ import annotations

import math

import pytest

from app.services.outlook_engine import CEILING, compute_outlook

HORIZONS = [3, 6, 12]


# ---------------------------------------------------------------------------
# Basic contract: return shape
# ---------------------------------------------------------------------------


class TestReturnShape:
    """compute_outlook always returns a dict keyed by {3, 6, 12}."""

    def test_returns_dict_with_three_horizons(self) -> None:
        result = compute_outlook(
            patient_id="PT0001",
            current_score=60.0,
            streak_days=5,
            protocol_adherence=0.8,
        )
        assert set(result.keys()) == {3, 6, 12}

    def test_all_values_are_floats(self) -> None:
        result = compute_outlook(
            patient_id="PT0001",
            current_score=60.0,
            streak_days=5,
            protocol_adherence=0.8,
        )
        for horizon, value in result.items():
            assert isinstance(value, float), (
                f"horizon {horizon}: expected float, got {type(value)}"
            )

    def test_patient_id_does_not_affect_result(self) -> None:
        """compute_outlook is pure: patient_id is not used in math."""
        result_a = compute_outlook(
            patient_id="PT0001",
            current_score=70.0,
            streak_days=10,
            protocol_adherence=0.9,
        )
        result_b = compute_outlook(
            patient_id="PT9999",
            current_score=70.0,
            streak_days=10,
            protocol_adherence=0.9,
        )
        assert result_a == result_b


# ---------------------------------------------------------------------------
# Core invariant: never drops below current_score
# ---------------------------------------------------------------------------


class TestNeverDropsBelowCurrentScore:
    """projected_score >= current_score for every horizon, every case."""

    @pytest.mark.parametrize("streak_days", [0, 1, 3, 7, 14, 30])
    @pytest.mark.parametrize("adherence", [0.0, 0.5, 1.0])
    @pytest.mark.parametrize("current_score", [40.0, 70.0, 89.0, 95.0, 100.0])
    def test_projection_never_drops(
        self, streak_days: int, adherence: float, current_score: float
    ) -> None:
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current_score,
            streak_days=streak_days,
            protocol_adherence=adherence,
        )
        for horizon, projected in result.items():
            assert projected >= current_score, (
                f"streak={streak_days}, adherence={adherence}, "
                f"score={current_score}, horizon={horizon}: "
                f"projected {projected} < current {current_score}"
            )

    def test_broken_streak_flattens_not_drops(self) -> None:
        """Breaking streak (streak_days=0) keeps projection at current_score."""
        current_score = 65.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current_score,
            streak_days=0,
            protocol_adherence=0.8,
        )
        for horizon, projected in result.items():
            assert projected == pytest.approx(current_score), (
                f"horizon {horizon}: expected flat {current_score}, got {projected}"
            )


# ---------------------------------------------------------------------------
# T4 test case 1: streak_days == 0 → flat at current_score
# ---------------------------------------------------------------------------


class TestZeroStreak:
    """Zero streak_days means the projection is flat at current_score."""

    def test_zero_streak_returns_current_score(self) -> None:
        current = 55.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=0,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            assert result[horizon] == pytest.approx(current)

    def test_negative_streak_returns_current_score(self) -> None:
        current = 55.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=-5,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            assert result[horizon] == pytest.approx(current)

    def test_zero_adherence_zero_streak_flat(self) -> None:
        current = 72.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=0,
            protocol_adherence=0.0,
        )
        for horizon in HORIZONS:
            assert result[horizon] == pytest.approx(current)


# ---------------------------------------------------------------------------
# T4 test case 2: protocol_adherence == 0.0 → flat at current_score
# ---------------------------------------------------------------------------


class TestZeroAdherence:
    """Zero adherence suppresses all gain even with an active streak."""

    def test_zero_adherence_with_long_streak_is_flat(self) -> None:
        current = 70.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=60,
            protocol_adherence=0.0,
        )
        for horizon in HORIZONS:
            assert result[horizon] == pytest.approx(current), (
                f"horizon {horizon}: expected flat {current}, got {result[horizon]}"
            )

    def test_full_adherence_produces_higher_projection_than_zero(self) -> None:
        """Full adherence with an active streak should produce a higher projection."""
        current = 70.0
        streak = 14
        zero_adh = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=streak,
            protocol_adherence=0.0,
        )
        full_adh = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=streak,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            assert full_adh[horizon] >= zero_adh[horizon]


# ---------------------------------------------------------------------------
# T4 test case 3: current_score == 100 → all horizons return 100
# ---------------------------------------------------------------------------


class TestScoreAt100:
    """Score already at 100 → reachable_gap = 0 → projection stays at 100."""

    def test_score_100_returns_100_for_all_horizons(self) -> None:
        result = compute_outlook(
            patient_id="PT0001",
            current_score=100.0,
            streak_days=30,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            # gap = max(0, 95 - 100) = 0, so gain = 0
            # projected = max(100, min(max(100,95), 100 + 0)) = 100
            assert result[horizon] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# T4 test case 4: current_score > CEILING → gap clamped to 0, flat at current
# ---------------------------------------------------------------------------


class TestScoreAboveCeiling:
    """When current_score > CEILING, reachable_gap is clamped to 0 — no gain."""

    def test_score_above_ceiling_stays_at_current(self) -> None:
        current = 97.0  # above CEILING=95
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=30,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            # reachable_gap = max(0, 95-97) = 0 → gain = 0
            # projected = max(97, min(max(97,95), 97)) = 97
            assert result[horizon] == pytest.approx(current), (
                f"horizon {horizon}: score above ceiling should stay at {current}, "
                f"got {result[horizon]}"
            )

    def test_score_exactly_at_ceiling_stays_at_ceiling(self) -> None:
        """Score at exactly CEILING → gap is 0 → flat at CEILING."""
        current = 95.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=30,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            assert result[horizon] == pytest.approx(CEILING)


# ---------------------------------------------------------------------------
# T4 test case 5: Monotonicity — longer streak → higher or equal projection
# ---------------------------------------------------------------------------


class TestMonotonicityStreak:
    """Longer streak at same adherence yields higher or equal projected score."""

    def test_longer_streak_projects_higher_than_shorter(self) -> None:
        current = 65.0
        adherence = 0.8
        short = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=3,
            protocol_adherence=adherence,
        )
        long_ = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=21,
            protocol_adherence=adherence,
        )
        for horizon in HORIZONS:
            assert long_[horizon] >= short[horizon], (
                f"horizon {horizon}: 21-day streak {long_[horizon]} < "
                f"3-day {short[horizon]}"
            )

    def test_broken_streak_does_not_exceed_active_streak(self) -> None:
        current = 60.0
        adherence = 0.9
        active = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=14,
            protocol_adherence=adherence,
        )
        broken = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=0,
            protocol_adherence=adherence,
        )
        for horizon in HORIZONS:
            assert active[horizon] >= broken[horizon], (
                f"horizon {horizon}: active {active[horizon]} < broken {broken[horizon]}"
            )

    def test_very_long_streak_monotone_with_medium(self) -> None:
        current = 50.0
        adherence = 0.7
        medium = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=30,
            protocol_adherence=adherence,
        )
        long_ = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=90,
            protocol_adherence=adherence,
        )
        for horizon in HORIZONS:
            assert long_[horizon] >= medium[horizon]


# ---------------------------------------------------------------------------
# T4 test case 6: Monotonicity — higher adherence → higher or equal projection
# ---------------------------------------------------------------------------


class TestMonotonicityAdherence:
    """Higher adherence at same streak yields higher or equal projected score."""

    def test_higher_adherence_projects_higher(self) -> None:
        current = 60.0
        streak = 10
        low = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=streak,
            protocol_adherence=0.2,
        )
        high = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=streak,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            assert high[horizon] >= low[horizon], (
                f"horizon {horizon}: high adherence {high[horizon]} < "
                f"low adherence {low[horizon]}"
            )

    @pytest.mark.parametrize("adherence_low,adherence_high", [
        (0.1, 0.5),
        (0.5, 0.9),
        (0.3, 1.0),
    ])
    def test_adherence_ordering_parametric(
        self, adherence_low: float, adherence_high: float
    ) -> None:
        current = 65.0
        streak = 14
        result_low = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=streak,
            protocol_adherence=adherence_low,
        )
        result_high = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=streak,
            protocol_adherence=adherence_high,
        )
        for horizon in HORIZONS:
            assert result_high[horizon] >= result_low[horizon]


# ---------------------------------------------------------------------------
# T4 test case 7: Horizon ordering — projections[3] ≤ projections[6] ≤ projections[12]
# ---------------------------------------------------------------------------


class TestHorizonOrdering:
    """Later horizons capture more of the gap: h=3 ≤ h=6 ≤ h=12."""

    def test_3m_lte_6m_lte_12m(self) -> None:
        """horizon_factor grows from 3→6→12; later horizons must project higher."""
        current = 65.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=14,
            protocol_adherence=0.9,
        )
        assert result[3] <= result[6], (
            f"3m {result[3]} > 6m {result[6]}"
        )
        assert result[6] <= result[12], (
            f"6m {result[6]} > 12m {result[12]}"
        )

    def test_deltas_increase_with_horizon(self) -> None:
        """Absolute gain (projected - current) is also increasing with horizon."""
        current = 60.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=20,
            protocol_adherence=0.75,
        )
        delta_3 = result[3] - current
        delta_6 = result[6] - current
        delta_12 = result[12] - current
        assert delta_3 <= delta_6, f"delta_3={delta_3} > delta_6={delta_6}"
        assert delta_6 <= delta_12, f"delta_6={delta_6} > delta_12={delta_12}"


# ---------------------------------------------------------------------------
# T4 test case 8: Rebecca worked example (docs/10-vitality-formula.md §6.8)
# ---------------------------------------------------------------------------


class TestRebeccaWorkedExample:
    """Golden values from the doc's worked example.

    Inputs: current=79.3, streak_days=14, adherence=0.85
    streak_mult = 1 − exp(−14/30) ≈ 0.373
    gap = 95.0 − 79.3 = 15.7
    h=3:  gain = 15.7 × 0.85 × 0.373 × 0.25 ≈ 1.25  → projected ≈ 80.5
    h=6:  gain = 15.7 × 0.85 × 0.373 × 0.50 ≈ 2.49  → projected ≈ 81.8
    h=12: gain = 15.7 × 0.85 × 0.373 × 0.70 ≈ 3.49  → projected ≈ 82.8
    """

    def test_rebecca_golden_values(self) -> None:
        result = compute_outlook(
            patient_id="PT0199",
            current_score=79.3,
            streak_days=14,
            protocol_adherence=0.85,
        )
        assert result[3] == pytest.approx(80.5, abs=0.3)
        assert result[6] == pytest.approx(81.8, abs=0.3)
        assert result[12] == pytest.approx(82.8, abs=0.3)

    def test_rebecca_all_projections_above_current(self) -> None:
        result = compute_outlook(
            patient_id="PT0199",
            current_score=79.3,
            streak_days=14,
            protocol_adherence=0.85,
        )
        for horizon, projected in result.items():
            assert projected > 79.3, (
                f"horizon {horizon}: expected gain above 79.3, got {projected}"
            )

    def test_rebecca_horizon_ordering(self) -> None:
        result = compute_outlook(
            patient_id="PT0199",
            current_score=79.3,
            streak_days=14,
            protocol_adherence=0.85,
        )
        assert result[3] < result[6] < result[12]


# ---------------------------------------------------------------------------
# T4 test case 9: Very long streak approaches CEILING=95, never exceeds it
# ---------------------------------------------------------------------------


class TestVeryLongStreakCeiling:
    """streak_days=1000, adherence=1.0, current=50 → approaches but ≤ CEILING=95."""

    def test_very_long_streak_bounded_by_ceiling(self) -> None:
        result = compute_outlook(
            patient_id="PT0001",
            current_score=50.0,
            streak_days=1000,
            protocol_adherence=1.0,
        )
        for horizon, projected in result.items():
            assert projected <= CEILING, (
                f"horizon {horizon}: projected {projected} exceeds CEILING={CEILING}"
            )

    def test_very_long_streak_approaches_ceiling(self) -> None:
        """At streak=1000 days streak_mult ≈ 1.0; 12m projection should be close to ceiling."""
        result = compute_outlook(
            patient_id="PT0001",
            current_score=50.0,
            streak_days=1000,
            protocol_adherence=1.0,
        )
        # At streak→∞, streak_mult→1.0; h=12 gain = (95-50)*1.0*1.0*0.70 = 31.5 → 81.5
        # (still not at ceiling because horizon_factor for 12m is only 0.70)
        expected_12 = 50.0 + (95.0 - 50.0) * 1.0 * (1.0 - math.exp(-1000 / 30)) * 0.70
        assert result[12] == pytest.approx(expected_12, abs=0.01)
        assert result[12] > 50.0

    def test_high_score_with_long_streak_cannot_exceed_ceiling(self) -> None:
        """Even at current=94.9 (just below ceiling), result is ≤ CEILING."""
        result = compute_outlook(
            patient_id="PT0001",
            current_score=94.9,
            streak_days=1000,
            protocol_adherence=1.0,
        )
        for horizon, projected in result.items():
            assert projected <= CEILING, (
                f"horizon {horizon}: projected {projected} exceeds CEILING={CEILING}"
            )
