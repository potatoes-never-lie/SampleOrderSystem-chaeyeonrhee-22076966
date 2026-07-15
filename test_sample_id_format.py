from model.sample_id_format import format_sample_id, parse_sample_id


def test_format_sample_id_pads_to_three_digits():
    assert format_sample_id(1) == "S-001"
    assert format_sample_id(42) == "S-042"
    assert format_sample_id(1234) == "S-1234"


def test_parse_sample_id_accepts_dash_format():
    assert parse_sample_id("S-003") == 3


def test_parse_sample_id_accepts_lowercase_and_no_dash():
    assert parse_sample_id("s003") == 3


def test_parse_sample_id_accepts_plain_digits():
    assert parse_sample_id("3") == 3


def test_parse_sample_id_strips_surrounding_whitespace():
    assert parse_sample_id("  S-003  ") == 3


def test_parse_sample_id_returns_none_for_non_matching_text():
    assert parse_sample_id("실리콘") is None
    assert parse_sample_id("") is None
    assert parse_sample_id("S-") is None
