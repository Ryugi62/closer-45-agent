import json
import os
from typing import Dict, List, Optional


class OutboxMail:
    """Mock mail: appends to an outbox file; replies come from a canned inbox list."""

    def __init__(self, outbox_path: str, inbox: Optional[List[Dict[str, str]]] = None):
        self.outbox_path = outbox_path
        self.inbox = inbox or []

    def send(self, step) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.outbox_path)), exist_ok=True)
        with open(self.outbox_path, "a") as f:
            f.write(json.dumps({"to": step.supplier_id, "subject": step.subject, "body": step.body,
                                "key": step.key}, sort_keys=True) + "\n")

    def fetch_replies(self) -> List[Dict[str, str]]:
        return list(self.inbox)
