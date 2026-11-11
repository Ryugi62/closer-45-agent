"""Pure domain objects. No I/O, no frameworks."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import date
from typing import Optional

MSME_STATUSES = ("micro", "small", "medium_or_large", "unknown")


@dataclass(frozen=True)
class Supplier:
    id: str
    name: str
    msme_status: str


@dataclass(frozen=True)
class Invoice:
    id: str
    supplier_id: str
    invoice_no: str
    amount: int  # rupees
    accepted_on: date
    agreed_days: Optional[int]  # None = no written agreement

    @property
    def norm_no(self) -> str:
        return self.invoice_no.strip().upper()

    @property
    def pay_key(self) -> str:
        return "pay:%s:%s" % (self.supplier_id, self.norm_no)


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PayStep:
    """Irreversible. Needs an approved digest."""
    key: str
    invoice_id: str
    supplier_id: str
    payee: str
    amount: int
    days_left: int
    reason: str
    kind: str = "pay"

    def digest(self) -> str:
        return _digest("pay", self.key, self.payee, self.amount)

    def with_amount(self, amount: int) -> "PayStep":
        return replace(self, amount=amount)


@dataclass(frozen=True)
class EmailStep:
    """External message. Shown on the same approval card; the body is part of the digest."""
    key: str
    supplier_id: str
    supplier_name: str
    kind: str  # ask_status | reschedule
    reason: str
    detail: str = ""
    subject: str = ""
    body: str = ""

    def digest(self) -> str:
        return _digest("mail", self.key, self.supplier_id, self.subject, self.body)

    def drafted(self, subject: str, body: str) -> "EmailStep":
        return replace(self, subject=subject, body=body)


@dataclass(frozen=True)
class Held:
    invoice_id: str
    reason: str


@dataclass(frozen=True)
class Uncovered:
    invoice_id: str
    supplier_id: str
    amount: int
    days_left: int
