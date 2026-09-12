import pytest

from rdspan.drills import IllegalTransition, ParadigmMachine, ScriptoriumMachine


def test_paradigm_rep_on_repeat():
    m = ParadigmMachine("idle", 0, 3).open()
    assert m.state == "preview"
    m = m.ack_repeat()
    assert m.reps == 1
    assert m.state == "scored"
    m = m.ack_repeat()
    assert m.reps == 2
    m = m.ack_repeat()
    assert m.reps == 3
    assert m.state == "mastered"


def test_paradigm_mastered_stays_mastered():
    m = ParadigmMachine("preview", 2, 3).ack_repeat()
    assert m.state == "mastered"
    assert m.reps == 3
    extra = m.ack_repeat()
    assert extra.state == "mastered"
    assert extra.reps == 4


def test_legacy_recite_state_opens_to_preview():
    m = ParadigmMachine("recite", 1, 100).open()
    assert m.state == "preview"
    assert m.reps == 1


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


def test_scriptorium_illegal_write_before_say():
    with pytest.raises(IllegalTransition):
        ScriptoriumMachine("listen", True, False, False).score_write(True)
