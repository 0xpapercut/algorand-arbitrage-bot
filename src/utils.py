import json
from typing import Tuple

from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from bot.account import Account


def get_algod_and_indexer() -> Tuple[AlgodClient, IndexerClient]:
    with open('../endpoint.json') as fp:
        endpoint = json.load(fp)
        algod = AlgodClient(endpoint['token'], endpoint['algod'])
        indexer = IndexerClient(endpoint['token'], endpoint['indexer'])
    return algod, indexer


def get_account(algod: AlgodClient):
    with open('../secret.json') as fp:
        secret = json.load(fp)
        mnemonic = secret['mnemonic']
    return Account(algod, mnemonic)
