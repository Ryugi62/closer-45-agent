import json
import os

import pytest

from closer45.domain.errors import ApprovalMismatch
from helpers import TODAY, make_agent


def bank_txns(tmp):
    with open(os.path.join(str(tmp), "bank_state.json")) as f:
        return json.load(f)["txns"]


def test_happy_path_pays_three_and_sends_two_emails(tmp_path):
    r = make_agent(tmp_path).run_cycle(TODAY)
    assert sorted(bank_txns(tmp_path)) == ["pay:S1:AF/2026/118", "pay:S2:BP-0442", "pay:S2:BP-0460"]
    assert len(r.sent_emails) == 2
    assert r.balance_after == 450000 - 375000


def test_uses_at_least_two_tools(tmp_path):
    r = make_agent(tmp_path).run_cycle(TODAY)
    assert {"ledger.read", "bank.balance", "bank.pay", "mail.send"} <= set(r.tools_used)


def test_nothing_happens_without_approval(tmp_path):
    r = make_agent(tmp_path, approve="none").run_cycle(TODAY)
    assert bank_txns(tmp_path) == {}
    assert r.sent_emails == [] and r.rejected


def test_partial_approval_only_runs_approved(tmp_path):
    make_agent(tmp_path, approve="except:pay:S2:BP-0442").run_cycle(TODAY)
    assert "pay:S2:BP-0442" not in bank_txns(tmp_path)
    assert "pay:S1:AF/2026/118" in bank_txns(tmp_path)


def test_second_run_does_not_pay_or_ask_again(tmp_path):
    make_agent(tmp_path).run_cycle(TODAY)
    r2 = make_agent(tmp_path).run_cycle(TODAY)
    assert r2.executed == [] and r2.sent_emails == []
    assert len(bank_txns(tmp_path)) == 3


def test_memory_reply_next_day_pays_unknown_supplier(tmp_path):
    make_agent(tmp_path).run_cycle(TODAY)
    r2 = make_agent(tmp_path, inbox=[{"supplier_id": "S4", "msme_status": "small"}]).run_cycle(TODAY)
    assert r2.memory_snapshot["replies"] == {"S4": "small"}
    assert "L-5" in [u.invoice_id for u in r2.plan.uncovered]  # now classified, but cash is short
    assert "mail:ask_status:S4" in r2.memory_snapshot["mail_sent"]
    assert [k for k in r2.sent_emails if "ask_status" in k] == []


def test_changed_amount_after_approval_moves_nothing(tmp_path):
    agent = make_agent(tmp_path)
    agent.tamper = lambda step: step.with_amount(step.amount + 1)
    with pytest.raises(ApprovalMismatch):
        agent.run_cycle(TODAY)
    assert bank_txns(tmp_path) == {}


def test_transient_error_is_retried_then_succeeds(tmp_path):
    agent = make_agent(tmp_path, faults={"pay:S2:BP-0442": ["error", "error"]})
    r = agent.run_cycle(TODAY)
    assert "pay:S2:BP-0442" in bank_txns(tmp_path)
    assert r.retries["pay:S2:BP-0442"] == 2 and not r.parked


def test_persistent_error_parks_step_after_two_retries(tmp_path):
    agent = make_agent(tmp_path, faults={"pay:S2:BP-0442": ["error"] * 5})
    r = agent.run_cycle(TODAY)
    assert "pay:S2:BP-0442" not in bank_txns(tmp_path)
    assert [p.key for p in r.parked] == ["pay:S2:BP-0442"]
    assert "pay:S1:AF/2026/118" in bank_txns(tmp_path)


def test_timeout_after_apply_does_not_double_pay(tmp_path):
    agent = make_agent(tmp_path, faults={"pay:S1:AF/2026/118": ["timeout_after_apply"]})
    r = agent.run_cycle(TODAY)
    txns = bank_txns(tmp_path)
    assert txns["pay:S1:AF/2026/118"]["count"] == 1
    assert r.balance_after == 450000 - 375000
