"""Normalization utilities for evidence collection."""

from __future__ import annotations

import re
import unicodedata

from src.extraction.types import EvidenceUnit


class EvidenceNormalizer:
    """Normalizes evidence text and filters low-signal noise."""

    _whitespace_re = re.compile(r"\s+")
    _mojibake_replacements = {
        "鈥檚": "'s",
        "鈥檇": "'d",
        "鈥檛": "n't",
        "鈥檒": "'ll",
        "鈥檓": "'m",
        "鈥榮": "'s",
        "鈥�": '"',
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€“": "-",
        "â€”": "-",
    }

    def normalize_units(self, units: list[EvidenceUnit]) -> list[EvidenceUnit]:
        normalized: list[EvidenceUnit] = []
        seen: set[tuple[str, str, str]] = set()

        for unit in units:
            normalized_text = self.normalize_text(unit.raw_text)
            if not normalized_text:
                continue

            normalized_metadata = dict(unit.metadata)
            for key in ("summary", "href"):
                value = normalized_metadata.get(key)
                if isinstance(value, str):
                    normalized_metadata[key] = self.normalize_text(value, allow_empty=True)

            dedupe_key = (unit.kind, normalized_text, str(normalized_metadata.get("href", "")))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            unit.normalized_text = normalized_text
            unit.metadata = normalized_metadata
            normalized.append(unit)

        return normalized

    def normalize_text(self, text: str, allow_empty: bool = False) -> str:
        if not text:
            return ""

        for source, target in self._mojibake_replacements.items():
            text = text.replace(source, target)
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\xa0", " ").replace("\u200b", " ").replace("\ufeff", " ")

        cleaned_chars: list[str] = []
        for char in text:
            category = unicodedata.category(char)
            if category.startswith("C"):
                cleaned_chars.append(" ")
                continue
            cleaned_chars.append(char)
        text = "".join(cleaned_chars)
        text = self._whitespace_re.sub(" ", text).strip()
        if not text:
            return ""

        tokens = [token for token in text.split(" ") if token]
        cleaned_tokens = [token for token in tokens if not self._drop_token(token, tokens)]
        cleaned = " ".join(cleaned_tokens).strip(" -|•·•●■►▸▹▶▷»«")
        cleaned = self._whitespace_re.sub(" ", cleaned).strip()

        if not cleaned and allow_empty:
            return ""
        return cleaned

    def _drop_token(self, token: str, all_tokens: list[str]) -> bool:
        if not token:
            return True
        if token in {"/", "&", "@", "+"}:
            return False
        if all(unicodedata.category(char).startswith(("S", "P")) for char in token):
            return True
        if len(token) == 1 and ord(token) > 127:
            ascii_tokens = sum(1 for item in all_tokens if item.isascii())
            if ascii_tokens >= max(1, len(all_tokens) // 2):
                return True
        if "?" in token and not any(char.isalnum() for char in token):
            return True
        return False
