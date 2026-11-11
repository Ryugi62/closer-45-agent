"""The simplified MSME payment-deadline rule (synthetic model, not tax advice)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .models import Invoice, Supplier

MAX_DAYS = 45
NO_AGREEMENT_DAYS = 15
COVERED = ("micro", "small")


def legal_days(invoice: Invoice, supplier: Supplier, status: Optional[str] = None) -> Optional[int]:
    status = status or supplier.msme_status
    if status not in COVERED:
        return None
    if invoice.agreed_days is None:
        return NO_AGREEMENT_DAYS
    return min(invoice.agreed_days, MAX_DAYS)


def due_date(invoice: Invoice, supplier: Supplier, status: Optional[str] = None) -> Optional[date]:
    d = legal_days(invoice, supplier, status)
    return None if d is None else invoice.accepted_on + timedelta(days=d)


def days_left(invoice: Invoice, supplier: Supplier, today: date, status: Optional[str] = None) -> Optional[int]:
    due = due_date(invoice, supplier, status)
    return None if due is None else (due - today).days
