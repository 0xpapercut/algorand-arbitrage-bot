from utils import get_algod_and_indexer, get_account

from bot.client import BotClient
from bot.asset import fetch_assets

import logging


def main():
    logging.basicConfig(level=logging.INFO)

    algod, indexer = get_algod_and_indexer()
    account = get_account(algod)
    assets = fetch_assets(algod, all=True)
    for asset in assets:
        account.opt_in_asset(asset)

    bot = BotClient(algod, indexer, account)
    bot.fetch_pools(assets)
    bot.run()


if __name__ == '__main__':
    main()
