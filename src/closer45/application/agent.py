"""The agent loop: observe -> plan -> draft -> ask a human -> act -> remember."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Dict, List, Optional

from ..domain.errors import ApprovalMismatch, BankError
from ..domain.models import EmailStep, PayStep
from ..domain.planner import Plan, build_plan


@dataclass
class ApprovalCard:
    summary: str
    cash: int
    reserve: int
    steps: list  # PayStep | EmailStep
    held: list
    uncovered: list


@dataclass
class CycleReport:
    today: str
    plan_fingerprint: str
    card_summary: str
    executed: List[PayStep] = field(default_factory=list)
    sent_emails: List[str] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)
    parked: List[PayStep] = field(default_factory=list)
    retries: Dict[str, int] = field(default_factory=dict)
    balance_before: int = 0
    balance_after: int = 0
    tools_used: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)
    memory_snapshot: dict = field(default_factory=dict)
    plan: Optional[Plan] = None

    def to_dict(self) -> dict:
        return {
            "today": self.today,
            "plan": self.plan_fingerprint,
            "executed": [s.key for s in self.executed],
            "sent_emails": list(self.sent_emails),
            "rejected": list(self.rejected),
            "parked": [s.key for s in self.parked],
            "retries": dict(self.retries),
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "tools_used": sorted(set(self.tools_used)),
            "trace": list(self.trace),
        }


class CloserAgent:
    def __init__(self, ledger, mail, bank, memory, llm, approver, reserve: int = 0, max_retries: int = 2):
        self.ledger, self.mail, self.bank = ledger, mail, bank
        self.memory, self.llm, self.approver = memory, llm, approver
        self.reserve, self.max_retries = reserve, max_retries
        self.tamper: Optional[Callable[[PayStep], PayStep]] = None  # test hook: change a step after approval

    def run_cycle(self, today: date) -> CycleReport:
        tools: List[str] = []
        trace: List[str] = []

        def note(msg: str) -> None:
            trace.append(msg)

        mem = self.memory.load()
        note("memory: %d paid, %d mails sent, %d replies" % (len(mem["paid"]), len(mem["mail_sent"]), len(mem["replies"])))

        tools.append("mail.fetch")
        for r in self.mail.fetch_replies():
            mem["replies"][r["supplier_id"]] = r["msme_status"]
            note("reply from %s: %s" % (r["supplier_id"], r["msme_status"]))

        tools.append("ledger.read")
        invoices, suppliers = self.ledger.load()
        tools.append("bank.balance")
        cash = self.bank.balance()
        note("observed %d ledger rows, cash Rs %d, reserve Rs %d" % (len(invoices), cash, self.reserve))

        plan = build_plan(invoices, suppliers, cash=cash, reserve=self.reserve, today=today,
                          paid_keys=frozenset(mem["paid"]), known_status=dict(mem["replies"]),
                          sent_mail_keys=frozenset(mem["mail_sent"]))
        note("plan: %d payments, %d emails, %d held, %d uncovered, budget Rs %d" % (
            len(plan.pay_steps), len(plan.email_steps), len(plan.held), len(plan.uncovered), plan.budget))

        emails = []
        for e in plan.email_steps:
            subject, body = self.llm.draft_email(e)
            emails.append(e.drafted(subject, body))
        steps = list(plan.pay_steps) + emails
        summary = self.llm.explain({
            "pay": [(s.payee, s.amount, s.reason) for s in plan.pay_steps],
            "emails": [(e.supplier_name, e.kind) for e in emails],
            "uncovered": [(u.invoice_id, u.amount) for u in plan.uncovered],
            "cash": cash, "reserve": self.reserve,
        })
        card = ApprovalCard(summary, cash, self.reserve, steps, list(plan.held), list(plan.uncovered))

        report = CycleReport(today.isoformat(), plan.fingerprint(), summary, balance_before=cash, plan=plan)
        approved = self.approver.decide(card) if steps else {}
        note("human approved %d of %d steps" % (len(approved), len(steps)))
        approved_digest = {s.key: approved[s.key] for s in steps if s.key in approved and approved[s.key] == s.digest()}
        report.rejected = [s.key for s in steps if s.key not in approved_digest]

        for step in steps:
            if step.key not in approved_digest:
                continue
            if isinstance(step, PayStep):
                self._pay(step, approved_digest[step.key], mem, report, tools, note)
            else:
                tools.append("mail.send")
                self.mail.send(step)
                mem["mail_sent"].append(step.key)
                report.sent_emails.append(step.key)
                note("sent %s to %s" % (step.kind, step.supplier_name))

        tools.append("bank.balance")
        report.balance_after = self.bank.balance()
        mem["runs"] = mem.get("runs", 0) + 1
        self.memory.save(mem)
        report.tools_used = tools
        report.trace = trace
        report.memory_snapshot = mem
        return report

    def _pay(self, step: PayStep, digest: str, mem: dict, report: CycleReport, tools: list, note) -> None:
        shown = self.tamper(step) if self.tamper else step
        tools.append("bank.status")
        if self.bank.status(step.key) == "applied":
            note("%s already applied at the bank, marking paid without paying again" % step.key)
            mem["paid"].append(step.key)
            return
        attempts = 0
        last_error = ""
        while attempts <= self.max_retries:
            attempts += 1
            try:
                tools.append("bank.pay")
                self.bank.pay(shown.key, shown.payee, shown.amount, digest)
                mem["paid"].append(step.key)
                report.executed.append(step)
                note("paid Rs %d to %s (%s)" % (step.amount, step.payee, step.reason))
                break
            except ApprovalMismatch:
                note("bank refused %s: approved digest does not match, nothing moved" % step.key)
                raise
            except BankError as exc:
                last_error = str(exc)
                tools.append("bank.status")
                if self.bank.status(step.key) == "applied":
                    note("%s: %s, but the bank shows it applied, not paying again" % (step.key, last_error))
                    mem["paid"].append(step.key)
                    report.executed.append(step)
                    break
                note("%s failed (%s), attempt %d" % (step.key, last_error, attempts))
        else:
            report.parked.append(step)
            note("parked %s after %d attempts: %s" % (step.key, attempts, last_error))
        if attempts > 1:
            report.retries[step.key] = attempts - 1
