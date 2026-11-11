class BankError(Exception):
    pass


class TransientBankError(BankError):
    pass


class ApprovalMismatch(BankError):
    pass
