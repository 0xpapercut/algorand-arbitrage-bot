from typing import Union

from algosdk.v2client.algod import AlgodClient
from algosdk.transaction import AssetOptInTxn
from algosdk.mnemonic import to_private_key
from algosdk.account import address_from_private_key
from algosdk.atomic_transaction_composer import AccountTransactionSigner

from .asset import Asset, ALGO
from .exceptions import NotOptedIntoAssetError


class Account:

    def __init__(self, algod_client: AlgodClient, mnemonic: str):
        private_key = to_private_key(mnemonic)
        public_address = address_from_private_key(private_key)

        self.algod_client = algod_client
        self.address = public_address
        self.private_key = private_key

    def get_balance(self, asset: Union[int, Asset], refresh: bool = False) -> int:
        if isinstance(asset, int):
            asset = Asset.from_index(self.algod_client, asset)
        elif not isinstance(asset, Asset):
            raise TypeError

        if refresh or not hasattr(self, 'balance'):
            self.refresh_state()

        try:
            return self._balance[asset]
        except KeyError:
            raise NotOptedIntoAssetError(f'Account must be opted into asset {asset}.')

    def is_opted_in_asset(self, asset: Union[int, Asset]) -> bool:
        if asset == ALGO:
            return True

        try:
            return self.get_balance(asset) is not None
        except NotOptedIntoAssetError:
            return False

    def _opt_in_asset_txn(self, asset: Union[int, Asset]) -> AssetOptInTxn:
        if isinstance(asset, int):
            index = asset
        elif isinstance(asset, Asset):
            index = asset.index
        else:
            return TypeError

        suggested_params = self.algod_client.suggested_params()
        opt_in_txn = AssetOptInTxn(
            sender=self.address,
            index=index,
            sp=suggested_params
        )

        return opt_in_txn.sign(self.private_key)

    def opt_in_asset(self, asset: Union[int, Asset]) -> None:
        if not self.is_opted_in_asset(asset):
            self.algod_client.send_transaction(self._opt_in_asset_txn(asset))

    @property
    def signer(self) -> AccountTransactionSigner:
        return AccountTransactionSigner(self.private_key)

    def refresh_state(self) -> None:
        self._balance = {}

        info = self.algod_client.account_info(self.address)
        for asset_info in info['assets']:
            asset = Asset.from_index(self.algod_client, asset_info['asset-id'])
            amount = asset_info['amount']
            self._balance[asset] = amount
        self._balance[ALGO] = info['amount']
