import io
import json

from closer45.adapters.llm_gemini import GeminiLLM
from closer45.domain.models import EmailStep
from closer45.infrastructure.cli import main

STEP = EmailStep("mail:reschedule:S5:L-3", "S5", "Eastern Plastics", "reschedule", "r", detail="EP/77 (Rs 90000, due in 17 days)")


def test_gemini_uses_model_text_when_valid():
    fake = lambda url, payload: {"candidates": [{"content": {"parts": [{"text": "Subject: Payment timing\nHello, EP/77 will be paid next run."}]}}]}
    subject, body = GeminiLLM("k", transport=fake).draft_email(STEP)
    assert subject == "Payment timing" and "EP/77" in body


def test_gemini_falls_back_on_error_and_on_lost_invoice_number():
    def boom(url, payload):
        raise OSError("no network")
    g = GeminiLLM("k", transport=boom)
    assert "EP/77" in g.draft_email(STEP)[1] and g.fallbacks_used == 1
    odd = lambda url, payload: {"candidates": [{"content": {"parts": [{"text": "Subject: Hi\nPay soon."}]}}]}
    g2 = GeminiLLM("k", transport=odd)
    assert "EP/77" in g2.draft_email(STEP)[1] and g2.fallbacks_used == 1


def test_cli_end_to_end(tmp_path):
    out = io.StringIO()
    rc = main(["--data", "demo/data", "--state", str(tmp_path), "--approve", "all"], out=out)
    assert rc == 0
    text = out.getvalue()
    assert "APPROVAL CARD" in text and "paid 3 | emails sent 2" in text
    assert json.load(open(str(tmp_path / "run.json")))["balance_after"] == 75000
