import pytest

from closxom.pubdate import InvalidPublishedValue, parse_published

ZONE = "America/New_York"


def test_bare_date_is_noon_in_zone_summer():
    # EDT is UTC-4
    assert parse_published("2027-06-01", ZONE) == "2027-06-01T16:00:00+00:00"


def test_bare_date_is_noon_in_zone_winter():
    # EST is UTC-5
    assert parse_published("2027-01-01", ZONE) == "2027-01-01T17:00:00+00:00"


def test_bare_date_uses_the_given_zone():
    assert parse_published("2027-06-01", "UTC") == "2027-06-01T12:00:00+00:00"


def test_zoneless_datetime_is_wall_time_in_zone():
    assert parse_published("2027-06-01T09:00:00", ZONE) == "2027-06-01T13:00:00+00:00"


def test_offset_bearing_datetime_is_taken_as_is():
    assert parse_published("2027-06-01T09:00:00+09:00", ZONE) == "2027-06-01T00:00:00+00:00"


def test_z_suffix_means_utc():
    assert parse_published("2027-06-01T00:00:00Z", ZONE) == "2027-06-01T00:00:00+00:00"


def test_surrounding_whitespace_is_tolerated():
    assert parse_published("  2027-06-01  ", ZONE) == "2027-06-01T16:00:00+00:00"


@pytest.mark.parametrize("value", [
    "0",                          # the retired magic sentinel
    "1234567890",                 # unix timestamp
    "2027/06/01",                 # slash-separated date
    "2027-06-01T09:00:00.500",    # fractional seconds
    "2027-06-01 09:00:00",        # space instead of T
    "soon",
    "",
])
def test_rejects_anything_else(value):
    with pytest.raises(InvalidPublishedValue):
        parse_published(value, ZONE)


def test_unknown_zone_name_raises():
    from zoneinfo import ZoneInfoNotFoundError
    with pytest.raises(ZoneInfoNotFoundError):
        parse_published("2027-06-01", "Not/AZone")
