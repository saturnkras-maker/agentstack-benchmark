from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

RUN_TRACK_LOCAL_PUBLIC = "local-public"
RUN_TRACK_HOSTED_VERIFIED = "hosted-verified"
ALLOWED_RUN_TRACKS = {RUN_TRACK_LOCAL_PUBLIC, RUN_TRACK_HOSTED_VERIFIED}


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def stable_json_hash(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_run_track(track: str) -> str:
    if track not in ALLOWED_RUN_TRACKS:
        raise ValueError(f"track must be one of: {', '.join(sorted(ALLOWED_RUN_TRACKS))}")
    return track


def canonicalize_report(report: dict[str, Any]) -> dict[str, Any]:
    track = validate_run_track(str(report.get("track", RUN_TRACK_LOCAL_PUBLIC)))
    canonical: dict[str, Any] = {}
    if "schemaVersion" in report:
        canonical["schemaVersion"] = report["schemaVersion"]
    canonical["track"] = track
    for key, value in report.items():
        if key not in {"schemaVersion", "track"}:
            canonical[key] = value
    return canonical


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def normalize_for_match(value: str) -> str:
    """Deterministic, language-agnostic normalization for answer matching.

    Beyond :func:`normalize_text` (lowercase + whitespace collapse), this folds
    Unicode to its compatibility form, casefolds (locale-independent lower for
    non-ASCII scripts incl. Cyrillic/German), strips combining marks, and drops
    punctuation so that correct answers are not penalised by trivial surface
    differences (case, accents, quotes, trailing periods, en/em dashes). It is
    used only for scoring matches — never for redaction or hashing — so the
    frozen ``scoring_schema_v1`` artifact hash composition is unaffected.
    """
    folded = unicodedata.normalize("NFKD", value).casefold()
    out_chars: list[str] = []
    for ch in folded:
        category = unicodedata.category(ch)
        if category.startswith("M"):
            # Combining mark (accent) — drop so "é" == "e".
            continue
        if category.startswith("P") or category.startswith("S"):
            # Punctuation/symbol — treat as a separator.
            out_chars.append(" ")
            continue
        out_chars.append(ch)
    return " ".join("".join(out_chars).split())


def match_tokens(answer: str, expected_value: str) -> bool:
    """All whitespace-separated tokens of ``expected_value`` appear in ``answer``.

    Order-independent multi-keyword containment over the normalized token sets.
    A multi-word expectation like ``"quality speed safety"`` therefore matches an
    answer that mentions all three keywords in any order or wording — fixing the
    exact-substring brittleness — while still requiring every keyword to be present.
    """
    answer_tokens = set(normalize_for_match(answer).split())
    expected_tokens = normalize_for_match(expected_value).split()
    if not expected_tokens:
        return True
    return all(token in answer_tokens for token in expected_tokens)
