"""
SBA AI Studio
Capture Time Validator

Validates timestamp candidates before they are used by the
Capture Time Resolver.

Author: SBA AI Studio
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Final

# ----------------------------------------------------------------------
# Validation configuration
# ----------------------------------------------------------------------

MIN_YEAR: Final[int] = 1990

FUTURE_TOLERANCE_DAYS: Final[int] = 2


def is_valid_timestamp(value: datetime | None) -> bool:
    """
    Returns True if the timestamp is considered valid.

    Parameters
    ----------
    value
        Timestamp to validate.

    Returns
    -------
    bool
    """

    if value is None:
        return False

    if value.year < MIN_YEAR:
        return False

    max_date = datetime.now() + timedelta(days=FUTURE_TOLERANCE_DAYS)

    if value > max_date:
        return False

    return True