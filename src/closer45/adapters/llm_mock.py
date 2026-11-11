from typing import Tuple


class MockLLM:
    """Deterministic stand-in so the demo and tests need no API key."""
    name = "mock"

    def draft_email(self, step) -> Tuple[str, str]:
        if step.kind == "ask_status":
            return ("Quick check on your Udyam registration",
                    "Dear %s team,\n\nTo schedule your payment correctly we need to know whether you are a "
                    "registered micro or small enterprise (Udyam). Could you reply with your status "
                    "(micro, small or neither)?\n\nThank you,\nAccounts Payable" % step.supplier_name)
        return ("Payment date for your open invoices",
                "Dear %s team,\n\nWe could not cover these invoices in this payment run: %s. "
                "We will pay them in the next run. Please reply if this timing is a problem.\n\n"
                "Thank you,\nAccounts Payable" % (step.supplier_name, step.detail))

    def explain(self, summary: dict) -> str:
        total = sum(a for _, a, _ in summary["pay"])
        return ("Pay %d invoice(s) totalling Rs %d (cash Rs %d, reserve Rs %d), send %d email(s), %d invoice(s) not covered."
                % (len(summary["pay"]), total, summary["cash"], summary["reserve"],
                   len(summary["emails"]), len(summary["uncovered"])))
