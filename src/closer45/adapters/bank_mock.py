import hashlib
import json
import os
from typing import Dict, List, Optional

from ..domain.errors import ApprovalMismatch, BankError, TransientBankError  # noqa: F401


class MockBank:
    """Mock NEFT bank with idempotency keys, digest check and injectable faults.
    faults: {key: ["error" | "timeout_after_apply", ...]} consumed one per pay() call."""

    def __init__(self, path: str, balance: int = 0, faults: Optional[Dict[str, List[str]]] = None):
        self.path = path
        self.faults = {k: list(v) for k, v in (faults or {}).items()}
        if os.path.exists(path):
            with open(path) as f:
                self.state = json.load(f)
        else:
            self.state = {"balance": balance, "txns": {}}
            self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.state, f, indent=2, sort_keys=True)

    def balance(self) -> int:
        return self.state["balance"]

    def status(self, key: str) -> str:
        return "applied" if key in self.state["txns"] else "absent"

    def pay(self, key: str, payee: str, amount: int, approval_digest: str) -> None:
        expected = hashlib.sha256(("|".join(["pay", key, payee, str(amount)])).encode()).hexdigest()
        if approval_digest != expected:
            raise ApprovalMismatch("digest mismatch for %s" % key)
        fault = self.faults.get(key, []).pop(0) if self.faults.get(key) else None
        if fault == "error":
            raise TransientBankError("bank returned 503")
        if key not in self.state["txns"]:
            if amount > self.state["balance"]:
                raise BankError("insufficient funds")
            self.state["balance"] -= amount
            self.state["txns"][key] = {"payee": payee, "amount": amount, "count": 1}
            self._save()
        if fault == "timeout_after_apply":
            raise TransientBankError("timeout after the bank applied the payment")
