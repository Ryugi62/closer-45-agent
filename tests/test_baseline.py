"""Measured comparison on the synthetic ledger: pay in ledger order vs the Closer plan."""
from datetime import date

from closer45.adapters.ledger_csv import CsvLedger
from closer45.domain.planner import build_plan
from closer45.domain.rules import due_date
from helpers import DATA, TODAY

CHECK_DAY = date(2026, 3, 16)


def missed(invoices, suppliers, paid_ids):
    sup = {s.id: s for s in suppliers}
    n, seen = 0, set()
    for inv in invoices:
        ident = (inv.supplier_id, inv.norm_no)
        if ident in seen:  # a duplicate row is the same debt, count it once
            continue
        seen.add(ident)
        due = due_date(inv, sup[inv.supplier_id])
        paid = inv.id in paid_ids or any(i.id in paid_ids and (i.supplier_id, i.norm_no) == ident for i in invoices)
        if due and due <= CHECK_DAY and not paid:
            n += 1
    return n


def ledger_order_paid(invoices, budget):
    paid, left = set(), budget
    for inv in invoices:  # naive: ledger order, no dedupe, no deadline awareness
        if inv.amount <= left:
            left -= inv.amount
            paid.add(inv.id)
    return paid


def test_closer_misses_fewer_deadlines_than_ledger_order():
    invoices, suppliers = CsvLedger(DATA).load()
    base_paid = ledger_order_paid(invoices, 400000)
    plan = build_plan(invoices, suppliers, cash=450000, reserve=50000, today=TODAY)
    closer_paid = {s.invoice_id for s in plan.pay_steps}
    assert missed(invoices, suppliers, base_paid) == 1  # L-7 (due 12 Mar) left unpaid
    assert missed(invoices, suppliers, closer_paid) == 0
