import csv
import os
from datetime import date

from ..domain.models import Invoice, Supplier


class CsvLedger:
    def __init__(self, directory: str):
        self.dir = directory

    def load(self):
        with open(os.path.join(self.dir, "suppliers.csv"), newline="") as f:
            suppliers = [Supplier(r["id"], r["name"], r["msme_status"]) for r in csv.DictReader(f)]
        with open(os.path.join(self.dir, "invoices.csv"), newline="") as f:
            invoices = [Invoice(r["id"], r["supplier_id"], r["invoice_no"], int(r["amount"]),
                                date.fromisoformat(r["accepted_on"]),
                                int(r["agreed_days"]) if r["agreed_days"].strip() else None)
                        for r in csv.DictReader(f)]
        return invoices, suppliers
