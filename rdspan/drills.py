"""Drill state machines. No conjugation happens here — forms are looked up only."""

from __future__ import annotations

from dataclasses import dataclass


class IllegalTransition(ValueError):
    pass


PARADIGM_STATES = ("idle", "preview", "scored", "mastered")
SCRIPTORIUM_STATES = ("idle", "listen", "say", "write", "done")


@dataclass(frozen=True)
class ParadigmMachine:
    state: str
    reps: int
    target: int

    def open(self) -> ParadigmMachine:
        if self.state in ("idle", "recite"):
            return ParadigmMachine("preview", self.reps, self.target)
        return self

    def ack_repeat(self) -> ParadigmMachine:
        """Honor-system: heard the table and repeated it aloud. Counts one rep."""
        current = self.open() if self.state in ("idle", "recite") else self
        reps = current.reps + 1
        if reps >= current.target:
            return ParadigmMachine("mastered", reps, current.target)
        return ParadigmMachine("scored", reps, current.target)

    @property
    def remaining(self) -> int:
        return max(0, self.target - self.reps)


@dataclass(frozen=True)
class ScriptoriumMachine:
    state: str
    listen_ok: bool
    say_ok: bool
    write_ok: bool

    @property
    def complete(self) -> bool:
        return self.listen_ok and self.say_ok and self.write_ok

    def open(self) -> ScriptoriumMachine:
        if self.complete:
            return ScriptoriumMachine("done", True, True, True)
        if self.state == "idle":
            return ScriptoriumMachine("listen", self.listen_ok, self.say_ok, self.write_ok)
        return self

    def ack_listen(self) -> ScriptoriumMachine:
        if self.state not in ("idle", "listen"):
            raise IllegalTransition("Ya escuchaste; ahora di la frase")
        nxt = "done" if self.say_ok and self.write_ok else "say"
        return ScriptoriumMachine(nxt, True, self.say_ok, self.write_ok)

    def score_say(self, passed: bool) -> ScriptoriumMachine:
        if self.state != "say":
            raise IllegalTransition("Di la frase después de oírla")
        if not passed:
            return ScriptoriumMachine("say", True, False, self.write_ok)
        nxt = "done" if self.write_ok else "write"
        return ScriptoriumMachine(nxt, True, True, self.write_ok)

    def score_write(self, passed: bool) -> ScriptoriumMachine:
        if self.state != "write":
            raise IllegalTransition("Escríbela después de decirla")
        if not passed:
            return ScriptoriumMachine("write", True, True, False)
        return ScriptoriumMachine("done", True, True, True)
