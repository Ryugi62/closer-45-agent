"""Deterministic planning kernel. The LLM never decides money: it only words messages."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Dict, FrozenSet, Iterable, List, Tuple

from .models import EmailStep, Held, Invoice, PayStep, Supplier, Uncovered
from .rules import COVERED, days_left, due_date


@dataclass(frozen=True)
class Plan:
    pay_steps: Tuple[PayStep, ...]
    email_steps: Tuple[EmailStep, ...]
    held: Tuple[Held, ...]
    uncovered: Tuple[Uncovered, ...]
    budget: int

    def fingerprint(self) -> str:
        return json.dumps({
            "budget": self.budget,
            "pay": [(s.key, s.amount) for s in self.pay_steps],
            "mail": [(e.key, e.kind) for e in self.email_steps],
            "held": sorted((h.invoice_id, h.reason) for h in self.held),
            "uncovered": sorted((u.invoice_id, u.amount) for u in self.uncovered),
        }, sort_keys=True)


def _reason(left: int) -> str:
    if left < 0:
        return "overdue by %d days" % (-left)
    if left == 0:
        return "due today"
    return "due in %d days" % left


def build_plan(invoices: Iterable[Invoice], suppliers: Iterable[Supplier], *, cash: int, reserve: int,
               today: date, paid_keys: FrozenSet[str] = frozenset(),
               asked_supplier_ids: FrozenSet[str] = frozenset(),
               known_status: Dict[str, str] = None,
               sent_mail_keys: FrozenSet[str] = frozenset()) -> Plan:
    known_status = known_status or {}
    sup = {s.id: s for s in suppliers}
    budget = max(0, cash - reserve)

    seen: Dict[Tuple[str, str], str] = {}
    held: List[Held] = []
    candidates: List[Tuple[int, str, Invoice, Supplier]] = []
    ask: Dict[str, Supplier] = {}

    for inv in sorted(invoices, key=lambda i: i.id):
        ident = (inv.supplier_id, inv.norm_no)
        if ident in seen:
            held.append(Held(inv.id, "duplicate of %s" % seen[ident]))
            continue
        seen[ident] = inv.id
        s = sup.get(inv.supplier_id)
        if s is None:
            held.append(Held(inv.id, "unknown supplier"))
            continue
        if inv.pay_key in paid_keys:
            held.append(Held(inv.id, "already paid"))
            continue
        status = known_status.get(s.id, s.msme_status)
        if status == "unknown":
            held.append(Held(inv.id, "supplier MSME status unknown, asking supplier"))
            if s.id not in asked_supplier_ids and ("mail:ask_status:%s" % s.id) not in sent_mail_keys:
                ask[s.id] = s
            continue
        if status not in COVERED:
            held.append(Held(inv.id, "no statutory deadline in this model (%s)" % status))
            continue
        candidates.append((days_left(inv, s, today, status), inv.id, inv, s))

    candidates.sort(key=lambda c: (c[0], c[1]))
    pay: List[PayStep] = []
    uncovered: List[Uncovered] = []
    left_budget = budget
    for left, _, inv, s in candidates:
        if inv.amount <= left_budget:
            left_budget -= inv.amount
            pay.append(PayStep(inv.pay_key, inv.id, s.id, s.name, inv.amount, left, _reason(left)))
        else:
            uncovered.append(Uncovered(inv.id, s.id, inv.amount, left))

    mails: List[EmailStep] = []
    for sid in sorted(ask):
        mails.append(EmailStep("mail:ask_status:%s" % sid, sid, ask[sid].name, "ask_status",
                               "MSME status unknown, deadline cannot be computed"))
    by_sup: Dict[str, List[Uncovered]] = {}
    for u in uncovered:
        by_sup.setdefault(u.supplier_id, []).append(u)
    inv_by_id = {i.id: i for i in invoices}
    for sid in sorted(by_sup):
        ids = ",".join(sorted(u.invoice_id for u in by_sup[sid]))
        key = "mail:reschedule:%s:%s" % (sid, ids)
        if key in sent_mail_keys:
            continue
        lines = []
        for u in sorted(by_sup[sid], key=lambda x: x.invoice_id):
            inv = inv_by_id[u.invoice_id]
            lines.append("%s (Rs %d, %s)" % (inv.invoice_no, u.amount, _reason(u.days_left)))
        mails.append(EmailStep(key, sid, sup[sid].name, "reschedule",
                               "cash this cycle does not cover it", detail="; ".join(lines)))
    return Plan(tuple(pay), tuple(mails), tuple(sorted(held, key=lambda h: h.invoice_id)),
                tuple(uncovered), budget)
