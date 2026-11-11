import sys
from typing import Dict


class ScriptedApprover:
    """Stands in for the human in tests and in the recorded demo (the demo says so on screen).
    modes: all | none | except:<key>,<key>"""

    def __init__(self, mode: str = "all"):
        self.mode = mode

    def decide(self, card) -> Dict[str, str]:
        if self.mode == "none":
            return {}
        skip = set()
        if self.mode.startswith("except:"):
            skip = set(self.mode[len("except:"):].split(","))
        return {s.key: s.digest() for s in card.steps if s.key not in skip}


class InteractiveApprover:
    """Real human at a terminal: y/n per step."""

    def __init__(self, stream_in=None, stream_out=None):
        self.i = stream_in or sys.stdin
        self.o = stream_out or sys.stdout

    def decide(self, card) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for s in card.steps:
            self.o.write("Approve %s? [y/N] " % s.key)
            self.o.flush()
            if self.i.readline().strip().lower() == "y":
                out[s.key] = s.digest()
        return out
