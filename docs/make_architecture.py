"""Draws docs/architecture.png. Run: python3 docs/make_architecture.py"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
BG, INK, MUTE = (250, 250, 247), (24, 28, 36), (96, 104, 118)
BLUE, GREEN, AMBER, RED = (38, 99, 235), (22, 128, 90), (196, 120, 8), (200, 48, 48)


def font(size, bold=False):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size, index=1 if bold and p.endswith(".ttc") else 0)
        except Exception:
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def box(x, y, w, h, title, lines, color, fill=(255, 255, 255)):
    d.rounded_rectangle([x, y, x + w, y + h], 18, fill=fill, outline=color, width=4)
    d.text((x + 22, y + 16), title, font=font(30, True), fill=color)
    for i, ln in enumerate(lines):
        d.text((x + 22, y + 64 + i * 34), ln, font=font(25), fill=INK)


def arrow(x1, y1, x2, y2, color=MUTE):
    d.line([x1, y1, x2, y2], fill=color, width=4)
    d.polygon([(x2, y2), (x2 - 14, y2 - 8) if x2 > x1 else (x2 + 14, y2 - 8),
               (x2 - 14, y2 + 8) if x2 > x1 else (x2 + 14, y2 + 8)], fill=color) if y1 == y2 else \
        d.polygon([(x2, y2), (x2 - 8, y2 - 14), (x2 + 8, y2 - 14)], fill=color)


d.text((60, 36), "Closer 45: observe, plan, ask a human, act, remember", font=font(40, True), fill=INK)
d.text((60, 90), "Dependencies point inward only (tests/test_architecture.py enforces it)", font=font(24), fill=MUTE)

box(60, 160, 440, 250, "domain/  (pure)", ["rules: 45-day / 15-day deadline", "planner: urgency order, cash budget,",
    "duplicates, asks when unknown", "steps + digest of each step"], GREEN)
box(580, 160, 440, 250, "application/", ["agent loop: observe -> plan ->", "draft -> approval card -> act ->", "retry/park -> memory",
    "ports: Ledger Mail Bank Mem LLM"], BLUE)
box(1100, 160, 440, 250, "infrastructure/", ["CLI, config, demo scripts", "wires adapters to ports", "prints the approval card"], MUTE)
arrow(580, 285, 500, 285, GREEN)
arrow(1100, 285, 1020, 285, MUTE)

d.text((60, 440), "adapters/  (the three tools the agent uses, all mocked and synthetic)", font=font(30, True), fill=INK)
box(60, 490, 340, 170, "Ledger tool", ["CSV: suppliers, invoices", "read-only"], BLUE)
box(430, 490, 340, 170, "Mail tool", ["outbox file (mock)", "ask status / reschedule"], AMBER)
box(800, 490, 340, 170, "Bank tool", ["mock NEFT, idempotent", "needs approved digest"], RED)
box(1170, 490, 370, 170, "Memory + LLM", ["JSON state across runs", "mock text or Gemini wording"], GREEN)

d.rounded_rectangle([60, 700, 1540, 860], 18, fill=(255, 244, 244), outline=RED, width=4)
d.text((82, 714), "Human gate before anything irreversible", font=font(30, True), fill=RED)
d.text((82, 760), "Each payment and email gets a digest (sha256 of key, payee, amount, text). The human approves digests.", font=font(25), fill=INK)
d.text((82, 796), "The bank recomputes the digest: change the amount after approval and 0 rupees move.", font=font(25), fill=INK)
for x in (230, 600, 970):
    d.line([x, 660, x, 700], fill=RED, width=4)
img.save("docs/architecture.png")
