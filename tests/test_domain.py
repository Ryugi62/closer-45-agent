from datetime import date

from closer45.domain.models import Invoice, Supplier
from closer45.domain.rules import days_left, due_date, legal_days


def inv(agreed, accepted=date(2026, 1, 30)):
    return Invoice("L", "S", "N-1", 100, accepted, agreed)


def sup(status):
    return Supplier("S", "x", status)


def test_agreed_days_capped_at_45():
    assert legal_days(inv(90), sup("micro")) == 45
    assert legal_days(inv(30), sup("small")) == 30


def test_no_written_agreement_is_15_days():
    assert legal_days(inv(None), sup("micro")) == 15


def test_medium_large_has_no_deadline():
    assert legal_days(inv(45), sup("medium_or_large")) is None


def test_unknown_status_has_no_computable_deadline():
    assert legal_days(inv(45), sup("unknown")) is None


def test_due_date_and_days_left():
    i, s = inv(45), sup("micro")
    assert due_date(i, s) == date(2026, 3, 16)
    assert days_left(i, s, date(2026, 3, 10)) == 6
    assert days_left(i, s, date(2026, 3, 20)) == -4
