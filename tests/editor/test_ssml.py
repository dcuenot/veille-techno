from src.editor.briefing import BriefingSegment
from src.editor.ssml import build_ssml


def test_build_ssml_wraps_in_speak_tag():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="outro", text="A demain."),
    ]
    ssml = build_ssml(segments)
    assert ssml.startswith("<speak>")
    assert ssml.endswith("</speak>")


def test_build_ssml_adds_breaks_between_segments():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="weather", text="Il fait beau."),
        BriefingSegment(type="outro", text="A demain."),
    ]
    ssml = build_ssml(segments)
    assert '<break time="800ms"/>' in ssml


def test_build_ssml_adds_long_break_before_tech():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
        BriefingSegment(type="news", text="L'essentiel."),
        BriefingSegment(type="news", text="Cote tech."),
        BriefingSegment(type="outro", text="A demain."),
    ]
    ssml = build_ssml(segments)
    assert '<break time="1200ms"/>' in ssml


def test_build_ssml_applies_prosody():
    segments = [
        BriefingSegment(type="intro", text="Bonjour."),
    ]
    ssml = build_ssml(segments)
    assert '<prosody rate="95%" volume="x-loud">' in ssml


def test_build_ssml_escapes_special_chars():
    segments = [
        BriefingSegment(type="news", text='L\'IA & le "cloud" <3'),
    ]
    ssml = build_ssml(segments)
    assert "&amp;" in ssml
    assert "<3" not in ssml  # < should be escaped
