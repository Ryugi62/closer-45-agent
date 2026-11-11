import json
import os
import urllib.request
from typing import Callable, Optional, Tuple

from .llm_mock import MockLLM


def _http(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


class GeminiLLM:
    """Optional. Words the supplier emails and the card summary. Money decisions stay in the domain kernel.
    Any error or odd output falls back to the deterministic mock text."""
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 transport: Callable[[str, dict], dict] = _http):
        self.key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.transport = transport
        self.fallback = MockLLM()
        self.fallbacks_used = 0

    def _ask(self, prompt: str) -> str:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
               % (self.model, self.key))
        data = self.transport(url, {"contents": [{"parts": [{"text": prompt}]}]})
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    def draft_email(self, step) -> Tuple[str, str]:
        base = self.fallback.draft_email(step)
        try:
            text = self._ask("Rewrite this supplier email politely and briefly in plain English. "
                             "Keep every invoice number and rupee amount exactly. First line = subject.\n\n"
                             "Subject: %s\n\n%s" % base)
            subject, _, body = text.partition("\n")
            subject = subject.replace("Subject:", "").strip()
            if not subject or not body.strip() or len(body) > 1500:
                raise ValueError("odd output")
            if step.detail and any(tok not in body for tok in step.detail.split("; ")[0].split(" ")[:1]):
                raise ValueError("invoice reference lost")
            return subject, body.strip()
        except Exception:
            self.fallbacks_used += 1
            return base

    def explain(self, summary: dict) -> str:
        return self.fallback.explain(summary)
