"""Helpers for turning captured labels and paths into cleaner report text."""

from __future__ import annotations

import re
from urllib.parse import urlparse

LOCALE_SEGMENTS = {
    "ar", "cn", "de", "en", "es", "fr", "hk", "it", "ja", "jp",
    "ko", "pt", "ru", "tw", "zh",
}

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
MOJIBAKE_HINTS = ("鈥", "鍗", "浠", "杩", "绔", "鎻", "鏂", "诲", "鏉", "闂", "€")


def clean_report_text(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    if "\ufffd" in normalized:
        return ""
    repaired = _repair_mojibake(normalized)
    return repaired or normalized


def display_label(value: str) -> str:
    text = clean_report_text(value)
    if not text:
        return "unknown"
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower() in LOCALE_SEGMENTS:
        return "unknown"
    if _looks_plain_ascii_slug(text):
        return text.title()
    return text


def strip_site_suffix(title: str) -> str:
    text = clean_report_text(title)
    if not text:
        return ""
    return text.split("|", 1)[0].strip(" -|\t")


def module_path_from_url(url: str) -> str:
    parsed = urlparse(url)
    fragment = parsed.fragment.strip()
    if fragment:
        fragment_path = fragment.split("?", 1)[0].strip("/")
        if fragment_path:
            return _normalize_path(fragment_path)

    path = parsed.path.strip("/")
    if not path:
        return "root"
    return _normalize_path(path)


def route_family_from_url(url: str) -> str:
    path = module_path_from_url(url)
    if not path or path == "root":
        return "root"
    return path.split("/")[0]


def best_surface_label(
    *,
    url: str,
    title: str = "",
    capture_label: str = "",
    fallback: str = "",
) -> str:
    capture = clean_report_text(capture_label)
    if capture and not _looks_internal_capture_label(capture):
        return display_label(capture)

    title_label = strip_site_suffix(title)
    path_label = _path_label_from_url(url)
    if title_label and not _looks_internal_capture_label(title_label):
        if _looks_mojibake(title_label) and path_label:
            return path_label
        return title_label

    if path_label:
        return path_label

    fallback_label = clean_report_text(fallback)
    if fallback_label:
        return display_label(fallback_label)

    parsed = urlparse(url)
    return parsed.netloc or "root"


def _normalize_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if parts and parts[0].lower() in LOCALE_SEGMENTS:
        parts = parts[1:]
    if parts and parts[0].isdigit():
        parts = parts[1:]
    return "/".join(parts) if parts else "root"


def _path_label_from_url(url: str) -> str:
    path = module_path_from_url(url)
    if not path or path == "root":
        return ""

    parts = [part for part in path.split("/") if part and not UUID_RE.fullmatch(part)]
    if not parts:
        return ""

    last = parts[-1]
    if last == "dashboard" and len(parts) >= 2:
        prior = parts[-2]
        if prior == "legacy":
            return "Legacy Dashboard"
    if last == "subscription":
        return "Subscription"
    if last == "dashboard-legacy":
        return "Legacy Dashboard"
    if last == "ponder":
        return "Ponder List"
    if last == "space":
        return "Workspace"
    return display_label(last)


def _looks_internal_capture_label(label: str) -> bool:
    lowered = label.lower()
    if lowered in {"root", "unknown"}:
        return True
    if re.fullmatch(r"[a-z]{2}_[a-z0-9_]+", lowered):
        return True
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return True
    return False


def _looks_plain_ascii_slug(text: str) -> bool:
    lowered = text.lower()
    return lowered == text and bool(re.fullmatch(r"[a-z0-9 /]+", text))


def _repair_mojibake(text: str) -> str:
    if not _looks_mojibake(text):
        return text

    original_score = _readability_score(text)
    best = text
    best_score = original_score
    for encoding in ("gb18030", "gbk", "latin1", "cp1252"):
        try:
            candidate = text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            continue
        candidate = " ".join(candidate.split()).strip()
        if not candidate:
            continue
        score = _readability_score(candidate)
        if score > best_score:
            best = candidate
            best_score = score
    return best


def _looks_mojibake(text: str) -> bool:
    return any(hint in text for hint in MOJIBAKE_HINTS)


def _readability_score(text: str) -> int:
    readable = sum(
        1
        for char in text
        if char.isalnum() or "\u4e00" <= char <= "\u9fff" or char in {" ", "-", "/", "_", ":"}
    )
    penalty = text.count("?") * 2 + sum(text.count(hint) for hint in MOJIBAKE_HINTS)
    return readable - penalty
