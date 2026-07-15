import re

_SAMPLE_ID_PATTERN = re.compile(r"^s-?(\d+)$", re.IGNORECASE)


def format_sample_id(sample_id: int) -> str:
    return f"S-{sample_id:03d}"


def parse_sample_id(text: str) -> int | None:
    stripped = text.strip()
    match = _SAMPLE_ID_PATTERN.match(stripped)
    if match:
        return int(match.group(1))
    if stripped.isdigit():
        return int(stripped)
    return None
