from datetime import datetime

from sba_resolve.core.models.timestamp_candidate import TimestampCandidate


def test_candidate_fields():

    dt = datetime(2026, 7, 12, 9, 14, 22)

    c = TimestampCandidate(
        confidence=100,
        timestamp=dt,
        source="DateTimeOriginal",
    )

    assert c.timestamp == dt
    assert c.source == "DateTimeOriginal"
    assert c.confidence == 100
    assert c.valid is True


def test_candidate_sorting():

    dt = datetime.now()

    a = TimestampCandidate(95, dt, "CreateDate")
    b = TimestampCandidate(100, dt, "DateTimeOriginal")

    result = sorted([a, b], reverse=True)

    assert result[0].confidence == 100