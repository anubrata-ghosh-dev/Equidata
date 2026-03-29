from __future__ import annotations

from typing import Any


def build_mitigation_summary(before: dict[str, Any], after: dict[str, Any]) -> dict[str, float]:
    before_disparity = float(before.get("disparity", 0.0))
    after_disparity = float(after.get("disparity", 0.0))
    bias_reduction = before_disparity - after_disparity

    # Removing the sensitive feature helps reduce direct dependence on that attribute.
    # This is a simple mitigation baseline, but proxy features can still carry bias.
    fairness_score = max(0.0, 1.0 - after_disparity)
    return {
        "bias_reduction": float(bias_reduction),
        "fairness_score": float(fairness_score),
    }
