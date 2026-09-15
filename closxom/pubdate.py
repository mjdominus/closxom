"""Parse META `published:` values into UTC instants.

See notes/redesign-decisions.md, "Timezone semantics" and "process_meta",
for the design this implements.
"""

import re
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

_DATE_RE = re.compile(r'''
    \A
    ( \d{4} - \d{2} - \d{2} )      # YYYY-MM-DD
    \Z
''', re.VERBOSE)

_DATETIME_RE = re.compile(r'''
    \A
    \d{4} - \d{2} - \d{2}          # YYYY-MM-DD
    T
    \d{2} : \d{2} : \d{2}          # hh:mm:ss
    (?P<offset>
        Z                          # UTC, or
      | [+-] \d{2} : \d{2}         # an explicit offset
    )?
    \Z
''', re.VERBOSE)


class InvalidPublishedValue(ValueError):
    """Raised when a `published:` value is not one of the accepted forms."""


def parse_published(value, zone_name):
    """Parse a META `published:` value into a UTC instant.

    Accepts exactly three forms:
      - YYYY-MM-DD           -> noon in the given zone
      - YYYY-MM-DDThh:mm:ss  -> that wall-clock time in the given zone
      - YYYY-MM-DDThh:mm:ss with an explicit offset, or a trailing Z ->
        that instant, taken as-is

    zone_name is an IANA timezone name (e.g. "America/New_York"), used to
    interpret the first two forms. Anything else - including a unix
    timestamp, a YYYY/MM/DD date, or a fractional-second time - raises
    InvalidPublishedValue.

    Returns a UTC ISO-8601 string, e.g. "2027-05-31T20:00:00+00:00".
    """
    value = value.strip()

    date_match = _DATE_RE.match(value)
    if date_match:
        zone = ZoneInfo(zone_name)
        local = datetime.combine(date.fromisoformat(date_match.group(1)),
                                  time(12, 0, 0), tzinfo=zone)
        return local.astimezone(timezone.utc).isoformat()

    datetime_match = _DATETIME_RE.match(value)
    if datetime_match:
        if datetime_match.group('offset'):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(zone_name))
        return dt.astimezone(timezone.utc).isoformat()

    raise InvalidPublishedValue(
        f"published value {value!r} is not YYYY-MM-DD, YYYY-MM-DDThh:mm:ss, "
        f"or an offset/Z-qualified variant of the latter"
    )
