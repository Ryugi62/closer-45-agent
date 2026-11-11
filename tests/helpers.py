import json
import os
import shutil
from datetime import date

from closer45.adapters.approver import ScriptedApprover
from closer45.adapters.bank_mock import MockBank
from closer45.adapters.ledger_csv import CsvLedger
from closer45.adapters.llm_mock import MockLLM
from closer45.adapters.mail_outbox import OutboxMail
from closer45.adapters.memory_json import JsonMemory
from closer45.application.agent import CloserAgent

DATA = os.path.join(os.path.dirname(__file__), "..", "demo", "data")
TODAY = date(2026, 3, 10)


def make_agent(tmp, approve="all", faults=None, inbox=None, data=DATA):
    with open(os.path.join(data, "bank.json")) as f:
        bank_cfg = json.load(f)
    return CloserAgent(
        ledger=CsvLedger(data),
        mail=OutboxMail(os.path.join(str(tmp), "mail.jsonl"), inbox=inbox or []),
        bank=MockBank(os.path.join(str(tmp), "bank_state.json"),
                      balance=bank_cfg["balance"], faults=faults or {}),
        memory=JsonMemory(os.path.join(str(tmp), "memory.json")),
        llm=MockLLM(),
        approver=ScriptedApprover(approve),
        reserve=bank_cfg["reserve"],
    )
