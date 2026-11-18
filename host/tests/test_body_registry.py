from maipai_body.bodies.registry import BODIES, selected


def test_the_default_body_is_reachy_mini_and_unknown_words_fall_back_to_it():
    assert selected({}).id == "reachy_mini"
    assert selected({"MAIPAI_BODY": "something-else"}).id == "reachy_mini"


def test_stackchan_and_fake_select_the_hosted_body():
    for word in ("stackchan", "STACKCHAN", " fake "):
        entry = selected({"MAIPAI_BODY": word})
        assert entry.id == "stackchan" and entry.hosted


def test_every_word_selects_one_body_only():
    words = [w for entry in BODIES for w in entry.words]
    assert len(words) == len(set(words))
