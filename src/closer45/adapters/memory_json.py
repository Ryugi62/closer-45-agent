import json
import os


class JsonMemory:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path) as f:
                return json.load(f)
        return {"paid": [], "mail_sent": [], "replies": {}, "runs": 0}

    def save(self, state: dict) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(state, f, indent=2, sort_keys=True)
