import os
import re

SRC = os.path.join(os.path.dirname(__file__), "..", "src", "closer45")
ALLOWED = {
    "domain": set(),
    "application": {"domain"},
    "adapters": {"domain", "application"},
    "infrastructure": {"domain", "application", "adapters"},
}


def imports(path):
    out = set()
    for line in open(path):
        m = re.match(r"\s*from\s+(\.+)(\w*)", line) or None
        if m and len(m.group(1)) >= 2 and m.group(2):
            out.add(m.group(2))
    return out


def test_dependencies_point_inward_only():
    for layer, allowed in ALLOWED.items():
        for root, _, files in os.walk(os.path.join(SRC, layer)):
            for f in files:
                if f.endswith(".py"):
                    bad = {i for i in imports(os.path.join(root, f))
                           if i in ALLOWED and i != layer and i not in allowed}
                    assert not bad, "%s/%s imports %s" % (layer, f, bad)


def test_domain_has_no_io_imports():
    for f in os.listdir(os.path.join(SRC, "domain")):
        if f.endswith(".py"):
            text = open(os.path.join(SRC, "domain", f)).read()
            for banned in ("import os", "import sys", "open(", "urllib", "requests", "import socket"):
                assert banned not in text, (f, banned)
