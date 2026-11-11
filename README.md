# Closer 45

**An accounts-payable agent for a small business. It decides which supplier invoices must be paid before the Indian MSME payment deadline, plans what the cash can cover, asks suppliers what it does not know, and pays only after a human approves the exact card.**

AgentX final, track PS-07 Open (team Lumia Agents). Built in the 24-hour window, 11-12 Nov 2026, with an AI coding assistant (allowed by the rules).

> **Synthetic data, mocked tools.** The ledger is a made-up CSV. The bank and mail tools are local mocks (a JSON file and an outbox file). Nothing here moves real money or sends real mail. The default LLM is a deterministic mock so the repo runs with no API key; set `GEMINI_API_KEY` and pass `--llm gemini` to let Gemini word the supplier emails (untested against the live API in this build, it falls back to the mock text on any error).

## Why an agent and not a chatbot
A chatbot answers "which invoice is urgent?". Closer 45 does the job: it plans its own steps, calls three tools, remembers what it did yesterday, and stops at every irreversible step.

| Agent requirement | Where it is in the code |
|---|---|
| Plans its own steps | `domain/planner.py` builds the ordered plan (urgency, cash budget, duplicates, unknown suppliers) |
| At least two tools | ledger read, mail send, bank pay, bank status (`adapters/`, ports in `application/ports.py`) |
| Remembers | `adapters/memory_json.py`: paid keys, sent mails, supplier replies survive runs |
| Human before anything irreversible | approval card with a digest per step (`application/agent.py`); the bank recomputes it (`adapters/bank_mock.py`) |
| Tool failure | retry at most 2 times, check the bank status before every retry, park the step if it still fails |

## The problem, in one case
A small manufacturer owes micro and small suppliers. Under the (simplified) rule modelled here, a micro or small supplier must be paid within the agreed days, never more than 45, and within 15 days if there is no written agreement. Late payment costs interest and tax deductions, and cash is never enough to pay everyone at once. Someone has to decide, every week, whom to pay first, whom to ask, and whom to tell "next run".

Measured on the demo ledger (7 rows, Rs 450,000 cash, Rs 50,000 reserve): paying in ledger order leaves 1 invoice past its deadline by 16 Mar; the Closer plan leaves 0 (`tests/test_baseline.py`). That is a synthetic ledger, not a customer result. Customer signal so far: none, the next step is to run the plan on one real small business ledger.

## Run it (3 lines, Python 3.8+, no network, no key)
```bash
git clone https://github.com/Ryugi62/closer-45-agent && cd closer-45-agent
./demo/run_demo.sh          # three days, a tool failure, a human "no", then the tests
python3 -m pytest -q        # 33 tests
```
One cycle by hand: `PYTHONPATH=src python3 -m closer45 --approve ask` (you type y/n for each step).

## What the demo shows
1. **Day 1**: reads 7 ledger rows, plans 3 payments (one overdue by 19 days), 2 emails (ask an unknown supplier its Udyam status, tell a supplier its invoice waits), holds a duplicate row and a large supplier, prints the approval card, acts only on approved steps.
2. **Day 2**: the supplier replied "small" and money arrived. The agent remembers day 1, does not ask again, does not repay, and pays the newly classified invoice.
3. **Day 3**: nothing to do, so it does nothing.
4. **Tool failure**: the bank returns 503 twice (retried), and times out after already applying a payment (the agent checks status and does not pay twice).
5. **Human says no**: 0 rupees move, 0 emails go out.

## Reliability numbers
- 33 tests pass (domain rules, planner, agent, failure paths, architecture, CLI, Gemini fallback).
- Replay: the same cycle run 20 times in fresh folders gives 1 identical result hash (20/20).
- The plan is identical across 20 shuffles of the ledger row order.
- The plan never spends above cash minus reserve (7 cash levels from 0 to Rs 2,000,000).
- Duplicates: duplicate ledger rows, repeated runs and a timeout-after-apply all end with exactly 1 bank transaction per invoice.
- A changed amount after approval moves 0 rupees (the bank refuses the digest mismatch).
- `tests/test_architecture.py` fails the build if an inner layer imports an outer one.

## What is new here
The agent does not let the model decide money. The LLM only words emails; the amounts, order and limits come from a small deterministic kernel, and every irreversible step is bound to a digest the human approved. Existing AP tools report overdue bills; this one plans, asks, remembers and holds at the gate.

Similar tools we looked at (idea round, 30 Oct 2026, public pages): Tally Prime MSME report, Zoho Books unpaid MSME bills filter, MSMEGuard (ICAI use-case list), TReDS invoice financing, an n8n sheet-and-Slack tracker template. What we found them doing is reporting or tracking. We did not find planning against a cash limit, supplier questions, or a per-step approval digest in them; that is a search-scope claim, not a survey of paid or private products.

## Technology choices
- Python standard library only at runtime (tests use pytest). Fewer moving parts to review.
- Ports and adapters, so the bank, mail and LLM can be swapped without touching the rules.
- Deterministic kernel plus optional LLM: replayable and testable; a model that miscounts cannot overspend.
- Mock bank with idempotency keys, like real payment APIs, so the retry logic is exercised without real money.

## Pre-existing versus built in the 24 hours
| Item | Status |
|---|---|
| The idea (45-day AP agent, human gate) | Pre-existing: our 6-slide idea deck submitted 30 Oct 2026 |
| `closer-airwallex` (our other public repo) | Pre-existing, different project. No code was copied or imported here |
| Everything in `src/`, `tests/`, `demo/`, `docs/`, this README | Written during the 24-hour window |

## Limits
Synthetic data and mock tools. The deadline rule is simplified and is not tax or legal advice (check the statute and your accountant). One currency. No UI. No live LLM test. Single-user, single-process state files.

Layout: `SPEC.md` (goals, language, Given/When/Then), `src/closer45/{domain,application,adapters,infrastructure}`, `tests/`, `demo/`, `docs/architecture.png`, `docs/qa.md`.
