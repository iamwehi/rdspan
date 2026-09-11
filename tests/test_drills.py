import pytest

from rdspan.drills import IllegalTransition, ParadigmMachine, ScriptoriumMachine


def test_paradigm_rep_only_on_passing_recite():
    m = ParadigmMachine("idle", 0, 3).open()
    assert m.state == "preview"
    m = m.begin_recite()
    failed = m.score_recite(False)
    assert failed.reps == 0
    assert failed.state == "scored"
    m = failed.begin_recite().score_recite(True)
    assert m.reps == 1
    assert m.state == "scored"


def test_paradigm_mastered_at_target():
    m = ParadigmMachine("recite", 2, 3).score_recite(True)
    assert m.state == "mastered"
    assert m.reps == 3
    # Extra practice cannot un-master.
    m = m.begin_recite().score_recite(False)
    assert m.state == "mastered"
    assert m.reps == 3


def test_cannot_score_from_preview():
    with pytest.raises(IllegalTransition):
        ParadigmMachine("preview", 0, 100).score_recite(True)


def test_scriptorium_page_complete_only_when_all_three():
    m = ScriptoriumMachine("idle", False, False, False).open()
    assert m.state == "listen"
    assert not m.complete
    m = m.ack_listen()
    assert m.listen_ok and m.state == "say"
    assert not m.complete
    m = m.score_say(False)
    assert m.state == "say" and not m.say_ok
    m = m.score_say(True)
    assert m.say_ok and m.state == "write"
    assert not m.complete
    m = m.score_write(True)
    assert m.complete
    assert m.state == "done"
