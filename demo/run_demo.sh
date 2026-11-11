#!/usr/bin/env bash
# One-line reproduction: ./demo/run_demo.sh   (Python 3.8+, no API key, no network)
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src PYTHONHASHSEED=0
rm -rf out/state out/state_fail out/state_no
banner() { printf '\n\n########## %s ##########\n' "$1"; }

banner "DAY 1  (10 Mar): read ledger, plan, ask the human, pay, email"
python3 -m closer45 --state out/state --today 2026-03-10 --approve all --label day1

banner "DAY 2  (11 Mar): supplier S4 replied 'small', Rs 100,000 received. The agent remembers day 1"
python3 -m closer45 --state out/state --today 2026-03-11 --approve all --inbox demo/data/inbox_day2.json --topup 100000 --label day2

banner "DAY 3  (12 Mar): run again. Nothing is paid twice, nobody is asked twice"
python3 -m closer45 --state out/state --today 2026-03-12 --approve all --label day3

banner "TOOL FAILURE: bank returns errors; a timeout happens after the money already moved"
python3 -m closer45 --state out/state_fail --today 2026-03-10 --approve all --label fail \
  --fault "pay:S2:BP-0442=error,error" --fault "pay:S1:AF/2026/118=timeout_after_apply"

banner "HUMAN SAYS NO: reject everything, nothing moves"
python3 -m closer45 --state out/state_no --today 2026-03-10 --approve none --label no

banner "TESTS"
python3 -m pytest -q -p no:cacheprovider 2>&1 | tail -3
python3 -m pytest -p no:cacheprovider tests/test_replay.py tests/test_planner.py -k "replay or shuffles" -v 2>&1 | grep -E "PASSED|passed"
