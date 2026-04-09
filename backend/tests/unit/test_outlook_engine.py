"""Unit tests for the outlook engine — pure math, no DB, no LLM.

Tests cover all the edge cases specified in docs/05-data-model.md:
- Zero streak → flat projection (no streak bonus)
- Broken streak → curve flattens (projected ≥ current_score), never drops
- 7+ day streak → streak boost is applied
- Score ≥ 90 → diminishing-returns region
- Adherence = 0.0 vs 1.0 → adherence modulates the streak weight
- Contract: projected_score >= current_score for all horizons always holds
"""

from __future__ import annotations

import pytest

from app.services.outlook_engine import compute_outlook

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
            assert isinstance(value, float), f"horizon {horizon}: expected float, got {type(value)}"

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
# Zero streak → flat projection
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
# Broken streak: streak_days=0 after some positive value
# ---------------------------------------------------------------------------


class TestBrokenStreak:
    """When streak is broken, projections should not exceed the pre-break values
    — but crucially they must stay >= current_score (flattens, never drops)."""

    def test_broken_streak_does_not_exceed_active_streak(self) -> None:
        """Active streak with same parameters should project higher than broken."""
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
            # Active streak must project at least as high as broken streak
            assert active[horizon] >= broken[horizon], (
                f"horizon {horizon}: active {active[horizon]} < broken {broken[horizon]}"
            )

    def test_broken_streak_holds_at_current_score(self) -> None:
        """Broken streak means hold the current score — the 'flattens' contract."""
        current = 77.5
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=0,
            protocol_adherence=0.5,
        )
        for horizon in HORIZONS:
            # Flat at current — no drop, no rise
            assert result[horizon] == pytest.approx(current)


# ---------------------------------------------------------------------------
# Seven-plus day streak: reward applied
# ---------------------------------------------------------------------------


class TestSevenPlusDayStreak:
    """A 7+ day streak should produce projections above current_score."""

    def test_seven_day_streak_raises_projection(self) -> None:
        current = 60.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=7,
            protocol_adherence=1.0,
        )
        # At least some horizon should be above current (streak bonus applied)
        assert any(result[h] > current for h in HORIZONS), (
            "7-day streak with full adherence should raise at least one horizon above current"
        )

    def test_longer_streak_projects_higher_than_shorter(self) -> None:
        """More streak days → higher projection at shorter horizons."""
        current = 65.0
        short = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=3,
            protocol_adherence=0.8,
        )
        long_ = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=21,
            protocol_adherence=0.8,
        )
        # Longer streak must project >= shorter at every horizon
        for horizon in HORIZONS:
            assert long_[horizon] >= short[horizon], (
                f"horizon {horizon}: 21-day streak {long_[horizon]} < 3-day {short[horizon]}"
            )

    def test_streak_boost_increases_with_adherence(self) -> None:
        """Higher adherence → higher projection, all else equal."""
        current = 60.0
        low = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=10,
            protocol_adherence=0.2,
        )
        high = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=10,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            assert high[horizon] >= low[horizon], (
                f"horizon {horizon}: high adherence {high[horizon]} < low adherence {low[horizon]}"
            )


# ---------------------------------------------------------------------------
# Score ≥ 90: diminishing returns
# ---------------------------------------------------------------------------


class TestDiminishingReturns:
    """When current_score >= 90 the boost should be visibly smaller."""

    def test_high_score_projection_stays_bounded_at_100(self) -> None:
        """No projected score may exceed 100."""
        result = compute_outlook(
            patient_id="PT0001",
            current_score=95.0,
            streak_days=30,
            protocol_adherence=1.0,
        )
        for horizon, projected in result.items():
            assert projected <= 100.0, f"horizon {horizon}: projected {projected} > 100"

    def test_high_score_boost_smaller_than_low_score_boost(self) -> None:
        """Boost for score=92 should be smaller than boost for score=60 (same streak)."""
        streak, adherence = 14, 1.0
        low_base = compute_outlook(
            patient_id="PT0001",
            current_score=60.0,
            streak_days=streak,
            protocol_adherence=adherence,
        )
        high_base = compute_outlook(
            patient_id="PT0001",
            current_score=92.0,
            streak_days=streak,
            protocol_adherence=adherence,
        )
        # absolute boost = projected - current
        for horizon in HORIZONS:
            low_boost = low_base[horizon] - 60.0
            high_boost = high_base[horizon] - 92.0
            assert high_boost <= low_boost, (
                f"horizon {horizon}: high-score boost {high_boost} > low-score boost {low_boost}"
            )

    def test_score_100_returns_100_for_all_horizons(self) -> None:
        """Score already at 100 → projection is 100 at all horizons."""
        result = compute_outlook(
            patient_id="PT0001",
            current_score=100.0,
            streak_days=30,
            protocol_adherence=1.0,
        )
        for horizon in HORIZONS:
            assert result[horizon] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Adherence = 0.0 vs 1.0
# ---------------------------------------------------------------------------


class TestAdherenceEdgeCases:
    """Zero adherence suppresses the streak bonus; full adherence maximises it."""

    def test_zero_adherence_with_active_streak_returns_flat(self) -> None:
        """adherence=0.0 means no benefit even from a long streak."""
        current = 70.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=20,
            protocol_adherence=0.0,
        )
        for horizon in HORIZONS:
            # Zero adherence → projection must equal current (no benefit)
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
# Horizon ordering: 3-month ≥ 6-month ≥ 12-month delta
# ---------------------------------------------------------------------------


class TestHorizonOrdering:
    """Decay should make the near-term projection relatively higher than long-term."""

    def test_3m_delta_gte_6m_delta(self) -> None:
        """Decay tempers long-horizon optimism: 3m boost ≥ 6m boost."""
        current = 65.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=14,
            protocol_adherence=0.9,
        )
        delta_3 = result[3] - current
        delta_6 = result[6] - current
        assert delta_3 >= delta_6, f"3m delta {delta_3} < 6m delta {delta_6}"

    def test_6m_delta_gte_12m_delta(self) -> None:
        """Decay: 6m boost ≥ 12m boost."""
        current = 65.0
        result = compute_outlook(
            patient_id="PT0001",
            current_score=current,
            streak_days=14,
            protocol_adherence=0.9,
        )
        delta_6 = result[6] - current
        delta_12 = result[12] - current
        assert delta_6 >= delta_12, f"6m delta {delta_6} < 12m delta {delta_12}"
