"""4-axis Verifier.

Given a Finding (and access to the KG for cross-pipeline context), assigns a
Verdict along REAL / TRIGGERABLE / IMPACTFUL / GENERAL axes.

Skeleton only — judging logic comes later.
"""

from __future__ import annotations

from .findings_kg import FindingsKG
from .models import Finding, Verdict


class Verifier:
    def __init__(self, kg: FindingsKG) -> None:
        self.kg = kg

    def verify(self, finding: Finding) -> Verdict:
        raise NotImplementedError
