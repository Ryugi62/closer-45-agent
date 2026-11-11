import hashlib
import json

from helpers import TODAY, make_agent


def run_hash(tmp):
    r = make_agent(tmp).run_cycle(TODAY)
    return hashlib.sha256(json.dumps(r.to_dict(), sort_keys=True).encode()).hexdigest()


def test_replay_20_runs_identical(tmp_path):
    hashes = set()
    for i in range(20):
        d = tmp_path / ("r%d" % i)
        d.mkdir()
        hashes.add(run_hash(d))
    assert len(hashes) == 1
