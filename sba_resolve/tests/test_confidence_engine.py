from sba_resolve.core.metadata.confidence_engine import ConfidenceEngine


def test_datetimeoriginal_has_highest_score():
    assert ConfidenceEngine.score("DateTimeOriginal") == 100


def test_createdate_score():
    assert ConfidenceEngine.score("CreateDate") == 95


def test_mediacreatedate_score():
    assert ConfidenceEngine.score("MediaCreateDate") == 90


def test_gps_score():
    assert ConfidenceEngine.score("GPSDateTime") == 85


def test_unknown_score():
    assert ConfidenceEngine.score("Unknown") == 0