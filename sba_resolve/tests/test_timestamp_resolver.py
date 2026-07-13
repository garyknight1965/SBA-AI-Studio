"""
SBA AI Studio
MI-002C Timestamp Resolver Tests
"""

from datetime import datetime

from core.timestamp_resolver import TimestampResolver


def test_datetimeoriginal():
    metadata = {
        "DateTimeOriginal": "2025:06:14 10:15:30"
    }

    result = TimestampResolver.resolve(metadata)

    assert result["timestamp"] == datetime(2025, 6, 14, 10, 15, 30)
    assert result["source"] == "DateTimeOriginal"
    assert result["confidence"] == "HIGH"


def test_createdate():
    metadata = {
        "CreateDate": "2025:06:14 10:15:30"
    }

    result = TimestampResolver.resolve(metadata)

    assert result["source"] == "CreateDate"
    assert result["confidence"] == "MEDIUM"


def test_media_createdate():
    metadata = {
        "MediaCreateDate": "2025:06:14 10:15:30"
    }

    result = TimestampResolver.resolve(metadata)

    assert result["source"] == "MediaCreateDate"
    assert result["confidence"] == "MEDIUM"


def test_file_createdate():
    metadata = {
        "FileCreateDate": "2025:06:14 10:15:30"
    }

    result = TimestampResolver.resolve(metadata)

    assert result["source"] == "FileCreateDate"
    assert result["confidence"] == "LOW"


def test_priority():
    metadata = {
        "FileModifyDate": "2025:06:14 11:11:11",
        "CreateDate": "2025:06:14 09:00:00",
        "DateTimeOriginal": "2025:06:14 08:00:00",
    }

    result = TimestampResolver.resolve(metadata)

    assert result["source"] == "DateTimeOriginal"
    assert result["timestamp"] == datetime(2025, 6, 14, 8, 0, 0)


def test_empty():
    result = TimestampResolver.resolve({})

    assert result["timestamp"] is None
    assert result["source"] is None
    assert result["confidence"] == "NONE"


def test_invalid_date():
    metadata = {
        "DateTimeOriginal": "Not a date"
    }

    result = TimestampResolver.resolve(metadata)

    assert result["timestamp"] is None
    assert result["confidence"] == "NONE"