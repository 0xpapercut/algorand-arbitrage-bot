# algorand-arbitrage-bot
A simple arbitrage bot for learning purposes.

## Setup
Prepare the following files at the root of the project
- `endpoint.json`
    ```json
    {
        "indexer": "<indexer endpoint>",
        "algod": "<algod endpoint>",
        "token": "<token>"
    }
    ```
- `secret.json`
    ```json
    {
        "mnemonic": "<24 word mnemonic>"
    }
    ```
Then install the dependencies with `pip install -r requirements.txt`, and run the bot with `python3 src/main.py`.

## Disclaimer
This repository is made available for *educational* purposes only; I take no responsibility on how it might be used or otherwise modified. Make sure you read all the code and understand the entire logic before any attempt to run it.
