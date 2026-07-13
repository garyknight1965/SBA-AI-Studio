"""
Unit tests for the GoPro filename parser.
"""

from sba_resolve.capture_time.parsers.gopro import GoProFilenameParser


def test_gopro_mp4():
    parser = GoProFilenameParser()
    assert parser.can_parse("GH010245.MP4")


def test_gopro_lrv():
    parser = GoProFilenameParser()
    assert parser.can_parse("GH010245.LRV")


def test_gopro_thm():
    parser = GoProFilenameParser()
    assert parser.can_parse("GH010245.THM")


def test_invalid_filename():
    parser = GoProFilenameParser()
    assert not parser.can_parse("DJI_0001.MP4")


def test_random_filename():
    parser = GoProFilenameParser()
    assert not parser.can_parse("holiday_video.mp4")