from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from pactsdk.client import PactClient

from ..asset import Asset
from ..pool import Pool
from ..exceptions import PoolFetchError


class PactfiPool(Pool):

    def __init__(self, algod: AlgodClient, indexer: IndexerClient, assets: tuple[Asset, Asset]):
        super().__init__(algod, indexer, assets)

        client = PactClient(algod)
        self._assets = {asset: client.fetch_asset(asset.index) for asset in assets}
        try:
            self._pool = client.fetch_pools_by_assets(*self._assets.values())[0]
        except IndexError:
            raise PoolFetchError
        self._address = self._pool.get_escrow_address()

        self.refresh_state()

    def refresh_state(self):
        self._pool.update_state()

        if self.assets[0].index == self._pool.primary_asset.index:
            primary_asset = self.assets[0]
        else:
            primary_asset = self.assets[1]
        secondary_asset = self.get_other_asset(primary_asset)
        self._supply = {
            primary_asset: self._pool.state.total_primary,
            secondary_asset: self._pool.state.total_secondary
        }

    def amount_out(self, asset_in: Asset, amount_in: int) -> int:
        if asset_in.index == self._pool.primary_asset.index:
            _asset_in = self._pool.primary_asset
        else:
            _asset_in = self._pool.secondary_asset
        swap = self._pool.prepare_swap(_asset_in, amount_in, 0)
        amount_out = swap.effect.amount_received

        return amount_out

    def prepare_internal_swap_txns(self, sender: str, asset_in: Asset, amount_in: int, amount_out: int, suggested_params: dict):
        _asset_in = self._assets[asset_in]

        swap = self._pool.prepare_swap(_asset_in, amount_in, 0)
        txns = self._pool.build_swap_txs(swap, sender, suggested_params)
        for txn in txns:
            txn.group = 0
        return txns
