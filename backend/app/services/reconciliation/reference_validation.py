"""Local, offline validation for accepted reconciliation references.

The Authority Service owns the record URI rules. This module mirrors those rules
for Shape Shifter without importing the Authority Service package or contacting
any service, so a save never depends on a reachable Authority instance.

The validator checks the URI shape, the expected type segment, and the numeric ID.
It cannot establish that the target exists, and it cannot tell a country
``location_id`` from another location type; export verification covers those
checks.
"""

from urllib.parse import urlsplit

# PostgreSQL stores target primary keys in ``integer`` columns.
POSTGRES_INTEGER_MAX = 2_147_483_647


def parse_record_uri(candidate_id: str, entity_type: str) -> int | None:
    """Return the positive record ID encoded in ``candidate_id``, or ``None``.

    A valid reference is an absolute URI with a scheme and host, no query string
    or fragment, whose last two path segments are ``entity_type`` and a positive
    ASCII decimal ID that fits a PostgreSQL ``integer``. Leading zeros are
    accepted.
    """
    if not isinstance(candidate_id, str) or not candidate_id:
        return None
    # The Authority Service rejects these characters before parsing, which also
    # keeps a stray '?' or '#' from changing the parsed path.
    if "?" in candidate_id or "#" in candidate_id:
        return None
    try:
        parsed = urlsplit(candidate_id)
    except ValueError:
        return None
    if not parsed.scheme or not parsed.netloc or parsed.query or parsed.fragment:
        return None

    path_segments = parsed.path.split("/")
    if len(path_segments) < 2:
        return None
    type_segment, id_segment = path_segments[-2], path_segments[-1]
    if type_segment != entity_type:
        return None
    if not id_segment.isascii() or not id_segment.isdecimal():
        return None
    try:
        record_id = int(id_segment)
    except ValueError:
        return None
    if not 0 < record_id <= POSTGRES_INTEGER_MAX:
        return None
    return record_id


def accepted_reference_error(candidate_id: str | None, target_id: int | None, entity_type: str | None) -> str | None:
    """Return why an accepted reference is invalid, or ``None`` when it is valid."""
    if not entity_type:
        return "The reconciliation specification has no remote service type"
    if target_id is None:
        return "An accepted decision requires a numeric target ID"
    if not candidate_id or not candidate_id.strip():
        return "An accepted decision requires a selected candidate URI"
    record_id = parse_record_uri(candidate_id, entity_type)
    if record_id is None:
        return (
            f"The candidate URI must be an absolute {entity_type} reference ending in "
            f"'/{entity_type}/<positive integer ID>' with no query or fragment: {candidate_id!r}"
        )
    if record_id != target_id:
        return "The selected candidate URI does not match the supplied target ID"
    return None
