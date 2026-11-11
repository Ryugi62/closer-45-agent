# SPEC: Closer 45 (AgentX final, track PS-07 Open)

## Purpose (목적)
An accounts-payable agent for a small Indian business. It reads the supplier ledger, works out which
invoices must be paid before the MSME payment deadline (45 days at most, 15 days when there is no
written agreement), plans what the cash on hand can cover, asks suppliers what it does not know,
and pays only after a human approves the exact payment card.
It is an agent, not a chatbot: it plans its own steps, uses three tools (ledger, mail, bank),
remembers across runs, and stops at every irreversible step.

## Ubiquitous language (code names match)
- Invoice, Supplier, MsmeStatus (micro, small, medium_or_large, unknown)
- legal_days: days allowed from acceptance to payment. due_date = accepted_on + legal_days.
- days_left: due_date minus today (negative = overdue).
- Plan: ordered Steps. PayStep (irreversible), EmailStep (external, goes on the same card).
- ApprovalCard: what the human sees. Digest: sha256 of one step (kind, key, payee, amount).
- Decision: the set of digests the human approved.
- Memory: state file that survives runs (paid keys, asked suppliers, replies).

## Success conditions (numbers · 성공 조건)
1. Planning is deterministic: 20 shuffled orderings of the same ledger produce one identical plan.
2. Never pays above cash minus reserve; never pays a step without an approved digest.
3. Never pays one invoice twice: duplicate ledger rows, repeated runs, and bank timeouts after apply
   all end with exactly 1 transaction per invoice.
4. A changed amount after approval moves 0 rupees (bank rejects the digest mismatch).
5. Transient bank errors are retried at most 2 times, then the step is parked and reported.
6. The demo is reproducible with one command (`demo/run_demo.sh`), and the replay test passes 20/20.

## Given / When / Then
- Given invoice due in 6 days, supplier micro, cash enough, When run, Then plan has a PayStep with reason "due in 6 days".
- Given supplier status unknown, When run, Then plan has an EmailStep asking for Udyam status and no PayStep for it.
- Given the supplier was already asked (memory), When run again, Then no second email.
- Given a reply "small", When run again, Then the invoice is classified and handled like any MSME invoice.
- Given cash covers only part of the at-risk invoices, Then the earliest-due ones are paid and the rest are reported as uncovered with a reschedule email.
- Given the human rejects a step, Then nothing for that step happens and the plan is recorded as rejected.
- Given a bank timeout after the payment was applied, When the agent retries, Then it checks bank status first and does not pay again.

## Non-goals (비목표)
Real bank or mail integration (mock adapters, synthetic data), tax advice, legal interpretation beyond
the simplified rule above, GST, multi-currency, a web UI, model training.

## Rule used (simplified, synthetic)
Micro and small suppliers: payment due within the agreed days, never more than 45; 15 days without a
written agreement. Medium and large suppliers: no statutory deadline in this model. Unknown: ask.
