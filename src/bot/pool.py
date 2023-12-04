from typing import Iterable
from abc import ABC, abstractmethod
from itertools import chain

from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk.atomic_transaction_composer import TransactionWithSigner

from .asset import Asset, ALGO
from .account import Account
from .transaction import AtomicTransaction
from .exceptions import TransactionError, PoolTransactionError


class BasePool(ABC):

    def __init__(self, algod: AlgodClient, indexer: IndexerClient,
                 assets: tuple[Asset, Asset]):
        self.algod = algod
        self.indexer = indexer
        self.assets = assets

    def get_other_asset(self, asset: Asset) -> Asset:
        assert asset in self.assets
        return self.assets[0] if asset != self.assets[0] else self.assets[1]

    def ratio(self, asset_in: Asset) -> float:
        """Quotes relative amount received for an infinitesimal swap."""
        return self.supply(self.get_other_asset(asset_in)) / self.supply(asset_in)

    def prepare_swap_txn(self, sender: Account, asset_in: Asset, amount_in: int, amount_out: int, suggested_params: dict):
        """Creates a transaction for the swap operation."""
        txns = self.prepare_internal_swap_txns(sender.address, asset_in, amount_in, amount_out, suggested_params)
        for i, txn in enumerate(txns):
            if txn.sender == sender.address:
                txns[i] = TransactionWithSigner(txn, sender.signer)
        return PoolAtomicTransaction(txns, self, sender, asset_in, amount_in, amount_out)

    @property
    @abstractmethod
    def address(self) -> str:
        """The address of the pool."""
        pass

    @abstractmethod
    def supply(self, asset: Asset) -> int:
        """Returns the supply of `asset` in the pool."""
        pass

    @abstractmethod
    def amount_out(self, asset_in: Asset, amount_in: int) -> int:
        """Calculates the exact amount of received tokens on the operation."""
        pass

    @abstractmethod
    def prepare_internal_swap_txns(self, sender: str, asset_in: Asset, amount_in: int, amount_out: int, suggested_params):
        """Returns a list of the internal swap transactions."""
        pass

    @abstractmethod
    def refresh_state(self):
        """Refreshs the state of the pool."""
        pass

    @abstractmethod
    def fee(self, suggested_params: dict):
        """Swap transaction fee value in ALGO."""
        pass

    def __str__(self):
        assets = sorted(self.assets)
        return f'{assets[0]} {self.supply(assets[0])}/{assets[1]} {self.supply(assets[1])} {self.__class__.__name__}'

    def __repr__(self):
        return str(self)


class XYKPoolMixin:

    def amount_out_approx(self: BasePool, asset_in: Asset, amount_in: float) -> float:
        if amount_in < 0:
            raise ValueError
        asset_out = self.get_other_asset(asset_in)
        gamma = 1 - self.fee
        amount_out = amount_in * gamma * self.supply(asset_out) / (gamma * amount_in + self.supply(asset_in))
        return amount_out


class Pool(XYKPoolMixin, BasePool):

    @property
    def address(self) -> str:
        try:
            return self._address
        except AttributeError:
            raise AttributeError(f'{self.__class__.__name__} object has no `_address` attribute.')

    def supply(self, asset: Asset) -> int:
        try:
            return self._supply[asset]
        except AttributeError:
            raise AttributeError(f'{self.__class__.__name__} object has no `_supply` attribute.')

    def fee(self, suggested_params: dict):
        txns = self.prepare_internal_swap_txns("", self.assets[0], 10_000, 1, suggested_params)
        return sum(txn.fee for txn in txns)


class PoolAtomicTransaction(AtomicTransaction):

    def __init__(
        self,
        txns: Iterable[TransactionWithSigner],
        pool: BasePool,
        account: Account,
        asset_in: Asset,
        amount_in: int,
        amount_out: int,
        note: str = None
    ):
        super().__init__(txns, note=note)
        self.pool = pool
        self.account = account
        self.asset_in = asset_in
        self.asset_out = pool.get_other_asset(asset_in)
        self.amount_in = amount_in
        self.amount_out = amount_out

    def send(self, algod: AlgodClient, wait: int = None) -> list:
        try:
            return super().send(algod, wait=wait)
        except TransactionError:
            raise PoolTransactionError(f'Swap transaction of {self.amount_in} {self.asset_in} to {self.amount_out} {self.asset_out} on pool {self.pool.address} failed.')


class ArbitrageAtomicTransaction(AtomicTransaction):

    def __init__(self, swap_txns: Iterable[PoolAtomicTransaction]):
        self.swap_txns = swap_txns
        txns = chain(*[swap_txn.txns for swap_txn in swap_txns])
        super().__init__(txns)

    @property
    def amount_in(self) -> int:
        return self.swap_txns[0].amount_in

    @property
    def amount_out(self) -> int:
        return self.swap_txns[-1].amount_out

    @property
    def asset(self) -> Asset:
        return self.swap_txns[0].asset_in

    @property
    def profit(self) -> int:
        return self.amount_out - self.amount_in

    def profit_after_fee(self, suggested_params: dict) -> int:
        assert self.asset == ALGO
        return self.profit - self.fee(suggested_params)

    def fee(self, suggested_params: dict) -> int:
        return sum(swap_txn.pool.fee(suggested_params) for swap_txn in self.swap_txns)
