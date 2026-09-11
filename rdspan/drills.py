"""Drill state machines. No conjugation happens here — forms are looked up only."""

from __future__ import annotations

from dataclasses import dataclass


class IllegalTransition(ValueError):
    pass


PARADIGM_STATES = ("idle", "preview", "recite", "scored", "mastered")
SCRIPTORIUM_STATES = ("idle", "listen", "say", "write", "done")


@dataclass(frozen=True)
class ParadigmMachine:
    state: str
    reps: int
    target: int

    def open(self) -> ParadigmMachine:
        if self.state == "idle":
            return ParadigmMachine("preview", self.reps, self.target)
        return self

    def begin_recite(self) -> ParadigmMachine:
        if self.state not in ("preview", "scored", "mastered"):
            raise IllegalTransition(
                "Primero escucha la tabla (vista previa), luego recita."
            )
        return ParadigmMachine("recite", self.reps, self.target)

    def preview_again(self) -> ParadigmMachine:
        if self.state not in ("scored", "recite", "mastered", "preview"):
            raise IllegalTransition(f"No se puede volver a vista previa desde {self.state}")
        if self.state == "mastered":
            return self
        return ParadigmMachine("preview", self.reps, self.target)

    def score_recite(self, passed: bool) -> ParadigmMachine:
        if self.state != "recite":
            raise IllegalTransition("La rep solo cuenta en el paso de recitar")
        reps = self.reps + 1 if passed else self.reps
        if reps >= self.target:
            return ParadigmMachine("mastered", reps, self.target)
        return ParadigmMachine("scored", reps, self.target)

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
