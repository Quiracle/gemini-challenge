from __future__ import annotations

from typing import Any

from nba_ingestion.models import DataQualityError


def clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def to_int(value: Any, field_name: str, allow_none: bool = True) -> int | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise DataQualityError(f"{field_name} is required but was null")
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise DataQualityError(f"{field_name} expected integer-compatible value: {value!r}") from exc


def to_float(value: Any, field_name: str, allow_none: bool = True) -> float | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise DataQualityError(f"{field_name} is required but was null")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise DataQualityError(f"{field_name} expected float-compatible value: {value!r}") from exc


def to_league_id(value: Any) -> str:
    text = clean_string(value)
    if text is None:
        raise DataQualityError("LEAGUE_ID is required but was null")
    if text.isdigit() and len(text) < 2:
        return text.zfill(2)
    return text
