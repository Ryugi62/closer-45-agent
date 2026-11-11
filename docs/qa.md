# Questions we expect, with straight answers
1. **Why this structure?** Domain rules and planner have no I/O, so they are testable and replayable. The agent loop talks to ports; adapters are mocks here and could be real banks later.
2. **What if a tool fails?** Bank errors are retried at most 2 times; before each retry the agent asks the bank whether the payment already applied. After that the step is parked and reported. Tests: `tests/test_agent.py`.
3. **How is the irreversible step confirmed?** The card lists each payment and email with a sha256 digest of its key, payee, amount (or email text). The human approves digests. The bank recomputes the digest, so a changed amount moves nothing.
4. **What about LLM hallucination?** The LLM never picks amounts, order or payees. It words emails; the digest covers the text; Gemini output that loses an invoice number falls back to the template.
5. **What was already there?** The idea and an unrelated repo. All code in this repo was written in the window. See README.
6. **What breaks at scale?** Greedy deadline-first packing is deterministic but not optimal knapsack; state is a JSON file. Both are swappable behind ports.
7. **What do the tests cover?** 33 tests: rules, planner properties, agent flows, failure injection, architecture boundaries, CLI, replay.
