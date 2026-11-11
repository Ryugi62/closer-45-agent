import random

from closer45.adapters.ledger_csv import CsvLedger
from closer45.domain.planner import build_plan
from helpers import DATA, TODAY


def load():
    return CsvLedger(DATA).load()


def plan_of(invoices, suppliers, **kw):
    args = dict(cash=450000, reserve=50000, today=TODAY, paid_keys=frozenset(),
                asked_supplier_ids=frozenset(), known_status={})
    args.update(kw)
    return build_plan(invoices, suppliers, **args)


def test_pays_most_urgent_first_within_budget():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers)
    assert [s.invoice_id for s in p.pay_steps] == ["L-2", "L-7", "L-1"]
    assert sum(s.amount for s in p.pay_steps) <= 400000


def test_overdue_reason_and_days_left():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers)
    first = p.pay_steps[0]
    assert first.days_left < 0 and "overdue" in first.reason


def test_unknown_supplier_gets_email_not_payment():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers)
    assert [e.supplier_id for e in p.email_steps if e.kind == "ask_status"] == ["S4"]
    assert all(s.supplier_id != "S4" for s in p.pay_steps)


def test_already_asked_supplier_is_not_asked_again():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers, asked_supplier_ids=frozenset(["S4"]))
    assert not [e for e in p.email_steps if e.kind == "ask_status"]


def test_duplicate_ledger_row_is_flagged_and_not_paid():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers)
    assert "L-6" in [h.invoice_id for h in p.held if h.reason.startswith("duplicate")]
    assert "L-6" not in [s.invoice_id for s in p.pay_steps]


def test_uncovered_invoice_gets_reschedule_email():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers)
    assert [u.invoice_id for u in p.uncovered] == ["L-3"]
    assert [e.supplier_id for e in p.email_steps if e.kind == "reschedule"] == ["S5"]


def test_non_msme_is_not_paid_early():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers)
    assert "L-4" in [h.invoice_id for h in p.held if "no statutory deadline" in h.reason]


def test_paid_keys_are_skipped():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers, paid_keys=frozenset(["pay:S2:BP-0442"]))
    assert "L-2" not in [s.invoice_id for s in p.pay_steps]


def test_known_status_reply_unlocks_payment():
    invoices, suppliers = load()
    p = plan_of(invoices, suppliers, known_status={"S4": "small"}, cash=900000)
    assert "L-5" in [s.invoice_id for s in p.pay_steps]


def test_plan_is_order_independent_20_shuffles():
    invoices, suppliers = load()
    base = plan_of(invoices, suppliers).fingerprint()
    rng = random.Random(7)
    for _ in range(20):
        shuffled = list(invoices)
        rng.shuffle(shuffled)
        assert plan_of(shuffled, suppliers).fingerprint() == base


def test_never_exceeds_budget():
    invoices, suppliers = load()
    for cash in (0, 50000, 100000, 130000, 250000, 450000, 2000000):
        p = plan_of(invoices, suppliers, cash=cash)
        assert sum(s.amount for s in p.pay_steps) <= max(0, cash - 50000)
