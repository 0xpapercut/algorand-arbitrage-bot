from typing import List
from itertools import combinations, product
from concurrent.futures import ThreadPoolExecutor, wait
import pickle
import logging

from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from .asset import Asset, ALGO
from .pool import BasePool
from .dex.pactfi import PactfiPool
from .dex.tinyman import TinymanPool
from .arbitrage import ArbitrageGraph
from .exceptions import PoolFetchError
from .account import Account

DEFAULT_CUTOFF = 4
DEFAULT_PICKLE_FILE = 'pools.pickle'
DEFAULT_MAX_WORKERS = 5
DEFAULT_MAX_AMOUNT_IN = 1_000_000


class BotClient:

    def __init__(self, algod: AlgodClient, indexer: IndexerClient, account: Account):
        self.algod = algod
        self.indexer = indexer
        self.account = account
        self.pools = List[BasePool]
        self.arbgraph = None

    def fetch_pools(self, assets: List[Asset], dump_state: bool = True):
        logging.info('Fetching pools...')
        self.pools = []
        classes = [TinymanPool, PactfiPool]
        for cls, _assets in product(classes, combinations(assets, 2)):
            if pool := self._fetch_pool(cls, _assets):
                self.pools.append(pool)
        logging.info('Finished fetching pools.')

        if dump_state:
            self.dump_state()

    def run(self,
            main_asset: Asset = ALGO,
            cutoff: int = DEFAULT_CUTOFF,
            max_amount_in: int = DEFAULT_MAX_AMOUNT_IN):
        logging.info('Starting bot...')
        logging.info('Constructing arbitrage graph...')
        self.arbgraph = ArbitrageGraph(self.pools)
        logging.info('Finished constructing arbitrage graph.')

        while True:
            self.refresh_state()

            logging.info('Finding possible opportunities...')
            opportunities = self.arbgraph.find_opportunities(main_asset, cutoff)
            opportunities = [path for path in opportunities if path.ratio > 0]
            # opportunities = [path for path in opportunities if path.maximum_profit(max_amount_in) > 0]
            # opportunities.sort(key=lambda path: -path.maximum_profit(max_amount_in))
            opportunities.sort(key=lambda path: -path.ratio)
            logging.info('Opportunities found.')

            for path in opportunities[:10]:
                optimal_amount_in = int(path.optimal_amount_in_precise(max_amount_in))
                txn = path.prepare_txn(self.account, optimal_amount_in, self.suggested_params)
                if txn.profit_after_fee(self.suggested_params) > 0:
                    txn.send(self.algod)
                    logging.info('Sent transaction.')

    def refresh_state(self):
        logging.info('Starting refreshing step...')
        self._refresh_pools()
        self._refresh_account()

        logging.info('Getting suggested params...')
        self.suggested_params = self.algod.suggested_params()
        logging.info('Finished refreshing step.')

    def _refresh_pools(self):
        logging.info('Refreshing pools...')
        with ThreadPoolExecutor(DEFAULT_MAX_WORKERS) as executor:
            futures = [executor.submit(pool.refresh_state) for pool in self.pools]
            wait(futures)
        logging.info('Finished refreshing pools.')

    def _refresh_account(self):
        logging.info('Refreshing account state...')
        self.account.refresh_state()
        logging.info('Finished refreshing pools.')

    def _fetch_pool(self, cls, assets: List[Asset]) -> BasePool:
        try:
            pool = cls(self.algod, self.indexer, assets)
            if pool.supply(assets[0]) == 0 or pool.supply(assets[1]) == 0:
                raise PoolFetchError
            print(f"Initialized {pool}.")
            return pool
        except PoolFetchError:
            print(f"Couldn't initiliaze {cls.__name__} with assets {'/'.join(str(asset) for asset in assets)}.")

    def dump_state(self, filename: str = DEFAULT_PICKLE_FILE):
        logging.info(f'Dumping pools to `{filename}`.')
        with open(filename, 'wb') as fp:
            pickle.dump(self.pools, fp)

    def load_state(self, filename: str = DEFAULT_PICKLE_FILE):
        logging.info(f'Loading pools from `{filename}`.')
        with open(filename, 'rb') as fp:
            self.pools = pickle.load(fp)
