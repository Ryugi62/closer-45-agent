import argparse
import json
import os
import sys
from datetime import date

from ..adapters.approver import InteractiveApprover, ScriptedApprover
from ..adapters.bank_mock import MockBank
from ..adapters.ledger_csv import CsvLedger
from ..adapters.llm_gemini import GeminiLLM
from ..adapters.llm_mock import MockLLM
from ..adapters.mail_outbox import OutboxMail
from ..adapters.memory_json import JsonMemory
from ..application.agent import CloserAgent
from ..domain.models import PayStep


def rs(n: int) -> str:
    return "Rs {:,}".format(n)


def print_card(card, out) -> None:
    w = out.write
    w("\n=== APPROVAL CARD (nothing irreversible happens before you approve) ===\n")
    w("%s\n" % card.summary)
    for s in card.steps:
        if isinstance(s, PayStep):
            w("  PAY   %-18s %10s  %s  [%s]\n" % (s.payee, rs(s.amount), s.reason, s.digest()[:8]))
        else:
            w("  EMAIL %-18s %s  [%s]\n" % (s.supplier_name, s.kind, s.digest()[:8]))
            w("        subject: %s\n" % s.subject)
    for u in card.uncovered:
        w("  NOT COVERED %s %s (cash short)\n" % (u.invoice_id, rs(u.amount)))
    for h in card.held:
        w("  HOLD  %s: %s\n" % (h.invoice_id, h.reason))


def build_agent(args) -> CloserAgent:
    with open(os.path.join(args.data, "bank.json")) as f:
        cfg = json.load(f)
    inbox = []
    if args.inbox:
        with open(args.inbox) as f:
            inbox = json.load(f)
    faults = {}
    for spec in args.fault or []:
        key, _, seq = spec.rpartition("=")
        faults[key] = seq.split(",")
    llm = GeminiLLM() if args.llm == "gemini" and os.environ.get("GEMINI_API_KEY") else MockLLM()
    if args.approve == "ask":
        approver = InteractiveApprover()
    else:
        approver = ScriptedApprover(args.approve)
    agent = CloserAgent(
        ledger=CsvLedger(args.data),
        mail=OutboxMail(os.path.join(args.state, "outbox.jsonl"), inbox=inbox),
        bank=MockBank(os.path.join(args.state, "bank_state.json"), balance=cfg["balance"], faults=faults),
        memory=JsonMemory(os.path.join(args.state, "memory.json")),
        llm=llm, approver=approver, reserve=cfg["reserve"])
    agent.llm_name = llm.name
    return agent


def main(argv=None, out=sys.stdout) -> int:
    p = argparse.ArgumentParser(prog="closer45")
    p.add_argument("--data", default="demo/data")
    p.add_argument("--state", default="out/state")
    p.add_argument("--today", default="2026-03-10")
    p.add_argument("--approve", default="all", help="ask | all | none | except:<key>,<key> (scripted human)")
    p.add_argument("--llm", default="mock", choices=["mock", "gemini"])
    p.add_argument("--inbox", default=None, help="canned supplier replies (json)")
    p.add_argument("--fault", action="append", help="KEY=error,timeout_after_apply (mock bank fault injection)")
    p.add_argument("--topup", type=int, default=0, help="simulate money received in the mock bank")
    p.add_argument("--label", default="run")
    args = p.parse_args(argv)

    agent = build_agent(args)
    if args.topup:
        agent.bank.state["balance"] += args.topup
        agent.bank._save()
    # show the card before acting: wrap the approver
    inner = agent.approver

    class Showing:
        def decide(self, card):
            print_card(card, out)
            out.write("\n[human step: %s]\n" % ("typed answers" if args.approve == "ask" else "scripted approval '%s'" % args.approve))
            return inner.decide(card)

    agent.approver = Showing()
    out.write("Closer 45  | llm=%s  | today=%s  | data is synthetic, bank and mail are mocks\n" % (agent.llm_name, args.today))
    r = agent.run_cycle(date.fromisoformat(args.today))
    out.write("\n=== TRACE ===\n")
    for line in r.trace:
        out.write("  - %s\n" % line)
    out.write("\n=== RESULT ===\npaid %d | emails sent %d | rejected %d | parked %d | cash %s -> %s\n" % (
        len(r.executed), len(r.sent_emails), len(r.rejected), len(r.parked), rs(r.balance_before), rs(r.balance_after)))
    os.makedirs(args.state, exist_ok=True)
    with open(os.path.join(args.state, "%s.json" % args.label), "w") as f:
        json.dump(r.to_dict(), f, indent=2, sort_keys=True)
    return 0
