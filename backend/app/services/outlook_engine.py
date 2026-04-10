"""Outlook engine — pure deterministic math for Vitality Outlook projections.

No database access, no LLM calls. Fully deterministic given the same inputs.
Cacheable by the caller.

Model (docs/10-vitality-formula.md §5 — capped-ceiling multiplicative):

    Outlook(h) = current + (ceiling − current) × adherence × streak_mult × horizon_factor(h)

    ``ceiling``         = 95.0  (theoretical healthy upper bound; not a clinical target)
    ``horizon_factor``  = {3: 0.25, 6: 0.50, 12: 0.70}  (fraction of gap captured at month h)
    ``streak_mult(s)``  = 1 − exp(−s / τ)  where τ = 30 days
                          → 0 at s=0, 0.37 at s=14, 0.63 at s=30, 0.86 at s=60

    Semantics: "Better habits close the gap to your ceiling; the longer you stick with it,
    the more of that gap you capture."

    **Product invariants:**
    - ``streak_days ≤ 0`` OR ``adherence ≤ 0.0`` → flat at ``current_score`` (no gain).
    - ``current_score ≥ ceiling`` → reachable gap is 0; projection stays at ``current_score``.
    - Result is always clamped to [current_score, ceiling] — never drops, never exceeds ceiling.

Usage::

    from app.services.outlook_engine import compute_outlook

    projections = compute_outlook(
        patient_id="PT0001",
        current_score=79.3,
        streak_days=14,
        protocol_adherence=0.85,
    )
    # → {3: 80.5, 6: 81.8, 12: 82.8}  (approximately)

Returns:
    dict[int, float] with keys ``{3, 6, 12}`` (horizon in months).
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

# Theoretical healthy upper bound — the "ceiling" the patient is closing in on.
# Not a clinical target; 95.0 leaves headroom to acknowledge life's complexity.
CEILING: float = 95.0

# Fraction of the reachable gap captured at each horizon (months).
# Later horizons have higher factors because more time allows more of the gap to close.
HORIZON_FACTOR: dict[int, float] = {3: 0.25, 6: 0.50, 12: 0.70}

# Time constant for the streak multiplier (days).  τ = 30 aligns with the ~4-week
# habit-formation window in behavioural research.
STREAK_TAU_DAYS: float = 30.0

# Horizons returned by every compute_outlook call (months).
_HORIZONS: list[int] = [3, 6, 12]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_outlook(
    patient_id: str,  # noqa: ARG001 — accepted for caller convenience/logging; not used in math
    current_score: float,
    streak_days: int,
    protocol_adherence: float,
) -> dict[int, float]:
    """Compute the vitality outlook projection for a set of time horizons.

    The function is **pure**: the same inputs always return the same outputs.
    ``patient_id`` is accepted for caller convenience (e.g. structured logging)
    but is not used in the calculation.

    Capped-ceiling multiplicative model (docs/10-vitality-formula.md §5):

      - ``streak_days ≤ 0`` OR ``adherence ≤ 0.0`` → flat at ``current_score``.
      - ``current_score ≥ CEILING`` → reachable gap is 0; result is ``current_score``.
      - Later horizons project higher (horizon_factor grows from 3m → 12m).
      - Result is always in [current_score, CEILING].

    Args:
        patient_id:          Patient identifier (not used in math; for logging).
        current_score:       Present Vitality Score on the 0–100 scale.
        streak_days:         Number of consecutive days the protocol was followed.
                             Zero or negative means the streak is broken or never started.
        protocol_adherence:  Fractional measure of how closely the patient followed
                             the protocol (0.0 = none, 1.0 = perfect).

    Returns:
        A ``dict[int, float]`` with keys ``{3, 6, 12}`` (horizon in months),
        each mapping to the projected Vitality Score at that horizon.
    """
    # ------------------------------------------------------------------
    # Edge case: broken streak or zero adherence → flat at current_score
    # ------------------------------------------------------------------
    if streak_days <= 0 or protocol_adherence <= 0.0:
        return {h: float(current_score) for h in _HORIZONS}

    # ------------------------------------------------------------------
    # Streak multiplier: saturating exponential (0 at s=0, →1 as s→∞)
    # ------------------------------------------------------------------
    streak_mult = 1.0 - math.exp(-streak_days / STREAK_TAU_DAYS)

    # ------------------------------------------------------------------
    # Reachable gap: how much room is left below the ceiling
    # clamped to 0 so above-ceiling scores don't create negative gains
    # ------------------------------------------------------------------
    reachable_gap = max(0.0, CEILING - current_score)

    # ------------------------------------------------------------------
    # Per-horizon projection
    # ------------------------------------------------------------------
    projections: dict[int, float] = {}
    for h, hf in HORIZON_FACTOR.items():
        gain = reachable_gap * protocol_adherence * streak_mult * hf
        projected = current_score + gain
        # Clamp: never below current_score, never above CEILING.
        # Use max(current_score, CEILING) as the upper bound so that scores
        # already above the ceiling are not dragged down by the CEILING cap.
        upper = max(float(current_score), CEILING)
        projected = max(projected, float(current_score))
        projected = min(projected, upper)
        projections[h] = float(projected)

    return projections
