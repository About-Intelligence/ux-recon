"""Novelty scorer — determines if a captured state adds new information."""

from __future__ import annotations

from src.observer.fingerprint import DOMFingerprinter


class NoveltyScorer:
    """Scores how novel a page state is compared to previously seen states."""

    def __init__(self, fingerprinter: DOMFingerprinter):
        self._fingerprinter = fingerprinter
        self._seen_fingerprints: list[str] = []
        self._seen_details: list[dict] = []

    def score(self, html: str) -> tuple[float, str]:
        """Score novelty of HTML content. Returns (score 0-1, fingerprint hash).

        1.0 = completely new structure
        0.0 = exact duplicate of a seen state
        """
        fingerprint = self._fingerprinter.compute(html)

        if not self._seen_fingerprints:
            # First page is always novel
            return 1.0, fingerprint

        # Check exact fingerprint match
        if fingerprint in self._seen_fingerprints:
            return 0.0, fingerprint

        # Detailed comparison against all seen states
        details = self._fingerprinter.detailed_fingerprint(html)
        max_similarity = 0.0
        for seen in self._seen_details:
            sim = self._fingerprinter.detailed_similarity(details, seen)
            max_similarity = max(max_similarity, sim)

        novelty = 1.0 - max_similarity
        return novelty, fingerprint

    def register(self, html: str, fingerprint: str) -> None:
        """Register a state as 'seen' for future comparisons."""
        if fingerprint not in self._seen_fingerprints:
            self._seen_fingerprints.append(fingerprint)
            self._seen_details.append(self._fingerprinter.detailed_fingerprint(html))

    @property
    def seen_count(self) -> int:
        return len(self._seen_fingerprints)
