from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from tinyman.v2.client import TinymanV2MainnetClient
from tinyman.exceptions import LowSwapAmountError

from ..asset import Asset
from ..pool import Pool
from ..exceptions import PoolFetchError


class TinymanPool(Pool):

    def __init__(self, algod: AlgodClient, indexer: IndexerClient, assets: tuple[Asset, Asset]):
        super().__init__(algod, indexer, assets)

        client = TinymanV2MainnetClient(algod)
        self._assets = {asset: client.fetch_asset(asset.index) for asset in assets}
        self._pool = client.fetch_pool(*self._assets.values())
        self._address = self._pool.address

        self.refresh_state()

    def refresh_state(self):
        self._pool.refresh()

        if not self._pool.asset_1_reserves or not self._pool.asset_2_reserves:
            raise PoolFetchError
        reserves = (self._pool.asset_1_reserves, self._pool.asset_2_reserves)
        self._supply = {asset: supply for asset, supply in zip(sorted(self.assets, reverse=True), reserves)}

    def amount_out(self, asset_in: Asset, amount_in: int) -> int:
        _asset_in = self._assets[asset_in]
        try:
            quote = self._pool.fetch_fixed_input_swap_quote(_asset_in(amount_in), slippage=0, refresh=False)
        except LowSwapAmountError:
            return 0
        amount_out = quote.amount_out.amount

        return amount_out

    def prepare_internal_swap_txns(self, sender: str, asset_in: Asset, amount_in: int, amount_out: int, suggested_params: dict):
        _asset_in = self._assets[asset_in]
        _asset_out = self._assets[self.get_other_asset(asset_in)]

        txns = self._pool.prepare_swap_transactions(_asset_in(amount_in), _asset_out(amount_out), 'fixed-input', sender, suggested_params).transactions
        for txn in txns:
            txn.group = 0
        return txns
