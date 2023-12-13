# algorand-arbitrage-bot
A simple arbitrage bot for learning purposes.

## Setup
Prepare the following files at the root of the project
- `endpoint.json`
    ```json
    {
        "indexer": <indexer endpoint>,
        "algod": <algod endpoint>,
        "token": <token>
    }
    ```
- `secret.json`
    ```json
    {
        "mnemonic": <24 word mnemonic>
    }
    ```
Then install the dependencies with `pip install -r requirements.txt`, and run the bot with `python3 src/main.py`.
