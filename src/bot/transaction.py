from typing import Iterable, List

from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner
)
from algosdk.v2client.algod import AlgodClient
from algosdk.error import AlgodHTTPError

from .exceptions import TransactionError


class AtomicTransaction:

    def __init__(self, txns: Iterable[TransactionWithSigner], note: str = None):
        self.composer = AtomicTransactionComposer()
        for txn in txns:
            self.composer.add_transaction(txn)

    def __add__(self, other):
        if isinstance(other, AtomicTransaction):
            return AtomicTransaction(self.txns + other.txns)
        raise NotImplementedError

    def add_transaction(self, txn: TransactionWithSigner) -> None:
        self.composer.add_transaction(txn)

    @property
    def txns(self) -> List[TransactionWithSigner]:
        return self.composer.txn_list

    def send(self, algod: AlgodClient, wait: int = None) -> list:
        try:
            if wait:
                return self.composer.execute(algod, wait)
            return self.composer.submit(algod)
        except AlgodHTTPError:
            raise TransactionError

    @property
    def fee(self):
        return sum(txn.fee for txn in self.txns)

    @property
    def groupid(self) -> int:
        return self.txns[0].txn.group
