from enum import Enum
from dataclasses import dataclass

from algosdk.v2client.algod import AlgodClient


@dataclass
class Asset:
    index: int
    decimals: int
    name: str
    unit: str

    @property
    def ratio(self):
        return 10**self.decimals

    @classmethod
    def from_index(cls, algod: AlgodClient, index: int) -> 'Asset':
        if index != 0:
            params = algod.asset_info(index)['params']
            return cls(
                index=index,
                decimals=params['decimals'],
                name=params['name'],
                unit=params['unit-name']
            )
        else:
            return ALGO

    def __str__(self):
        return self.name

    def __eq__(self, other: 'Asset'):
        if not isinstance(other, Asset):
            return False
        return self.index == other.index

    def __gt__(self, other: 'Asset'):
        if not isinstance(other, Asset):
            raise NotImplementedError
        return self.index > other.index

    def __hash__(self):
        return hash(self.index)


ALGO = Asset(index=0, decimals=6, name='ALGO', unit='ALGO')


class AssetID(Enum):
    USDC = 31566704
    GALGO = 793124631
    CHIP = 388592191
    USDT = 312769
    OPUL = 287867876
    DEFLY = 470842789
    COOP = 796425061
    MUSDC = 1073876536
    GOBTC = 386192725
    GOETH = 386195940
    GOUSD = 672913181
    FUSDT = 971385312
    FUSDC = 971384592


def fetch_assets(algod, asset_names: [str] = None, all=False, as_dict=False):
    global ALGO

    if asset_names is None and not all:
        raise ValueError(f'Must either define `asset_names` or set `all` to True.')
    if asset_names is not None and all:
        raise ValueError(f'Must define either `asset_names` or set `all` to True, but not both.')

    assets = {}
    if not all:
        for name in asset_names:
            if name == ALGO.name:
                assets['ALGO'] = ALGO
            else:
                assets[name] = Asset.from_index(algod, AssetID[name].value)
    else:
        for index in AssetID:
            assets[index.name] = Asset.from_index(algod, index.value)
        assets['ALGO'] = ALGO

    if as_dict:
        return assets
    return list(assets.values())
