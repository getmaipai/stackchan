"""The privacy sentence is one text on the settings page and the robot's first-run screen."""

from maipai_body import i18n

SENTENCE = "Your voice and pictures stay in your home. Nothing goes to the internet unless you turn it on."


def test_the_settings_page_says_the_shared_privacy_sentence():
    assert i18n.CATALOG["en"]["settings.ui.fam.privacy"] == SENTENCE, (
        "The privacy sentence changed. Change the robot's first-run screen text in the same commit (docs/plan/privacy-sentence.md)."
    )
