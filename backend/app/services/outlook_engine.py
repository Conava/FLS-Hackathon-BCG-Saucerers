"""Outlook engine — pure deterministic math for Vitality Outlook projections.

No database access, no LLM calls. Fully deterministic given the same inputs.
Cacheable by the caller.

Contract (docs/05-data-model.md):
    Outlook(h months) = Score_now + Σ (streak_weight × streak_days × adherence × decay(h))

    ``streak_weight`` is a heuristic aggregate across protocol action categories
    (nutrition 0.15/day capped, sleep 0.20, movement 0.15, mind 0.10,
    supplement 0.05). We use the mean weight (0.13) as the aggregate single-
    category estimate, then allow the caller to supply per-category detail in
    a future extension. For now a single ``streak_days`` and
    ``protocol_adherence`` drives the projection.

    **Product invariant:** Breaking a streak flattens the curve — the
    projected score holds at the last projected value (= current_score when
    streak_days == 0), never drops below current_score.

    **Diminishing returns:** When ``current_score >= 90`` the per-day boost
    is scaled down to model the harder gains near the ceiling.

    **Cap at 100:** No projected score may exceed 100.

Usage::

    from app.services.outlook_engine import compute_outlook

    projections = compute_outlook(
        patient_id="PT0001",
        current_score=68.5,
        streak_days=12,
        protocol_adherence=0.9,
    )
    # → {3: 71.2, 6: 70.4, 12: 69.8}

Returns:
    dict[int, float] with keys ``{3, 6, 12}`` (horizon in months).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Heuristic constants
# ---------------------------------------------------------------------------

# Aggregate streak weight per day — average across the five action categories
# defined in docs/05 (nutrition=0.15, sleep=0.20, movement=0.15, mind=0.10,
# supplement=0.05 → mean ≈ 0.13).
_STREAK_WEIGHT_PER_DAY: float = 0.13

# Hard cap on the per-day boost to avoid unbounded projections with very long streaks.
# Represents the maximum daily score gain from streak adherence.
_MAX_DAILY_BOOST: float = 0.25

# Decay factors per horizon (fraction of the streak bonus retained).
# Near-term projection is less discounted; 12-month outlook is heavily decayed.
_DECAY: dict[int, float] = {
    3: 0.80,   # 3-month: 80% of the streak signal survives
    6: 0.55,   # 6-month: 55%
    12: 0.30,  # 12-month: 30% — long-range uncertainty
}

# Diminishing-returns threshold.  Above this score each additional day's gain
# is scaled down by ``(100 - current_score) / (100 - _DR_THRESHOLD)``.
_DR_THRESHOLD: float = 90.0

# Horizons returned by every compute_outlook call (months).
_HORIZONS: list[int] = [3, 6, 12]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_outlook(
    patient_id: str,  # noqa: ARG001 — included for caller convenience/logging
    current_score: float,
    streak_days: int,
    protocol_adherence: float,
) -> dict[int, float]:
    """Compute the vitality outlook projection for a set of time horizons.

    The function is **pure**: the same inputs always return the same outputs.
    ``patient_id`` is accepted for caller convenience (e.g. structured logging)
    but is not used in the calculation.

    Streak math (docs/05-data-model.md):
      - ``streak_days == 0`` → broken or never started → projection held at
        ``current_score`` (flattens the curve, never drops).
      - ``protocol_adherence == 0.0`` → no benefit even with an active streak.
      - ``current_score >= 90`` → diminishing-returns region — boost is scaled
        by ``(100 - current_score) / (100 - DR_THRESHOLD)``.
      - Resulting score is clamped to ``[current_score, 100.0]``.

    Args:
        patient_id:          Patient identifier (not used in math; for logging).
        current_score:       Present Vitality Score on the 0–100 scale.
        streak_days:         Number of consecutive days the protocol was followed.
                             Zero means the streak is broken.
        protocol_adherence:  Fractional measure of how closely the patient followed
                             the protocol (0.0 = none, 1.0 = perfect).

    Returns:
        A ``dict[int, float]`` with keys ``{3, 6, 12}`` (horizon in months),
        each mapping to the projected Vitality Score at that horizon.
    """
    # ------------------------------------------------------------------
    # Broken / zero streak → flat projection at current_score
    # ------------------------------------------------------------------
    if streak_days <= 0 or protocol_adherence <= 0.0:
        return {h: float(current_score) for h in _HORIZONS}

    # ------------------------------------------------------------------
    # Streak bonus: effective daily boost
    # ------------------------------------------------------------------
    # Raw bonus per day, capped at MAX_DAILY_BOOST.
    daily_boost = min(_STREAK_WEIGHT_PER_DAY * protocol_adherence, _MAX_DAILY_BOOST)

    # Total raw streak contribution (streak_days × daily_boost).
    raw_streak_bonus = float(streak_days) * daily_boost

    # ------------------------------------------------------------------
    # Diminishing returns near the score ceiling (≥ DR_THRESHOLD)
    # ------------------------------------------------------------------
    if current_score >= _DR_THRESHOLD:
        # headroom_fraction: 0.0 at score=100, 1.0 at score=DR_THRESHOLD
        headroom = 100.0 - current_score
        headroom_fraction = headroom / (100.0 - _DR_THRESHOLD)
        raw_streak_bonus *= headroom_fraction

    # ------------------------------------------------------------------
    # Per-horizon projection with decay
    # ------------------------------------------------------------------
    projections: dict[int, float] = {}
    for horizon in _HORIZONS:
        bonus = raw_streak_bonus * _DECAY[horizon]
        projected = current_score + bonus
        # Clamp: never below current_score, never above 100
        projected = max(projected, current_score)
        projected = min(projected, 100.0)
        projections[horizon] = float(projected)

    return projections
